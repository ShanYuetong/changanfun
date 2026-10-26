"""JSON API 测试：健康检查、列表、详情、分页与参数校验。"""

from __future__ import annotations

from fastapi.testclient import TestClient


# ---------------- 健康检查 ----------------


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "长安玩乐指南"
    assert data["version"] == "1.0.0"
    assert data["database"] == "ok"
    assert data["event_count"] == 15


# ---------------- 列表接口 ----------------


def test_list_events_returns_json(client: TestClient) -> None:
    response = client.get("/api/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert data["total"] == 15
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 15

    first = data["items"][0]
    # 字段完整性
    for field in [
        "id",
        "title",
        "category",
        "venue",
        "start_time",
        "end_time",
        "price",
        "description",
        "source",
        "created_at",
    ]:
        assert field in first
    # 时间字段为 ISO 8601 字符串
    assert "T" in first["start_time"]


def test_list_events_is_sorted_by_start_time(client: TestClient) -> None:
    """排序必须稳定：开始时间升序，相同则按 id 升序。"""
    items = client.get("/api/events?limit=100").json()["items"]
    keys = [(item["start_time"], item["id"]) for item in items]
    assert keys == sorted(keys)


def test_list_events_filter_by_category(client: TestClient) -> None:
    data = client.get("/api/events?category=电影").json()
    assert data["total"] == 3
    assert all(item["category"] == "电影" for item in data["items"])


def test_list_events_search_by_keyword(client: TestClient) -> None:
    data = client.get("/api/events?q=城墙").json()
    assert data["total"] >= 1
    for item in data["items"]:
        haystack = f"{item['title']}{item['venue']}{item['description']}"
        assert "城墙" in haystack


def test_list_events_search_and_category_combined(client: TestClient) -> None:
    data = client.get("/api/events?q=城墙&category=演出").json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["category"] == "演出"
    assert "城墙下的六把吉他" in item["title"]


def test_list_events_search_with_no_match(client: TestClient) -> None:
    data = client.get("/api/events?q=不存在的关键词zzz").json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_events_pagination(client: TestClient) -> None:
    """limit / offset 必须正确切分结果且互不重复。"""
    page1 = client.get("/api/events?limit=5&offset=0").json()
    page2 = client.get("/api/events?limit=5&offset=5").json()

    assert page1["total"] == 15 and page2["total"] == 15
    assert len(page1["items"]) == 5
    assert len(page2["items"]) == 5
    assert page1["offset"] == 0
    assert page2["offset"] == 5

    ids1 = {item["id"] for item in page1["items"]}
    ids2 = {item["id"] for item in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_list_events_offset_beyond_total_returns_empty(client: TestClient) -> None:
    data = client.get("/api/events?offset=1000").json()
    assert data["total"] == 15
    assert data["items"] == []


def test_list_events_optional_params_can_be_omitted(client: TestClient) -> None:
    """缺少所有可选参数时不应崩溃。"""
    response = client.get("/api/events")
    assert response.status_code == 200


def test_list_events_ignores_blank_keyword(client: TestClient) -> None:
    """空白关键词等同于没有关键词。"""
    data = client.get("/api/events?q=%20%20").json()
    assert data["total"] == 15


def test_list_events_treats_all_category_as_no_filter(client: TestClient) -> None:
    """category=全部 视为不筛选。"""
    data = client.get("/api/events?category=%E5%85%A8%E9%83%A8").json()
    assert data["total"] == 15


# ---------------- 参数校验 ----------------


def test_invalid_limit_returns_422(client: TestClient) -> None:
    for bad_limit in ["0", "-1", "101", "abc"]:
        response = client.get(f"/api/events?limit={bad_limit}")
        assert response.status_code == 422, f"limit={bad_limit} 应返回 422"
        assert "detail" in response.json()


def test_invalid_offset_returns_422(client: TestClient) -> None:
    for bad_offset in ["-1", "abc"]:
        response = client.get(f"/api/events?offset={bad_offset}")
        assert response.status_code == 422, f"offset={bad_offset} 应返回 422"


# ---------------- 详情接口 ----------------


def test_event_detail_api(client: TestClient) -> None:
    response = client.get("/api/events/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "《长安夜航》校园超前点映"
    assert data["category"] == "电影"


def test_event_detail_matches_list_item(client: TestClient) -> None:
    """详情接口与列表接口返回的数据应一致。"""
    items = client.get("/api/events?limit=100").json()["items"]
    for item in items[:5]:
        detail = client.get(f"/api/events/{item['id']}").json()
        assert detail == item


def test_missing_event_api_returns_404(client: TestClient) -> None:
    response = client.get("/api/events/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "活动不存在"


def test_invalid_event_id_type_returns_422(client: TestClient) -> None:
    """非整数 ID 属于参数类型错误，返回 FastAPI 默认的 422。"""
    response = client.get("/api/events/not-a-number")
    assert response.status_code == 422


def test_unknown_api_path_returns_json_404(client: TestClient) -> None:
    response = client.get("/api/unknown-endpoint")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


# ---------------- 接口文档 ----------------


def test_openapi_schema_is_available(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/health" in paths
    assert "/api/events" in paths
    assert "/api/events/{event_id}" in paths


def test_docs_page_is_available(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


# ---------------- 新增活动接口（POST /api/events）----------------

ADMIN_TOKEN = "test-admin-token-please-change"


def _new_event_payload(**overrides: object) -> dict[str, object]:
    """构造一条合法的活动提交数据。"""
    payload: dict[str, object] = {
        "title": "新增接口测试活动",
        "category": "展览",
        "venue": "测试美术馆",
        "start_time": "2026-06-01T10:00:00",
        "end_time": "2026-06-01T18:00:00",
        "price": "免费",
        "description": "由自动化测试创建的记录，用于验证新增接口。",
        "source": "测试数据 · 非真实信息",
    }
    payload.update(overrides)
    return payload


def test_create_event_requires_token(client: TestClient, monkeypatch) -> None:
    """未带密钥时应拒绝写入。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    response = client.post("/api/events", json=_new_event_payload())
    assert response.status_code == 401
    assert "密钥" in response.json()["detail"]


def test_create_event_rejects_wrong_token(client: TestClient, monkeypatch) -> None:
    """密钥错误时应拒绝写入。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    response = client.post(
        "/api/events",
        json=_new_event_payload(),
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert response.status_code == 401


def test_create_event_disabled_when_token_not_configured(
    client: TestClient, monkeypatch
) -> None:
    """服务端未配置密钥时返回 503，而不是放行（fail closed）。"""
    monkeypatch.delenv("CHANGAN_ADMIN_TOKEN", raising=False)

    response = client.post(
        "/api/events",
        json=_new_event_payload(),
        headers={"X-Admin-Token": "anything"},
    )
    assert response.status_code == 503
    assert "未配置管理密钥" in response.json()["detail"]


def test_create_event_success(client: TestClient, monkeypatch) -> None:
    """带正确密钥时应创建成功并返回 201。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    before = client.get("/api/events?limit=100").json()["total"]

    response = client.post(
        "/api/events",
        json=_new_event_payload(),
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert response.status_code == 201

    created = response.json()
    assert created["title"] == "新增接口测试活动"
    assert created["category"] == "展览"
    assert created["price"] == "免费"
    assert created["source"] == "测试数据 · 非真实信息"
    assert isinstance(created["id"], int)
    assert created["id"] > 0

    # 总数应 +1
    after = client.get("/api/events?limit=100").json()["total"]
    assert after == before + 1

    # 详情接口能读到
    detail = client.get(f"/api/events/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "新增接口测试活动"


def test_created_event_appears_in_list_and_search(
    client: TestClient, monkeypatch
) -> None:
    """新增的活动应能被列表、搜索、分类筛选与 HTML 页面找到。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    client.post(
        "/api/events",
        json=_new_event_payload(title="独一无二的新增活动标题"),
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )

    # 搜索
    found = client.get("/api/events?q=独一无二").json()
    assert found["total"] == 1
    assert found["items"][0]["title"] == "独一无二的新增活动标题"

    # 分类筛选（原本展览有 3 条，现在应为 4 条）
    exhibitions = client.get("/api/events?category=展览").json()
    assert exhibitions["total"] == 4
    assert all(item["category"] == "展览" for item in exhibitions["items"])

    # HTML 页面也能看到
    html = client.get("/?q=独一无二")
    assert html.status_code == 200
    assert "独一无二的新增活动标题" in html.text


def test_create_event_strips_whitespace(client: TestClient, monkeypatch) -> None:
    """提交的文本字段应去掉首尾空格。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    response = client.post(
        "/api/events",
        json=_new_event_payload(title="   带空格的标题   ", venue="  某场馆  "),
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "带空格的标题"
    assert response.json()["venue"] == "某场馆"


def test_create_event_rejects_invalid_category(client: TestClient, monkeypatch) -> None:
    """分类不在允许范围内应返回 422。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    response = client.post(
        "/api/events",
        json=_new_event_payload(category="音乐会"),
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert response.status_code == 422
    assert "分类" in response.text


def test_create_event_rejects_blank_fields(client: TestClient, monkeypatch) -> None:
    """必填文本字段为空白应返回 422。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    for field in ["title", "venue", "price", "description", "source"]:
        response = client.post(
            "/api/events",
            json=_new_event_payload(**{field: "   "}),
            headers={"X-Admin-Token": ADMIN_TOKEN},
        )
        assert response.status_code == 422, f"{field} 为空时应返回 422"


def test_create_event_rejects_reversed_time(client: TestClient, monkeypatch) -> None:
    """结束时间早于开始时间应返回 422。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    response = client.post(
        "/api/events",
        json=_new_event_payload(
            start_time="2026-06-01T18:00:00",
            end_time="2026-06-01T10:00:00",
        ),
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert response.status_code == 422
    assert "结束时间不能早于开始时间" in response.text


def test_create_event_rejects_timezone_aware_time(
    client: TestClient, monkeypatch
) -> None:
    """带时区的时间应被拒绝，保证全表时间语义一致。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    response = client.post(
        "/api/events",
        json=_new_event_payload(start_time="2026-06-01T10:00:00+08:00"),
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert response.status_code == 422
    assert "不带时区" in response.text


def test_create_event_allows_null_end_time(client: TestClient, monkeypatch) -> None:
    """结束时间可以省略，表示未标注固定结束时间。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    payload = _new_event_payload(title="无结束时间的新增活动")
    payload.pop("end_time")

    response = client.post(
        "/api/events", json=payload, headers={"X-Admin-Token": ADMIN_TOKEN}
    )
    assert response.status_code == 201
    assert response.json()["end_time"] is None


def test_create_event_rejects_duplicate(client: TestClient, monkeypatch) -> None:
    """同标题 + 同地点 + 同开始时间视为重复，返回 409。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)

    payload = _new_event_payload(title="重复提交测试")
    headers = {"X-Admin-Token": ADMIN_TOKEN}

    first = client.post("/api/events", json=payload, headers=headers)
    assert first.status_code == 201

    second = client.post("/api/events", json=payload, headers=headers)
    assert second.status_code == 409
    assert "已存在相同活动" in second.json()["detail"]
    # 提醒里带上已存在的 ID，便于排查
    assert str(first.json()["id"]) in second.json()["detail"]


def test_create_event_different_time_is_not_duplicate(
    client: TestClient, monkeypatch
) -> None:
    """标题与地点相同但开始时间不同，不算重复（同一活动可能有多场）。"""
    monkeypatch.setenv("CHANGAN_ADMIN_TOKEN", ADMIN_TOKEN)
    headers = {"X-Admin-Token": ADMIN_TOKEN}

    first = client.post("/api/events", json=_new_event_payload(), headers=headers)
    assert first.status_code == 201

    second = client.post(
        "/api/events",
        json=_new_event_payload(start_time="2026-06-02T10:00:00", end_time="2026-06-02T18:00:00"),
        headers=headers,
    )
    assert second.status_code == 201


def test_openapi_documents_post_endpoint(client: TestClient) -> None:
    """新增接口必须出现在 OpenAPI 文档里，且声明了安全相关响应码。"""
    schema = client.get("/openapi.json").json()
    events_path = schema["paths"]["/api/events"]
    assert "post" in events_path

    responses = events_path["post"]["responses"]
    assert "201" in responses
    assert "401" in responses
    assert "409" in responses
    assert "503" in responses