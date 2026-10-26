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


# ---------------- 写接口（新增活动）的访问控制 ----------------
# 添加活动属于写操作，不能对所有人开放，否则任何人都能污染数据。
# 密钥通过环境变量 CHANGAN_ADMIN_TOKEN 提供；未设置时写接口一律拒绝（fail closed），
# 而不是「没配置就放行」——后者是常见的安全事故来源。
ADMIN_TOKEN_ENV = "CHANGAN_ADMIN_TOKEN"


def get_admin_token() -> str | None:
    """返回当前配置的管理密钥；未配置时返回 None。"""
    token = os.environ.get(ADMIN_TOKEN_ENV)
    if token is None:
        return None
    token = token.strip()
    return token or None


# 活动分类（顺序即页面导航顺序，"全部"由页面单独处理）
CATEGORIES = ["电影", "展览", "演出", "校园活动", "休闲娱乐"]

# 每个分类对应的图标标识。
# 这里只存 key，真正的 SVG 图形放在 templates/_icons.html 里，
# 用 SVG 而不是 emoji 的原因：emoji 在 Windows / macOS / Android 上
# 由不同字体渲染，字形、粗细、配色都不一致，看起来像拼凑；
# SVG 用 currentColor 继承文字颜色，跨系统完全一致，且总体积不到 3 KB。
CATEGORY_ICONS = {
    "电影": "film",
    "展览": "gallery",
    "演出": "stage",
    "校园活动": "campus",
    "休闲娱乐": "leisure",
}

# 「全部」分类的图标
ALL_ICON = "sparkle"

# 每个分类的主题色（用于详情页色带、卡片强调）。
# 主色仍为朱红，#bf3b2c 是品牌色；其余为各分类的辅助色。
CATEGORY_COLORS = {
    "电影": ("#bf3b2c", "#e08a4a"),      # 朱红 → 橙
    "展览": ("#2f6f9f", "#5fa8c9"),      # 靛蓝 → 浅蓝
    "演出": ("#7a3b8f", "#b06fc4"),      # 紫 → 浅紫
    "校园活动": ("#2e7d5b", "#5fb08a"),  # 墨绿 → 浅绿
    "休闲娱乐": ("#c47b1e", "#e0a94a"),  # 赭黄 → 浅黄
}