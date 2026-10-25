"""HTML 页面路由：首页、活动详情、404。

筛选逻辑统一调用 app.crud，与 API 共用同一套查询代码。
搜索与分类全部走 GET 查询参数（?q=...&category=...），
因此即使浏览器禁用了 JavaScript，核心浏览功能依然可用。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.templating import render_404, templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="home")
def home_page(
    request: Request,
    q: str | None = Query(default=None, description="搜索关键词"),
    category: str | None = Query(default=None, description="活动分类"),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """首页：展示活动卡片列表，支持关键词搜索与分类筛选。"""
    # 规范化输入：去掉首尾空格，"全部" 视为不筛选
    keyword = crud.normalize_keyword(q)
    active_category = crud.normalize_category(category)

    events = crud.get_events(db, q=keyword, category=active_category)
    total = crud.count_events(db, q=keyword, category=active_category)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            # 数据库对象转成对外结构，模板里的字段语义更清晰
            "events": [schemas.EventOut.model_validate(event) for event in events],
            "total": total,
            # 保留用户输入（已去空格），刷新后筛选条件仍然可见
            "keyword": keyword or "",
            "active_category": active_category or "全部",
            "has_filter": bool(keyword or active_category),
        },
    )


@router.get("/events/{event_id}", response_class=HTMLResponse, name="event_detail")
def event_detail_page(
    request: Request,
    event_id: str,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """活动详情页；活动 ID 非法或不存在时返回 404 页面。"""
    # 手动解析 ID：这样 /events/abc 也会得到友好的 404 页面，
    # 而不是 FastAPI 默认的 422 JSON 校验错误。
    if not event_id.isdigit():
        return render_404(request, f"「{event_id}」不是一个有效的活动编号。")

    event = crud.get_event(db, int(event_id))
    if event is None:
        return render_404(request, f"没有找到编号为 {event_id} 的活动，它可能已经被移除。")

    return templates.TemplateResponse(
        request=request,
        name="event_detail.html",
        context={"event": schemas.EventOut.model_validate(event)},
    )