"""数据库测试：初始化、幂等种子数据、持久化、模型约束与 CRUD 行为。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app import crud, database, seed
from app.models import Event


# ---------------- 建表与种子数据 ----------------


def test_database_file_is_created_in_expected_path(client: TestClient, temp_db_path: Path) -> None:
    """访问应用后，数据库文件应出现在配置的路径。"""
    assert client.get("/").status_code == 200
    assert temp_db_path.exists()
    assert temp_db_path.stat().st_size > 0


def test_seed_data_is_complete(db_session) -> None:
    """示例数据至少 12 条，且覆盖 5 个分类、每个分类至少 2 条。"""
    inserted = seed.seed_if_empty(db_session)
    assert inserted == len(seed.DEMO_EVENTS)
    assert inserted >= 12

    events = db_session.query(Event).all()
    assert len(events) == inserted

    counts: dict[str, int] = {}
    for event in events:
        counts[event.category] = counts.get(event.category, 0) + 1

    assert set(counts) == {"电影", "展览", "演出", "校园活动", "休闲娱乐"}
    for category, count in counts.items():
        assert count >= 2, f"{category} 分类只有 {count} 条演示数据"


def test_seed_is_idempotent(db_session) -> None:
    """重复调用不会重复插入。"""
    first = seed.seed_if_empty(db_session)
    second = seed.seed_if_empty(db_session)
    assert first > 0
    assert second == 0
    assert db_session.query(Event).count() == first


def test_seed_runs_only_once_across_restarts(temp_db_path: Path) -> None:
    """模拟应用重启：多次启动后数据量不变。"""
    from app.main import init_database

    init_database()
    session = database.get_session_factory()()
    try:
        first_count = session.query(Event).count()
    finally:
        session.close()

    # 再次模拟启动两次
    init_database()
    init_database()

    session = database.get_session_factory()()
    try:
        assert session.query(Event).count() == first_count
    finally:
        session.close()


def test_seed_data_time_fields_are_valid(db_session) -> None:
    """示例数据的时间必须合法：结束时间不早于开始时间。"""
    seed.seed_if_empty(db_session)
    events = db_session.query(Event).all()
    for event in events:
        assert isinstance(event.start_time, datetime)
        if event.end_time is not None:
            assert event.end_time >= event.start_time, f"{event.title} 的结束时间早于开始时间"


def test_seed_data_has_no_blank_required_fields(db_session) -> None:
    """示例数据的必要字段都应有内容，且明确标注为演示数据。"""
    seed.seed_if_empty(db_session)
    for event in db_session.query(Event).all():
        assert event.title.strip()
        assert event.category.strip()
        assert event.venue.strip()
        assert event.price.strip()
        assert event.description.strip()
        assert event.source.strip()
        # 演示数据必须自我声明，不能伪装成真实活动
        assert "演示" in event.source or "示例" in event.source


def test_seed_data_has_required_categories(db_session) -> None:
    """示例数据必须用到 config 中声明的所有分类。"""
    from app import config

    seed.seed_if_empty(db_session)
    used = {event.category for event in db_session.query(Event).all()}
    assert used == set(config.CATEGORIES)


# ---------------- 数据持久化 ----------------


def test_data_persists_after_restart(temp_db_path: Path) -> None:
    """写入一条新活动后重新初始化数据库（模拟重启），数据仍在。"""
    from app.main import init_database

    init_database()

    session = database.get_session_factory()()
    try:
        crud.create_event(
            session,
            title="持久化测试活动",
            category="休闲娱乐",
            venue="持久化测试地点",
            start_time=datetime(2031, 5, 1, 9, 0),
            end_time=datetime(2031, 5, 1, 11, 0),
            price="免费",
            description="用于验证数据库持久化。",
            source="测试数据 · 非真实信息",
        )
    finally:
        session.close()

    # 释放连接后重新初始化 + 重新连接，模拟进程重启
    database.reset_database_state()
    init_database()

    session = database.get_session_factory()()
    try:
        titles = [event.title for event in session.query(Event).all()]
        assert "持久化测试活动" in titles
    finally:
        session.close()


# ---------------- 模型约束 ----------------


def test_end_time_before_start_time_is_rejected(sample_event_payload) -> None:
    """结束时间早于开始时间必须被拒绝。"""
    payload = dict(sample_event_payload)
    payload["start_time"] = datetime(2030, 1, 1, 12, 0)
    payload["end_time"] = datetime(2030, 1, 1, 10, 0)  # 早于开始时间

    with pytest.raises(ValueError, match="结束时间不能早于开始时间"):
        Event(**payload)


def test_end_time_equal_to_start_time_is_allowed(db_session) -> None:
    """结束时间等于开始时间是允许的（属于边界情况）。"""
    same = datetime(2030, 2, 2, 10, 0)
    event = Event(
        title="零时长活动",
        category="展览",
        venue="测试场馆",
        start_time=same,
        end_time=same,
        price="免费",
        description="测试结束时间等于开始时间。",
        source="测试数据",
    )
    db_session.add(event)
    db_session.commit()
    assert event.id is not None


def test_time_validation_is_order_independent() -> None:
    """无论先赋值 end_time 还是 start_time，非法组合都必须被拒绝。"""
    # 先传 end_time，再传早于它的 start_time
    with pytest.raises(ValueError, match="开始时间不能晚于结束时间"):
        Event(
            title="顺序测试",
            category="展览",
            venue="测试场馆",
            price="免费",
            description="测试赋值顺序。",
            source="测试数据",
            end_time=datetime(2030, 1, 1, 10, 0),
            start_time=datetime(2030, 1, 1, 12, 0),
        )


def test_modifying_start_time_after_creation_is_validated() -> None:
    """创建后修改 start_time 也不能破坏时间关系。"""
    event = Event(
        title="修改时间测试",
        category="展览",
        venue="测试场馆",
        start_time=datetime(2030, 1, 1, 10, 0),
        end_time=datetime(2030, 1, 1, 12, 0),
        price="免费",
        description="测试后续修改。",
        source="测试数据",
    )
    with pytest.raises(ValueError, match="开始时间不能晚于结束时间"):
        event.start_time = datetime(2030, 1, 1, 13, 0)


def test_missing_start_time_is_rejected() -> None:
    """start_time 为空时应在 Python 层被拒绝。"""
    with pytest.raises(ValueError, match="开始时间不能为空"):
        Event(
            title="缺少开始时间",
            category="展览",
            venue="测试场馆",
            start_time=None,  # type: ignore[arg-type]
            price="免费",
            description="测试必填时间。",
            source="测试数据",
        )


def test_end_time_is_optional(db_session) -> None:
    """end_time 允许为空。"""
    event = Event(
        title="无结束时间活动",
        category="休闲娱乐",
        venue="测试场馆",
        start_time=datetime(2030, 3, 3, 10, 0),
        end_time=None,
        price="免费",
        description="测试可空结束时间。",
        source="测试数据",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    assert event.end_time is None


def test_blank_required_field_is_rejected(sample_event_payload) -> None:
    """必要字段为空字符串时应报错。"""
    payload = dict(sample_event_payload)
    payload["title"] = "   "
    with pytest.raises(ValueError, match="不能为空"):
        Event(**payload)


def test_null_required_field_is_rejected_by_database(db_session) -> None:
    """数据库层面的非空约束是最后一道防线（绕过 ORM 校验直接插入）。"""
    from sqlalchemy import text

    with pytest.raises(IntegrityError):
        # 故意不提供 venue（NOT NULL 列），验证数据库自身也会拒绝
        db_session.execute(
            text(
                "INSERT INTO events "
                "(title, category, venue, start_time, end_time, price, description, source, created_at) "
                "VALUES ('缺少地点的活动', '展览', NULL, '2030-01-01 10:00:00', NULL, '免费', '说明', '测试数据', "
                "'2030-01-01 10:00:00')"
            )
        )
        db_session.commit()
    db_session.rollback()


# ---------------- CRUD 行为 ----------------


def test_crud_get_event_returns_none_for_missing(db_session) -> None:
    assert crud.get_event(db_session, 999999) is None


def test_crud_normalize_keyword() -> None:
    assert crud.normalize_keyword(None) is None
    assert crud.normalize_keyword("") is None
    assert crud.normalize_keyword("   ") is None
    assert crud.normalize_keyword("  城墙  ") == "城墙"


def test_crud_normalize_category() -> None:
    assert crud.normalize_category(None) is None
    assert crud.normalize_category("") is None
    assert crud.normalize_category("全部") is None
    assert crud.normalize_category("  电影 ") == "电影"


def test_crud_search_is_parameterized_not_string_concatenated(db_session) -> None:
    """包含 SQL 特殊字符的关键词应被当作普通文本处理，不能造成注入或报错。"""
    seed.seed_if_empty(db_session)
    for dangerous in ["' OR 1=1 --", "'; DROP TABLE events; --", "%", "_", "100%"]:
        # 不抛异常，且不会返回全部数据（除非真的匹配）
        results = crud.get_events(db_session, q=dangerous)
        assert isinstance(results, list)
    # 表结构仍然存在
    assert db_session.query(Event).count() > 0


def test_crud_pagination_is_stable(db_session) -> None:
    """相同条件多次查询，顺序必须一致，避免分页重复/遗漏。"""
    seed.seed_if_empty(db_session)
    first = [event.id for event in crud.get_events(db_session, limit=5, offset=0)]
    second = [event.id for event in crud.get_events(db_session, limit=5, offset=0)]
    assert first == second

    third = [event.id for event in crud.get_events(db_session, limit=5, offset=5)]
    assert set(first).isdisjoint(set(third))


def test_crud_count_matches_query_length(db_session) -> None:
    seed.seed_if_empty(db_session)
    for q, category in [(None, None), ("城墙", None), (None, "电影"), ("城墙", "演出")]:
        total = crud.count_events(db_session, q=q, category=category)
        events = crud.get_events(db_session, q=q, category=category, limit=crud.MAX_LIMIT)
        assert total == len(events)


def test_build_filters_is_shared_by_list_and_count(db_session) -> None:
    """筛选条件由 build_filters 统一生成，列表与统计不会出现口径差异。"""
    seed.seed_if_empty(db_session)

    # 无条件
    assert crud.build_filters() == []
    # 仅关键词（标题/地点/简介三选一即命中，因此生成 1 个 OR 条件）
    assert len(crud.build_filters(q="城墙")) == 1
    # 仅分类
    assert len(crud.build_filters(category="电影")) == 1
    # 关键词 + 分类
    assert len(crud.build_filters(q="城墙", category="演出")) == 2
    # 空白与「全部」都不产生条件
    assert crud.build_filters(q="   ", category="全部") == []

    # 统计结果必须与按同样条件取回的列表长度一致
    total = crud.count_events(db_session, q="城墙", category="演出")
    items = crud.get_events(db_session, q="城墙", category="演出", limit=crud.MAX_LIMIT)
    assert total == len(items) == 1


def test_database_url_is_absolute_and_configurable(temp_db_path: Path) -> None:
    """数据库地址来自配置且指向临时路径，不会写到项目 data 目录。"""
    from app import config

    url = config.get_database_url()
    assert url.startswith("sqlite:///")
    assert "test_changan.db" in url
    assert temp_db_path.as_posix() in url


def test_tests_do_not_touch_development_database(temp_db_path: Path) -> None:
    """测试必须使用独立临时库：开发数据库文件的修改时间不应变化。"""
    from app import config

    dev_db = config.DEFAULT_DATABASE_FILE
    before = dev_db.stat().st_mtime if dev_db.exists() else None

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        # 写一条只在测试库里存在的记录
        session = database.get_session_factory()()
        try:
            crud.create_event(
                session,
                title="不应出现在开发库的活动",
                category="休闲娱乐",
                venue="临时库",
                start_time=datetime(2032, 1, 1, 10, 0),
                end_time=None,
                price="免费",
                description="隔离性测试。",
                source="测试数据",
            )
        finally:
            session.close()
        assert test_client.get("/").status_code == 200

    after = dev_db.stat().st_mtime if dev_db.exists() else None
    assert before == after, "测试不应修改开发数据库文件"