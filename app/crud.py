"""数据查询层（CRUD）。

页面路由与 API 路由共用这里的查询函数，保证筛选逻辑只有一份实现。

安全说明：所有用户输入都通过 SQLAlchemy 的参数化表达处理（.where(Event.title.ilike(...))），
不存在字符串拼接 SQL。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Event

# 分页默认值与上限，页面与 API 共用
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def normalize_keyword(q: str | None) -> str | None:
    """规范化搜索关键词：去掉首尾空格；空字符串视为「没有关键词」。"""
    if q is None:
        return None
    cleaned = q.strip()
    return cleaned or None


def normalize_category(category: str | None) -> str | None:
    """规范化分类：去掉首尾空格；"全部" / 空字符串 视为「不筛选」。"""
    if category is None:
        return None
    cleaned = category.strip()
    if not cleaned or cleaned == "全部":
        return None
    return cleaned


def build_filters(q: str | None = None, category: str | None = None) -> list:
    """把关键词与分类转换成 SQLAlchemy 的筛选条件列表。

    get_events() 与 count_events() 共用这一份逻辑，
    所以「列表里看到的」与「total 统计的」永远一致。
    传入的 q / category 会先被规范化，None 或空白表示不筛选。
    """
    filters = []

    keyword = normalize_keyword(q)
    if keyword:
        # ilike 在 SQLite 上等价于 LIKE：ASCII 不区分大小写；
        # 中文没有大小写问题。这里用参数化表达式，不做字符串拼接。
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                Event.title.ilike(pattern),
                Event.venue.ilike(pattern),
                Event.description.ilike(pattern),
            )
        )

    chosen_category = normalize_category(category)
    if chosen_category:
        filters.append(Event.category == chosen_category)

    return filters


def get_events(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[Event]:
    """按关键词、分类查询活动列表。

    - q：在标题、地点、简介中做不区分大小写的模糊匹配（支持中文）
    - category：精确匹配分类
    - 两者可以同时生效（AND 关系）
    - 排序规则：开始时间升序 → id 升序（保证顺序稳定，分页不会重复或跳动）
    """
    statement = select(Event).where(*build_filters(q, category))
    statement = statement.order_by(Event.start_time.asc(), Event.id.asc())
    statement = statement.limit(limit).offset(offset)

    return list(db.scalars(statement).all())


def count_events(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
) -> int:
    """统计符合筛选条件的活动总数（用于分页与结果数量展示）。"""
    statement = select(func.count()).select_from(Event).where(*build_filters(q, category))
    return int(db.scalar(statement) or 0)


def get_event(db: Session, event_id: int) -> Event | None:
    """按 ID 获取单个活动；不存在时返回 None（由调用方决定返回 404）。"""
    return db.get(Event, event_id)


def create_event(db: Session, **fields: object) -> Event:
    """创建一条活动记录。

    供示例数据导入、API 新增活动与测试共同使用。
    写入失败时回滚事务，避免会话停留在脏状态导致同一请求内的后续操作全部失败。
    """
    event = Event(**fields)  # type: ignore[arg-type]
    db.add(event)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(event)
    return event


def find_duplicate_event(
    db: Session,
    *,
    title: str,
    venue: str,
    start_time: datetime,
) -> Event | None:
    """查找可能重复的活动：标题、地点、开始时间三者完全相同。

    MVP 阶段用「完全相同」作为判重标准，简单且不会误伤。
    真实数据接入后可改为模糊匹配（见文档第 9 章的清洗与去重一节）。
    """
    statement = (
        select(Event)
        .where(
            Event.title == title,
            Event.venue == venue,
            Event.start_time == start_time,
        )
        .limit(1)
    )
    return db.scalars(statement).first()