"""pytest 公共配置。

关键职责：
1. **数据隔离**：每个测试函数都使用自己独立的临时 SQLite 数据库文件，
   绝不触碰开发用的 data/changan.db；
2. 数据库地址通过环境变量 CHANGAN_DATABASE_URL 注入，
   并调用 reset_database_state() 让 Engine 重新绑定到新地址；
3. TestClient 使用 with 语句启动，会触发 lifespan，
   从而真实地执行「建表 + 导入示例数据」的启动流程。
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import database
from app.main import app
from app.models import Base, Event


@pytest.fixture()
def temp_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """为单个测试准备独立的临时数据库地址。"""
    db_file = tmp_path / "test_changan.db"
    monkeypatch.setenv("CHANGAN_DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    # 让 Engine / Session 工厂重新读取上面的地址
    database.reset_database_state()
    yield db_file
    database.reset_database_state()


@pytest.fixture()
def client(temp_db_path: Path) -> Iterator[TestClient]:
    """带示例数据的测试客户端（启动流程会建表并导入演示数据）。"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def empty_client(client: TestClient) -> TestClient:
    """清空活动表后的测试客户端，用于验证空状态。

    示例数据只在应用启动时导入一次，因此这里清空后不会被自动补回。
    """
    session = database.get_session_factory()()
    try:
        session.query(Event).delete()
        session.commit()
    finally:
        session.close()
    return client


@pytest.fixture()
def db_session(temp_db_path: Path) -> Iterator[Session]:
    """直接操作数据库的会话，用于测试模型约束与持久化。

    依赖 temp_db_path，因此同样使用独立的临时数据库，不会污染 data/changan.db；
    并主动建表，保证不依赖 TestClient 也能使用。
    """
    Base.metadata.create_all(bind=database.get_engine())
    session = database.get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def sample_event_payload() -> dict[str, object]:
    """一条用于测试的最小合法活动数据。"""
    return {
        "title": "测试专用活动",
        "category": "展览",
        "venue": "测试场馆",
        "start_time": datetime(2030, 1, 1, 10, 0),
        "end_time": datetime(2030, 1, 1, 12, 0),
        "price": "免费",
        "description": "用于自动化测试的活动记录。",
        "source": "测试数据 · 非真实信息",
    }