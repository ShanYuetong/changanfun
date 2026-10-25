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