"""JSON API 路由。

接口：
- GET  /api/health          健康检查
- GET  /api/events          活动列表（支持 q / category / limit / offset）
- POST /api/events          新增活动（需要管理密钥）
- GET  /api/events/{id}     活动详情

参数校验交给 FastAPI + Pydantic：
limit / offset 通过 Query(ge=..., le=...) 约束，非法时自动返回 422 验证错误。

写接口的访问控制：请求头需带 X-Admin-Token，值与环境变量 CHANGAN_ADMIN_TOKEN 一致。
未配置密钥时写接口一律返回 503（fail closed），不会因为「忘记配置」而变成人人可写。
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app import config, crud, schemas
from app.database import get_db

router = APIRouter()


def require_admin_token(
    x_admin_token: str | None = Header(
        default=None,
        alias="X-Admin-Token",
        description="管理密钥，需与环境变量 CHANGAN_ADMIN_TOKEN 一致",
    ),
) -> None:
    """校验写接口的管理密钥。

    两种失败分开处理，便于排查：
    - 服务端没配置密钥 → 503，表示「这个功能还没开启」，而不是客户端密码错
    - 客户端没带或带错 → 401

    比较使用 secrets.compare_digest：普通 == 会在第一个不同字符处提前返回，
    理论上可通过响应时间差异逐字符猜出密钥，常数时间比较能避免这一点。
    """
    expected = config.get_admin_token()
    if expected is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "服务端未配置管理密钥，写接口已禁用。"
                f"请设置环境变量 {config.ADMIN_TOKEN_ENV} 后重启服务。"
            ),
        )

    provided = (x_admin_token or "").strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理密钥缺失或不正确",
            headers={"WWW-Authenticate": "X-Admin-Token"},
        )


@router.post(
    "/events",
    response_model=schemas.EventOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_token)],
    responses={
        201: {"description": "创建成功"},
        401: {"description": "管理密钥缺失或不正确"},
        409: {"description": "已存在相同标题、地点与开始时间的活动"},
        422: {"description": "参数验证失败"},
        503: {"description": "服务端未配置管理密钥，写接口已禁用"},
    },
    summary="新增活动（需要管理密钥）",
)
def create_event(
    payload: schemas.EventCreate,
    db: Session = Depends(get_db),
) -> schemas.EventOut:
    """新增一条活动记录。

    校验顺序：先说清楚为什么拒绝，再决定要不要写。
    1. 参数格式由 EventCreate 校验（分类合法、文本非空、时间关系正确），失败返回 422；
    2. 查重：标题 + 地点 + 开始时间完全相同视为重复，返回 409 并带上已存在的 ID，
       避免重复提交（例如网络重试）产生多条相同记录；
    3. 写入并返回 201 与新记录的完整内容。
    """
    existing = crud.find_duplicate_event(
        db,
        title=payload.title,
        venue=payload.venue,
        start_time=payload.start_time,
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"已存在相同活动（ID {existing.id}）：{existing.title}",
        )

    event = crud.create_event(
        db,
        title=payload.title,
        category=payload.category,
        venue=payload.venue,
        start_time=payload.start_time,
        end_time=payload.end_time,
        price=payload.price,
        description=payload.description,
        source=payload.source,
    )
    return schemas.EventOut.model_validate(event)


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