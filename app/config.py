"""应用配置。

所有可配置项集中在这里，避免在代码各处散落魔法字符串与硬编码路径。
数据库地址通过环境变量 CHANGAN_DATABASE_URL 管理，
测试时由 conftest.py 注入临时数据库地址，从而隔离测试数据。
"""

from __future__ import annotations

import os
from pathlib import Path

# 项目根目录：本文件位于 <项目根>/app/config.py，向上两级即项目根
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录（数据库文件默认放在这里）
DATA_DIR = BASE_DIR / "data"

# 模板目录与静态文件目录
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

# 网站元信息，模板与页脚统一从这里取，避免重复书写
APP_NAME = "长安玩乐指南"
APP_NAME_EN = "Chang'an Play Guide"
APP_TAGLINE = "发现西安的电影、展览、演出与校园周末好去处"
APP_VERSION = "1.0.0"

# 演示数据声明：页面上必须明确告知用户这是示例数据
DEMO_NOTICE = "本站当前展示的是本地演示数据（示例活动），并非实时票务或活动信息。"

# 默认数据库地址：SQLite 文件固定解析到项目根目录下的 data/changan.db，
# 这样无论从哪个工作目录启动，都不会生成多个数据库文件。
DEFAULT_DATABASE_FILE = DATA_DIR / "changan.db"


def get_database_url() -> str:
    """返回数据库连接地址。

    优先读取环境变量 CHANGAN_DATABASE_URL（测试用它指向临时数据库），
    否则使用项目根目录下的 data/changan.db。
    """
    env_url = os.environ.get("CHANGAN_DATABASE_URL")
    if env_url:
        return env_url
    return f"sqlite:///{DEFAULT_DATABASE_FILE.as_posix()}"


def ensure_data_dir() -> None:
    """确保 data 目录存在，避免首次创建 SQLite 文件时报错。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# 活动分类（顺序即页面导航顺序，"全部"由页面单独处理）
CATEGORIES = ["电影", "展览", "演出", "校园活动", "休闲娱乐"]

# 每个分类对应的图标（纯 emoji/字符，不依赖外部图片）
CATEGORY_ICONS = {
    "电影": "🎬",
    "展览": "🖼️",
    "演出": "🎭",
    "校园活动": "🎓",
    "休闲娱乐": "🍃",
}