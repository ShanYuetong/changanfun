"""HTML 页面测试：首页、搜索、分类、组合筛选、详情页与 404。"""

from __future__ import annotations

import urllib.parse

from fastapi.testclient import TestClient


def _url(**params: str) -> str:
    """把查询参数拼成 URL（自动做中文编码）。"""
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    return f"/?{query}" if query else "/"


# ---------------- 首页 ----------------


def test_homepage_returns_200(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "长安玩乐指南" in response.text


def test_homepage_shows_event_cards(client: TestClient) -> None:
    """首页应展示从 SQLite 真实读取的活动卡片。"""
    response = client.get("/")
    assert response.status_code == 200
    # 15 条演示数据应全部出现在首页
    assert response.text.count('class="event-card"') == 15
    # 抽查几条具体标题
    assert "《长安夜航》校园超前点映" in response.text
    assert "春季社团招新市集" in response.text


def test_homepage_shows_category_navigation(client: TestClient) -> None:
    response = client.get("/")
    for category in ["全部", "电影", "展览", "演出", "校园活动", "休闲娱乐"]:
        assert category in response.text


def test_homepage_shows_demo_notice_and_version(client: TestClient) -> None:
    """页脚必须显示演示数据声明与版本号。"""
    response = client.get("/")
    assert "演示数据" in response.text
    assert "v1.0.0" in response.text


# ---------------- 搜索 ----------------


def test_search_by_title_returns_matching_events(client: TestClient) -> None:
    response = client.get(_url(q="长安夜航"))
    assert response.status_code == 200
    assert "《长安夜航》校园超前点映" in response.text
    # 只应命中一条
    assert response.text.count('class="event-card"') == 1


def test_search_matches_venue(client: TestClient) -> None:
    """关键词应能匹配地点字段。"""
    response = client.get(_url(q="易俗社"))
    assert response.status_code == 200
    assert "秦腔新编折子戏学生专场" in response.text
    assert response.text.count('class="event-card"') == 1


def test_search_matches_description(client: TestClient) -> None:
    """关键词应能匹配简介字段。"""
    response = client.get(_url(q="护林员"))
    assert response.status_code == 200
    assert "露天电影夜：《秦岭的风》" in response.text


def test_search_strips_surrounding_spaces(client: TestClient) -> None:
    """关键词前后空格必须被忽略。"""
    with_spaces = client.get(_url(q="  城墙  "))
    without_spaces = client.get(_url(q="城墙"))
    assert with_spaces.status_code == 200
    assert with_spaces.text == without_spaces.text


def test_search_is_case_insensitive_for_ascii(client: TestClient) -> None:
    """ASCII 片段大小写不敏感（SQLite 的 LIKE 语义）。"""
    lower = client.get(_url(q="livehouse"))
    upper = client.get(_url(q="LIVEHOUSE"))
    assert "城墙下的六把吉他" in lower.text
    assert "城墙下的六把吉他" in upper.text


def test_search_with_no_match_shows_empty_state(client: TestClient) -> None:
    response = client.get(_url(q="这个关键词肯定不存在zzz"))
    assert response.status_code == 200
    assert "暂时没有符合条件的活动" in response.text
    assert "没有找到包含" in response.text
    assert 'class="event-card"' not in response.text


def test_search_result_page_shows_current_condition(client: TestClient) -> None:
    """页面应显示当前搜索条件，并提供清除入口。"""
    response = client.get(_url(q="城墙"))
    assert "当前条件" in response.text
    assert "关键词「城墙」" in response.text
    assert "全部清除" in response.text


def test_search_handles_chinese_boundary_cases(client: TestClient) -> None:
    """中文关键词的边界情况：单字、多字、全角空格、中英混排。"""
    # 单字关键词应能匹配
    single = client.get(_url(q="城"))
    assert single.status_code == 200
    assert single.text.count('class="event-card"') >= 1

    # 全角空格同样视为空白，应被去掉
    with_fullwidth = client.get(_url(q="\u3000城墙\u3000"))
    normal = client.get(_url(q="城墙"))
    assert with_fullwidth.text == normal.text

    # 中英混排
    mixed = client.get(_url(q="Livehouse 小厅"))
    assert mixed.status_code == 200
    assert "城墙下的六把吉他" in mixed.text


def test_search_special_characters_do_not_break_page(client: TestClient) -> None:
    """包含 SQL 特殊字符的关键词不能导致服务器错误。"""
    for dangerous in ["100%", "a_b", "' OR 1=1 --", "<script>alert(1)</script>"]:
        response = client.get(_url(q=dangerous))
        assert response.status_code == 200, f"关键词 {dangerous!r} 导致异常"

    # 关键词必须被转义，不能原样注入 HTML
    injected = client.get(_url(q="<script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in injected.text


def test_search_keyword_is_preserved_in_input_box(client: TestClient) -> None:
    """刷新后搜索框仍保留关键词。"""
    response = client.get(_url(q="城墙"))
    assert 'value="城墙"' in response.text


# ---------------- 分类筛选 ----------------


def test_filter_by_movie_category(client: TestClient) -> None:
    response = client.get(_url(category="电影"))
    assert response.status_code == 200
    # 演示数据中电影分类有 3 条
    assert response.text.count('class="event-card"') == 3
    # 其它分类的活动不应出现
    assert "春季社团招新市集" not in response.text


def test_all_categories_return_expected_counts(client: TestClient) -> None:
    """每个分类至少 2 条数据，且总数之和等于全部 15 条。"""
    counts = {}
    for category in ["电影", "展览", "演出", "校园活动", "休闲娱乐"]:
        response = client.get(_url(category=category))
        assert response.status_code == 200
        counts[category] = response.text.count('class="event-card"')
        assert counts[category] >= 2, f"{category} 分类数据不足 2 条"
    assert sum(counts.values()) == 15


def test_active_category_has_visual_state(client: TestClient) -> None:
    """选中分类应带 is-active 样式与 aria-current 标记。"""
    response = client.get(_url(category="展览"))
    assert "category-link is-active" in response.text
    assert 'aria-current="true"' in response.text


def test_unknown_category_shows_empty_state(client: TestClient) -> None:
    response = client.get(_url(category="不存在的分类"))
    assert response.status_code == 200
    assert "暂时没有符合条件的活动" in response.text


# ---------------- 搜索 + 分类组合 ----------------


def test_search_and_category_combined(client: TestClient) -> None:
    """组合条件下结果必须同时满足两个条件。"""
    response = client.get(_url(q="城墙", category="演出"))
    assert response.status_code == 200
    assert "城墙下的六把吉他" in response.text
    # 「城墙」单独搜索会命中电影、休闲娱乐等其他分类，组合后应被排除
    assert "露天电影夜：《秦岭的风》" not in response.text
    assert "环城公园春日骑行集合" not in response.text


def test_combined_filter_with_conflicting_condition_shows_empty(client: TestClient) -> None:
    """关键词与分类不可能同时满足时，显示空状态。"""
    response = client.get(_url(q="秦腔", category="电影"))
    assert response.status_code == 200
    assert "暂时没有符合条件的活动" in response.text


def test_category_links_keep_keyword(client: TestClient) -> None:
    """切换分类时应保留当前关键词，保证组合筛选可用。"""
    response = client.get(_url(q="城墙"))
    # 分类链接中应包含经过 URL 编码的关键词
    encoded = urllib.parse.quote("城墙")
    assert f"category=" in response.text
    assert encoded in response.text


# ---------------- 详情页 ----------------


def test_event_detail_page_returns_200(client: TestClient) -> None:
    response = client.get("/events/1")
    assert response.status_code == 200
    assert "《长安夜航》校园超前点映" in response.text
    # 详情页必备信息
    assert "活动地点" in response.text
    assert "开始时间" in response.text
    assert "结束时间" in response.text
    assert "价格" in response.text
    assert "活动介绍" in response.text
    assert "数据来源" in response.text
    assert "返回活动列表" in response.text


def test_all_event_cards_link_to_valid_detail_pages(client: TestClient) -> None:
    """首页每条卡片都能打开对应详情页。"""
    listing = client.get("/api/events?limit=100").json()
    assert listing["total"] == 15
    for item in listing["items"]:
        detail = client.get(f"/events/{item['id']}")
        assert detail.status_code == 200
        assert item["title"] in detail.text


def test_missing_event_id_returns_404_page(client: TestClient) -> None:
    """不存在的活动 ID 返回 404 HTML 页面，而不是服务器错误。"""
    response = client.get("/events/999999")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "404" in response.text
    assert "返回首页" in response.text


def test_non_numeric_event_id_returns_404_page(client: TestClient) -> None:
    """非数字 ID 也返回友好的 404 页面。"""
    response = client.get("/events/abc")
    assert response.status_code == 404
    assert "不是一个有效的活动编号" in response.text


def test_unknown_page_returns_404_page(client: TestClient) -> None:
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404
    assert "404" in response.text


def test_homepage_shows_empty_state_when_no_events(empty_client: TestClient) -> None:
    """数据库为空时首页显示友好提示，而不是空白页或报错。"""
    response = empty_client.get("/")
    assert response.status_code == 200
    assert "暂时没有符合条件的活动" in response.text
    assert "目前还没有任何活动数据" in response.text
    assert "返回全部活动" in response.text
    assert 'class="event-card"' not in response.text
    # 空数据时数量显示为 0
    assert "共 0 个活动" in response.text


def test_api_returns_empty_list_when_no_events(empty_client: TestClient) -> None:
    """数据库为空时 API 返回空列表，total 为 0。"""
    data = empty_client.get("/api/events").json()
    assert data["total"] == 0
    assert data["items"] == []


def test_empty_database_still_serves_health_check(empty_client: TestClient) -> None:
    """空库时健康检查依然正常，活动数为 0。"""
    response = empty_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["event_count"] == 0
    assert response.json()["status"] == "ok"


# ---------------- 静态资源 ----------------


def test_static_css_and_js_are_served(client: TestClient) -> None:
    css = client.get("/static/css/style.css")
    js = client.get("/static/js/main.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "--color-accent" in css.text
    assert "use strict" in js.text


# ---------------- PWA 相关 ----------------


def test_manifest_is_served_and_valid(client: TestClient) -> None:
    """PWA manifest 必须可访问且字段完整。"""
    response = client.get("/static/manifest.json")
    assert response.status_code == 200

    data = response.json()
    for key in ("name", "short_name", "start_url", "display", "theme_color", "icons"):
        assert key in data, f"manifest 缺少字段 {key}"
    assert data["display"] == "standalone"
    assert data["start_url"] == "/"
    # 至少要有 192 与 512 两种尺寸
    sizes = {icon["sizes"] for icon in data["icons"]}
    assert "192x192" in sizes
    assert "512x512" in sizes
    # maskable 图标是 Android 自适应图标所必需
    assert any(icon.get("purpose") == "maskable" for icon in data["icons"])


def test_service_worker_is_served_from_root(client: TestClient) -> None:
    """Service Worker 必须从根路径提供，否则作用域会被限制在 /static/ 下。"""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    # 允许 SW 控制全站
    assert response.headers.get("service-worker-allowed") == "/"
    # 不能被浏览器长期缓存，否则更新无法生效
    assert "no-cache" in response.headers.get("cache-control", "")
    # 关键逻辑必须存在
    assert "addEventListener" in response.text
    assert "caches" in response.text


def test_service_worker_does_not_cache_api(client: TestClient) -> None:
    """SW 源码中必须显式跳过 /api/，避免活动数据被缓存成过期内容。"""
    text = client.get("/sw.js").text
    assert "/api/" in text


def test_offline_page_is_served(client: TestClient) -> None:
    response = client.get("/static/offline.html")
    assert response.status_code == 200
    assert "离线" in response.text


def test_pwa_icons_are_served(client: TestClient) -> None:
    """所有 manifest 声明的图标都必须真实可访问。"""
    for name in [
        "icon.svg",
        "favicon.svg",
        "icon-192.png",
        "icon-512.png",
        "icon-maskable-512.png",
    ]:
        response = client.get(f"/static/icons/{name}")
        assert response.status_code == 200, f"图标 {name} 无法访问"
        assert len(response.content) > 0


def test_base_template_declares_pwa_metadata(client: TestClient) -> None:
    """页面必须声明 manifest、theme-color 与 iOS 相关 meta。"""
    html = client.get("/").text
    assert 'rel="manifest"' in html
    assert 'name="theme-color"' in html
    assert "apple-touch-icon" in html
    assert "apple-mobile-web-app-capable" in html


# ---------------- 视觉增强 ----------------


def test_category_icons_are_inline_svg(client: TestClient) -> None:
    """分类图标应为内联 SVG，而不是依赖系统字体渲染的 emoji。"""
    html = client.get("/").text
    assert 'class="icon icon-' in html
    # 原来的 emoji 不应再出现（跨系统渲染不一致）
    for emoji in ["🎬", "🖼", "🎭", "🎓", "🍃"]:
        assert emoji not in html, f"页面仍包含 emoji 图标 {emoji}"


def test_event_cards_carry_category_color(client: TestClient) -> None:
    """卡片应带上分类主色变量，用于顶部渐变色带。"""
    html = client.get("/").text
    assert "--cat-a:" in html
    assert "--cat-b:" in html


def test_detail_page_has_visual_accent(client: TestClient) -> None:
    """详情页必须有分类色带作为视觉锚点。"""
    html = client.get("/events/1").text
    assert 'class="detail-accent"' in html
    assert "--cat-a:" in html


def test_animations_respect_reduced_motion(client: TestClient) -> None:
    """动效必须在系统开启「减少动画」时被关闭。"""
    css = client.get("/static/css/style.css").text
    assert "prefers-reduced-motion" in css
    assert "@keyframes fade-up" in css