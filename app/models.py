"""SQLAlchemy 数据模型。

时间字段统一约定：使用「不带时区」的本地时间（北京时间），
全表保持一致，避免不同时区语义混用导致排序错乱。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates


class Base(DeclarativeBase):
    """所有模型的基类（SQLAlchemy 2.x 声明式写法）。"""


def _now() -> datetime:
    """当前本地时间，用作 created_at 默认值。"""
    return datetime.now()


class Event(Base):
    """活动信息。

    一条 Event 代表一个电影场次、展览、演出、校园活动或休闲娱乐去处。
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    price: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    # 常用查询的索引：分类筛选、标题搜索、时间排序
    __table_args__ = (
        Index("ix_events_category", "category"),
        Index("ix_events_title", "title"),
        Index("ix_events_start_time", "start_time"),
        # 数据库层面的兜底约束：结束时间不得早于开始时间
        CheckConstraint(
            "end_time IS NULL OR end_time >= start_time",
            name="ck_events_end_time_not_before_start",
        ),
    )

    # ---- Python 层面的校验，能在写入前给出更清晰的错误信息 ----
    @validates("title", "category", "venue", "price", "description", "source")
    def _validate_not_blank(self, key: str, value: str) -> str:
        """必要文本字段不能为空白。"""
        if value is None or not str(value).strip():
            raise ValueError(f"字段 {key} 不能为空")
        return str(value).strip()

    @validates("start_time", "end_time")
    def _validate_time_order(self, key: str, value: datetime | None) -> datetime | None:
        """校验开始 / 结束时间的先后关系。

        这里同时监听两个字段，因此无论先赋值 start_time 还是先赋值 end_time，
        甚至在之后修改其中一个，都能被检查到（只监听 end_time 会留下绕过路径）。
        """
        if key == "start_time":
            if value is None:
                raise ValueError("开始时间不能为空")
        elif value is None:
            # end_time 允许为空，表示「未标注固定结束时间」
            return value

        other = self.end_time if key == "start_time" else self.start_time
        if other is not None:
            if key == "end_time" and value < other:
                raise ValueError("结束时间不能早于开始时间")
            if key == "start_time" and other < value:
                raise ValueError("开始时间不能晚于结束时间")
        return value

    def __repr__(self) -> str:  # pragma: no cover - 仅用于调试输出
        return f"<Event id={self.id} title={self.title!r}>"