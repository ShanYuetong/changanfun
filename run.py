"""本地启动脚本。

用法：
    python run.py

默认绑定 127.0.0.1:8000（只允许本机访问，不会暴露到公网）。
如需修改，可设置环境变量 CHANGAN_HOST / CHANGAN_PORT。
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    host = os.environ.get("CHANGAN_HOST", "127.0.0.1")
    port = int(os.environ.get("CHANGAN_PORT", "8000"))

    print("=" * 56)
    print("  长安玩乐指南 · Chang'an Play Guide")
    print("=" * 56)
    print(f"  网站首页：  http://{host}:{port}/")
    print(f"  API 文档：  http://{host}:{port}/docs")
    print(f"  健康检查：  http://{host}:{port}/api/health")
    print("  按 Ctrl+C 停止服务")
    print("=" * 56)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
    )