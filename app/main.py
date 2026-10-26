"""FastAPI 应用入口。

职责（尽量只有「装配」）：
1. 创建应用、挂载路由与静态文件；
2. 通过 lifespan 管理数据库初始化与示例数据导入（避免导入模块时写盘）；
3. 配置统一的 404 处理。
具体的模板配置在 app/templating.py，业务查询在 app/crud.py。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as http_exception_default_handler
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config, seed
from app.database import get_engine, get_session_factory
from app.models import Base
from app.routers import api, pages
from app.templating import render_404, setup_templates


def init_database() -> None:
    """创建表结构；数据库为空时导入示例数据。

    该函数是幂等的：已存在的表不会被重建，已有数据不会重复插入，
    因此应用反复重启也不会产生重复的示例数据。
    """
    Base.metadata.create_all(bind=get_engine())

    session_factory = get_session_factory()
    with session_factory() as session:
        seed.seed_if_empty(session)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时初始化数据库，关闭时释放连接。"""
    init_database()
    yield
    # 关闭时释放数据库连接池
    get_engine().dispose()


app = FastAPI(
    title=config.APP_NAME,
    description=(
        f"{config.APP_TAGLINE}。\n\n"
        "**数据说明**：本站所有活动均为本地演示数据，不是实时采集的真实活动信息。"
    ),
    version=config.APP_VERSION,
    lifespan=lifespan,
)

# 模板过滤器与全局变量
setup_templates()

# 静态文件（CSS / JS）
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")


# Service Worker 必须从站点根路径提供，否则它的默认作用域会被限制在 /static/ 下，
# 无法接管页面导航请求。/static/sw.js 仍保留，便于直接查看看源码。
@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    """以根路径提供 Service Worker，使其作用域覆盖整个站点。"""
    return FileResponse(
        config.STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={
            # 浏览器更新 SW 时会走 HTTP 缓存，这里强制每次校验，避免用户长期用旧版本
            "Cache-Control": "no-cache, must-revalidate",
            # 允许 SW 控制根路径下的所有页面
            "Service-Worker-Allowed": "/",
        },
    )

# 路由注册：页面路由在前，API 路由统一挂在 /api 前缀下
app.include_router(pages.router)
app.include_router(api.router, prefix="/api")


# ---------------- 统一的错误处理 ----------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    """404 时页面返回 HTML 错误页、API 返回 JSON；其余状态码保持 FastAPI 默认行为。"""
    if exc.status_code != 404:
        # 422 等其它状态码沿用默认响应，避免影响接口契约
        return await http_exception_default_handler(request, exc)

    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": exc.detail or "资源不存在"})

    return render_404(request, "你访问的页面不存在，可能链接已经失效。")


@app.get("/health", response_class=HTMLResponse, include_in_schema=False)
def health_shortcut() -> HTMLResponse:
    """给不熟悉 /api 前缀的同学一个简短提示页。"""
    return HTMLResponse(
        '<meta charset="utf-8">'
        '<p>服务运行中，健康检查请访问 <a href="/api/health">/api/health</a>。</p>'
    )