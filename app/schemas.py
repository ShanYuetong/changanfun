"""API 的请求 / 响应数据结构（Pydantic）。

区分两层：
- models.Event 是数据库表结构；
- schemas.EventOut 是对外返回给客户端的数据结构。
这样以后修改数据库字段时，不会直接破坏 API 契约。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import config


class EventOut(BaseModel):
    """单个活动的对外输出结构。"""

    # from_attributes 允许直接从 SQLAlchemy 对象转换
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="活动 ID", examples=[1])
    title: str = Field(..., description="活动标题")
    category: str = Field(..., description="活动分类")
    venue: str = Field(..., description="活动地点")
    start_time: datetime = Field(..., description="开始时间（北京时间）")
    end_time: datetime | None = Field(None, description="结束时间（北京时间），可为空")
    price: str = Field(..., description="价格或免费说明")
    description: str = Field(..., description="活动简介")
    source: str = Field(..., description="数据来源或演示数据声明")
    created_at: datetime = Field(..., description="记录创建时间")


class EventListResponse(BaseModel):
    """活动列表的统一响应结构，包含分页信息。"""

    total: int = Field(..., description="符合筛选条件的活动总数", examples=[14])
    limit: int = Field(..., description="本次返回数量上限", examples=[20])
    offset: int = Field(..., description="本次结果的分页偏移量", examples=[0])
    items: list[EventOut] = Field(..., description="活动列表")


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = Field(..., description="服务状态", examples=["ok"])
    app: str = Field(..., description="应用名称")
    version: str = Field(..., description="应用版本")
    database: str = Field(..., description="数据库连通状态", examples=["ok"])
    event_count: int = Field(..., description="当前数据库中的活动总数", examples=[14])


class ErrorResponse(BaseModel):
    """错误响应的统一结构。"""

    detail: str = Field(..., description="错误说明", examples=["活动不存在"])


class EventCreate(BaseModel):
    """新增活动的请求结构。

    校验集中在这里，写入逻辑不必重复判断：
    - 分类必须属于 config.CATEGORIES（防止写入「电影 」这种拼写不一致导致筛不到）
    - 文本字段去空格后不能为空，并有长度上限
    - 结束时间若提供，必须不早于开始时间
    - source 必填且不能是空白：每条记录都必须说明数据来源，不能无主
    """

    title: str = Field(..., max_length=200, description="活动标题")
    category: str = Field(..., max_length=50, description="活动分类")
    venue: str = Field(..., max_length=200, description="活动地点")
    start_time: datetime = Field(..., description="开始时间（不带时区，视为北京时间）")
    end_time: datetime | None = Field(
        None, description="结束时间（不带时区），可为空；提供时必须不早于开始时间"
    )
    price: str = Field(..., max_length=100, description="价格或免费说明")
    description: str = Field(..., max_length=2000, description="活动简介")
    source: str = Field(..., max_length=200, description="数据来源，例如「演示数据」或具体来源")

    @field_validator("title", "venue", "price", "description", "source")
    @classmethod
    def _strip_and_require(cls, value: str, info) -> str:
        """文本字段去首尾空格，且不允许为空或纯空白。"""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"字段 {info.field_name} 不能为空")
        return cleaned

    @field_validator("category")
    @classmethod
    def _check_category(cls, value: str) -> str:
        """分类必须属于允许的取值。"""
        cleaned = value.strip()
        if cleaned not in config.CATEGORIES:
            raise ValueError(
                f"活动分类必须是以下之一：{'、'.join(config.CATEGORIES)}"
            )
        return cleaned

    @field_validator("start_time")
    @classmethod
    def _check_start_time(cls, value: datetime) -> datetime:
        """开始时间必填，且不允许带时区。"""
        if value.tzinfo is not None:
            raise ValueError("时间请使用不带时区的格式，例如 2026-04-01T19:30:00")
        return value

    @field_validator("end_time")
    @classmethod
    def _check_time_order(cls, value: datetime | None, info) -> datetime | None:
        """结束时间若提供，必须不早于开始时间，且不能带时区。

        数据库统一存不带时区的北京时间，混入带时区的值会导致排序错乱，
        这里提前拦下并给出明确提示。
        """
        if value is None:
            return None
        if value.tzinfo is not None:
            raise ValueError("时间请使用不带时区的格式，例如 2026-04-01T19:30:00")

        start = info.data.get("start_time")
        if start is not None and value < start:
            raise ValueError("结束时间不能早于开始时间")
        return value