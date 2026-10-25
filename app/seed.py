"""初始示例数据（演示数据）。

⚠️ 重要说明：
下面的活动、场次与价格全部是**为了演示网站功能而虚构的示例数据**，
不是从任何票务平台采集的实时信息。所有记录的 source 字段都明确写明这一点，
页面与 API 也会原样展示该声明。

如果需要修改示例数据，只需改动本文件中的 DEMO_EVENTS 列表。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Event

# 统一的演示数据声明文字
DEMO_SOURCE = "演示数据 · 示例活动，非实时信息"

# 15 条演示数据，覆盖全部 5 个分类（每个分类 3 条）
# 时间统一使用不带时区的北京时间写法。
DEMO_EVENTS: list[dict[str, object]] = [
    # ---------------- 电影 ----------------
    {
        "title": "《长安夜航》校园超前点映",
        "category": "电影",
        "venue": "小寨星光影城 3 号厅",
        "start_time": datetime(2026, 3, 14, 19, 30),
        "end_time": datetime(2026, 3, 14, 21, 35),
        "price": "示例票价 35 元（学生场）",
        "description": (
            "一部以唐代长安城为背景的虚构剧情片，讲述一位年轻画师在一夜之间"
            "寻找失落画稿的故事。点映场结束后安排十五分钟的映后交流，"
            "由影迷社团的同学主持讨论。座位有限，建议提前到场。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "经典修复电影《城墙上空的云》重映",
        "category": "电影",
        "venue": "钟楼电影资料馆 1 号放映厅",
        "start_time": datetime(2026, 3, 15, 14, 0),
        "end_time": datetime(2026, 3, 15, 16, 10),
        "price": "示例票价 25 元",
        "description": (
            "经过数字修复的老电影重映，画面中保留了大量上世纪八十年代"
            "西安城墙与老街巷的影像。适合对城市记忆和纪录片风格感兴趣的同学，"
            "放映前会有十分钟的修复过程介绍。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "露天电影夜：《秦岭的风》",
        "category": "电影",
        "venue": "曲江青年文化广场露天映区",
        "start_time": datetime(2026, 3, 20, 20, 0),
        "end_time": datetime(2026, 3, 20, 22, 0),
        "price": "免费（需自带坐垫）",
        "description": (
            "在广场草地上放映的自然题材影片，讲述秦岭深处护林员的日常。"
            "现场提供少量折叠椅，也可以自带坐垫和外套。春季夜间气温偏低，"
            "建议穿厚一点。遇雨顺延。"
        ),
        "source": DEMO_SOURCE,
    },
    # ---------------- 展览 ----------------
    {
        "title": "「砖瓦之间」唐代建筑构件特展",
        "category": "展览",
        "venue": "碑林区城市博物馆 二层临展厅",
        "start_time": datetime(2026, 3, 1, 9, 0),
        "end_time": datetime(2026, 4, 30, 17, 0),
        "price": "免费（需现场登记）",
        "description": (
            "通过瓦当、砖雕与斗拱模型，介绍唐代建筑的基本结构与装饰语言。"
            "展厅内有可触摸的复制构件与拓印体验区，适合建筑、历史和设计专业的同学"
            "做课程参考。周末人流较多，工作日上午相对安静。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "青年影像联展：我们的街区",
        "category": "展览",
        "venue": "纺织城艺术区 C 栋展厅",
        "start_time": datetime(2026, 3, 7, 10, 30),
        "end_time": datetime(2026, 3, 22, 18, 0),
        "price": "示例票价 20 元（学生凭证 10 元）",
        "description": (
            "由本地高校摄影社团联合策划的影像展，主题是西安不同街区的日常生活。"
            "展品包括胶片照片、手机短片与声音记录。展厅旁边设有留言墙，"
            "观众可以写下自己熟悉的街区故事。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "「长安一日」插画原作展",
        "category": "展览",
        "venue": "大雁塔南广场文创小院 A 厅",
        "start_time": datetime(2026, 3, 10, 11, 0),
        "end_time": datetime(2026, 3, 29, 20, 0),
        "price": "免费",
        "description": (
            "十二位年轻插画作者以「在长安的一天」为题创作的系列原作。"
            "从早市的胡辣汤到傍晚的城墙骑行，画面里都是学生熟悉的城市细节。"
            "现场提供明信片盖章台，可以带走一张自己涂色的线稿。"
        ),
        "source": DEMO_SOURCE,
    },
    # ---------------- 演出 ----------------
    {
        "title": "校园民谣专场：城墙下的六把吉他",
        "category": "演出",
        "venue": "小寨 Livehouse 小厅",
        "start_time": datetime(2026, 3, 13, 20, 0),
        "end_time": datetime(2026, 3, 13, 22, 0),
        "price": "示例票价 60 元（预售 45 元）",
        "description": (
            "六位高校原创音乐人轮番登台，曲目以民谣与城市民谣为主，"
            "歌词大量取材于西安的校园与街巷。演出中间设有开放麦环节，"
            "报名可在入场处登记，每人限一首。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "小剧场话剧《寄存处》",
        "category": "演出",
        "venue": "南门里黑盒剧场",
        "start_time": datetime(2026, 3, 21, 19, 30),
        "end_time": datetime(2026, 3, 21, 21, 20),
        "price": "示例票价 80 元",
        "description": (
            "一部发生在火车站寄存处的双人话剧，全剧只有两位演员和一个行李架。"
            "剧本由本地青年剧社原创，演出时长约 100 分钟，中场不休息。"
            "剧场座位不到百个，视线都比较好。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "秦腔新编折子戏学生专场",
        "category": "演出",
        "venue": "易俗社小剧场",
        "start_time": datetime(2026, 3, 28, 15, 0),
        "end_time": datetime(2026, 3, 28, 16, 40),
        "price": "示例票价 30 元（学生凭证 15 元）",
        "description": (
            "在传统秦腔折子戏基础上做了适合年轻观众的精简改编，"
            "演出前有二十分钟的唱腔与行当讲解。字幕投屏同步显示唱词，"
            "即使第一次听秦腔也能跟上剧情。"
        ),
        "source": DEMO_SOURCE,
    },
    # ---------------- 校园活动 ----------------
    {
        "title": "春季社团招新市集",
        "category": "校园活动",
        "venue": "长安大学城 中心广场",
        "start_time": datetime(2026, 3, 8, 10, 0),
        "end_time": datetime(2026, 3, 8, 17, 0),
        "price": "免费",
        "description": (
            "四十多个学生社团集中摆摊，包括天文、话剧、骑行、汉服与机器人等。"
            "现场有小型舞台轮番表演，也设置了新生咨询台。"
            "适合刚入学、还没决定加入哪个社团的同学一次逛完。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "跨校读书会：一起读《城市与人》",
        "category": "校园活动",
        "venue": "高校图书馆 三层讨论室",
        "start_time": datetime(2026, 3, 12, 18, 30),
        "end_time": datetime(2026, 3, 12, 20, 30),
        "price": "免费（需提前报名）",
        "description": (
            "由三所高校读书会联合组织的月度共读活动，本期主题是城市空间与日常生活。"
            "讨论分为小组分享与自由发言两段，不需要提前读完，"
            "现场会发放章节摘录。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "校园开放日：实验室参观与科普讲座",
        "category": "校园活动",
        "venue": "理工大学 科技楼 B 座",
        "start_time": datetime(2026, 3, 22, 9, 30),
        "end_time": datetime(2026, 3, 22, 16, 0),
        "price": "免费",
        "description": (
            "面向全市大学生的开放日活动，可以参观材料、机器人与地理信息实验室，"
            "并参加三场通俗科普讲座。每组参观由在读研究生带队讲解，"
            "适合想了解其他专业方向的同学。"
        ),
        "source": DEMO_SOURCE,
    },
    # ---------------- 休闲娱乐 ----------------
    {
        "title": "环城公园春日骑行集合",
        "category": "休闲娱乐",
        "venue": "环城公园 南门集合点",
        "start_time": datetime(2026, 3, 15, 9, 0),
        "end_time": datetime(2026, 3, 15, 12, 0),
        "price": "免费（自行车自备或现场租）",
        "description": (
            "沿城墙根绕行一圈的轻松骑行，全程约十四公里，速度以能聊天为准。"
            "中途在公园东段休息补水。参加者需自带头盔，"
            "没有自行车的同学可以在集合点附近租用。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "老菜场夜市闲逛指南",
        "category": "休闲娱乐",
        "venue": "建国门老菜场创意街区",
        "start_time": datetime(2026, 3, 16, 17, 30),
        "end_time": None,
        "price": "免费入场（消费自理）",
        "description": (
            "由菜市场改造的街区，傍晚开始逐渐热闹，摊位以小吃、旧物和手作为主。"
            "街区不大，一小时可以逛完，适合和同学边吃边聊。"
            "没有固定结束时间，多数摊位在晚上十点前后收摊。"
        ),
        "source": DEMO_SOURCE,
    },
    {
        "title": "桌游与自习共享空间体验夜",
        "category": "休闲娱乐",
        "venue": "纬二街 共享空间二层",
        "start_time": datetime(2026, 3, 19, 18, 0),
        "end_time": datetime(2026, 3, 19, 22, 0),
        "price": "示例价格 15 元/人（含一杯饮品）",
        "description": (
            "白天是自习区，晚上开放为桌游区，提供三十余款轻中度策略桌游。"
            "现场有志愿者负责讲解规则，一个人来也可以拼桌。"
            "桌面插座充足，适合带电脑的同学先自习再玩。"
        ),
        "source": DEMO_SOURCE,
    },
]


def seed_if_empty(session: Session) -> int:
    """当数据库为空时导入示例数据，返回本次插入的条数。

    幂等保证：只要 events 表里已有任意记录就直接跳过，
    因此应用反复重启不会重复插入同一批示例数据。
    """
    existing = session.scalar(select(func.count()).select_from(Event)) or 0
    if existing > 0:
        return 0

    for item in DEMO_EVENTS:
        session.add(Event(**item))  # type: ignore[arg-type]
    session.commit()
    return len(DEMO_EVENTS)