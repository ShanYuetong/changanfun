"""模板引擎配置。

把 Jinja2 的创建、全局变量与格式化过滤器集中在这里，
页面路由 (routers/pages.py) 与错误页渲染都复用同一个 templates 对象，
避免同一份配置散落在多个文件里。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import config

templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


def format_datetime_cn(value: datetime | None) -> str:
    """把 datetime 格式化为「2026年03月14日 19:30」这种中文写法。"""
    if value is None:
        return "时间待定"
    return f"{value.year}年{value.month:02d}月{value.day:02d}日 {value.hour:02d}:{value.minute:02d}"


def format_time_range_cn(start: datetime | None, end: datetime | None) -> str:
    """格式化时间区间；同一天时省略重复的日期部分，列表阅读更轻松。"""
    if start is None:
        return "时间待定"
    if end is None:
        return format_datetime_cn(start)
    if start.date() == end.date():
        return f"{format_datetime_cn(start)} — {end.hour:02d}:{end.minute:02d}"
    return f"{format_datetime_cn(start)} — {format_datetime_cn(end)}"


def render_404(request: Request, message: str) -> HTMLResponse:
    """渲染统一的 404 页面，供页面路由与全局异常处理复用。"""
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={"message": message},
        status_code=404,
    )


def setup_templates() -> None:
    """注册过滤器与全局变量（每个模板都能直接使用站点信息）。"""
    templates.env.filters["datetime_cn"] = format_datetime_cn
    templates.env.filters["timerange_cn"] = format_time_range_cn
    templates.env.globals.update(
        app_name=config.APP_NAME,
        app_name_en=config.APP_NAME_EN,
        app_tagline=config.APP_TAGLINE,
        app_version=config.APP_VERSION,
        demo_notice=config.DEMO_NOTICE,
        categories=config.CATEGORIES,
        category_icons=config.CATEGORY_ICONS,
        category_colors=config.CATEGORY_COLORS,
        all_icon=config.ALL_ICON,
    )