"""数据库连接与会话管理。

设计要点：
1. Engine 与 Session 工厂采用「懒加载」：只有在真正需要数据库时才创建，
   避免导入模块时就产生写盘行为。
2. 数据库地址集中由 config.get_database_url() 决定，测试通过环境变量
   CHANGAN_DATABASE_URL 指向临时文件，实现测试数据与开发数据隔离。
3. get_db() 是 FastAPI 的依赖注入函数，负责每个请求创建 / 关闭一个会话。
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import config

# 模块级缓存：Engine 与 Session 工厂只创建一次
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """获取（必要时创建）全局 Engine。"""
    global _engine
    if _engine is None:
        config.ensure_data_dir()
        url = config.get_database_url()
        # SQLite 在多线程测试客户端下需要关闭同线程检查
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """获取（必要时创建）Session 工厂。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：为每个请求提供一个数据库会话，请求结束后自动关闭。"""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_database_state() -> None:
    """释放 Engine 并清空缓存。

    主要给测试使用：切换数据库地址后需要重建连接；
    正常业务代码不需要调用它。
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None