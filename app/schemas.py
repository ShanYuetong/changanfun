"""API 的请求 / 响应数据结构（Pydantic）。

区分两层：
- models.Event 是数据库表结构；
- schemas.EventOut 是对外返回给客户端的数据结构。
这样以后修改数据库字段时，不会直接破坏 API 契约。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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