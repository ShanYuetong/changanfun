"""JSON API 路由。

接口：
- GET /api/health          健康检查
- GET /api/events          活动列表（支持 q / category / limit / offset）
- GET /api/events/{id}     活动详情

参数校验交给 FastAPI + Pydantic：
limit / offset 通过 Query(ge=..., le=...) 约束，非法时自动返回 422 验证错误。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import config, crud, schemas
from app.database import get_db

router = APIRouter()


@router.get("/health", response_model=schemas.HealthResponse, summary="健康检查")
def health_check(db: Session = Depends(get_db)) -> schemas.HealthResponse:
    """检查服务与数据库是否正常。"""
    try:
        event_count = crud.count_events(db)
        database_state = "ok"
    except Exception:  # pragma: no cover - 仅在数据库异常时触发
        # 不把内部异常细节暴露给调用方，但状态如实标记为不可用
        event_count = 0
        database_state = "unavailable"

    return schemas.HealthResponse(
        status="ok" if database_state == "ok" else "degraded",
        app=config.APP_NAME,
        version=config.APP_VERSION,
        database=database_state,
        event_count=event_count,
    )


@router.get(
    "/events",
    response_model=schemas.EventListResponse,
    responses={422: {"description": "参数验证失败"}},
    summary="获取活动列表",
)
def list_events(
    q: str | None = Query(default=None, description="关键词，匹配标题、地点或简介"),
    category: str | None = Query(default=None, description="活动分类，如「电影」"),
    limit: int = Query(default=20, ge=1, le=crud.MAX_LIMIT, description="返回数量上限"),
    offset: int = Query(default=0, ge=0, description="分页偏移量"),
    db: Session = Depends(get_db),
) -> schemas.EventListResponse:
    """按关键词与分类查询活动列表，返回带分页信息的 JSON。"""
    keyword = crud.normalize_keyword(q)
    active_category = crud.normalize_category(category)

    events = crud.get_events(
        db,
        q=keyword,
        category=active_category,
        limit=limit,
        offset=offset,
    )
    total = crud.count_events(db, q=keyword, category=active_category)

    return schemas.EventListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[schemas.EventOut.model_validate(event) for event in events],
    )


@router.get(
    "/events/{event_id}",
    response_model=schemas.EventOut,
    responses={404: {"description": "活动不存在"}},
    summary="获取活动详情",
)
def get_event_detail(
    event_id: int = Path(..., description="活动 ID"),
    db: Session = Depends(get_db),
) -> schemas.EventOut:
    """按 ID 获取单个活动；不存在时返回 HTTP 404。"""
    event = crud.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    return schemas.EventOut.model_validate(event)