# 长安玩乐指南 · Chang'an Play Guide

面向西安大学生的本地娱乐信息聚合网站。用最基础的 Python Web 技术栈，
把电影、展览、演出、校园活动和休闲娱乐信息集中在一个页面里，支持**关键词搜索**、
**分类筛选**和**活动详情**查看。

> ⚠️ **数据说明**：本项目内置的活动、场次和价格全部是**为了演示功能而虚构的示例数据**，
> 不是从任何票务平台采集的实时信息，也不代表真实票价或票务状态。
> 每条记录的「数据来源」字段和页面底部都会明确标注这一点。请勿据此安排实际出行。

---

## 1. 运行环境

| 项目 | 要求 |
| --- | --- |
| Python | **3.11 或更高**（本项目在 Python 3.13.14 + Windows 上开发与测试通过） |
| 数据库 | SQLite（Python 自带，无需单独安装） |
| 浏览器 | Chrome / Edge / Firefox / Safari 等现代浏览器 |

主要依赖（版本已在 `requirements.txt` 中固定）：

- FastAPI 0.115.6 —— Web 框架
- Uvicorn 0.34.0 —— ASGI 服务器
- Jinja2 3.1.5 —— HTML 模板
- SQLAlchemy 2.0.36 —— 数据库 ORM
- Pydantic 2.10.4 —— 数据校验
- pytest 8.3.4 + httpx 0.28.1 —— 自动化测试

---

## 2. 快速开始

### Windows PowerShell

```powershell
# 1. 创建虚拟环境
py -3 -m venv .venv

# 2. 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 3. 安装依赖
python -m pip install -r requirements.txt

# 4. 启动网站
python run.py
```

> **如果第 2 步报错**「无法加载文件 …Activate.ps1，因为在此系统上禁止运行脚本」，
> 说明 PowerShell 的执行策略限制了脚本运行。**不需要修改系统设置**，
> 直接调用虚拟环境里的 Python 即可，效果完全相同：
>
> ```powershell
> .\.venv\Scripts\python.exe -m pip install -r requirements.txt
> .\.venv\Scripts\python.exe run.py
> ```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

### 启动后访问

服务默认绑定 `127.0.0.1:8000`（仅本机可访问，不会暴露到公网）：

| 用途 | 地址 |
| --- | --- |
| 网站首页 | <http://127.0.0.1:8000/> |
| API 文档（Swagger） | <http://127.0.0.1:8000/docs> |
| 健康检查 | <http://127.0.0.1:8000/api/health> |

停止服务：在终端按 `Ctrl + C`。

---

## 3. 功能一览

### 网站页面

- **首页 `/`**
  - 网站名称、产品介绍、搜索框、分类导航
  - 活动卡片列表：标题、分类、地点、时间、价格、简介摘要
  - 分类图标为内联 SVG（不依赖系统字体，跨设备渲染一致）
  - 卡片按分类显示不同主色的顶部色带，并有错峰的入场动效
  - 结果数量提示；数据为空时显示友好的空状态与返回入口
  - 底部固定展示演示数据声明与版本号
- **搜索与分类筛选**
  - 关键词同时匹配**标题、地点、简介**，支持中文，自动忽略前后空格（含全角空格）
  - 5 个分类：电影 / 展览 / 演出 / 校园活动 / 休闲娱乐，选中项高亮显示
  - 搜索与分类可以**同时生效**；页面展示「当前条件」并支持单独或一键清除
  - 全部通过 URL 查询参数（`?q=...&category=...`）实现，**刷新后条件保留**，
    禁用 JavaScript 也能正常使用
- **活动详情 `/events/{id}`**
  - 顶部按分类变色的渐变色带作为视觉锚点
  - 标题、分类、地点、起止时间、价格、详细介绍、数据来源声明、返回列表链接
  - 不存在或非数字的活动 ID 返回**统一的 404 页面**（不是服务器错误）

### 可安装的 Web 应用（PWA）

网站支持「添加到主屏幕」，安装后像原生应用一样从桌面图标直接打开：

- `manifest.json` 声明应用名称、主题色、启动路径与四种图标（含 Android 自适应所需的 maskable 图标）
- Service Worker 缓存**应用外壳**（HTML / CSS / JS / 图标 / 离线页），
  让二次加载更快，并在断网时显示友好的离线提示页
- **接口数据永不缓存**：`/api/` 请求直接放行到网络，保证活动信息始终是最新的
- 满足条件时页面底部会出现样式统一的「添加到主屏幕」提示条，用户拒绝后不再打扰
- 设置页主题色 `#bf3b2c`，与站点品牌色一致

> 说明：PWA 的完整能力（Service Worker、安装提示）需要 **HTTPS 或 localhost** 环境。
> 本项目默认运行在 `127.0.0.1`，属于 localhost 范畴，因此本地即可测试。
> 若在局域网用 IP 访问（非 HTTPS），Service Worker 不会注册，但**网站功能完全不受影响**。

### JSON API

| 接口 | 说明 |
| --- | --- |
| `GET /api/health` | 服务状态、版本、数据库连通性、当前活动总数 |
| `GET /api/events` | 活动列表，返回 `total / limit / offset / items` |
| `GET /api/events/{event_id}` | 单个活动详情，不存在返回 404 |

`GET /api/events` 支持的可选参数：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `q` | string | 无 | 关键词，匹配标题 / 地点 / 简介 |
| `category` | string | 无 | 活动分类；传 `全部` 等同于不筛选 |
| `limit` | int | 20 | 返回数量，范围 1–100 |
| `offset` | int | 0 | 分页偏移量，≥ 0 |

示例：

```bash
curl "http://127.0.0.1:8000/api/events?q=城墙&category=演出&limit=10&offset=0"
```

参数非法时（如 `limit=0`、`limit=abc`、`offset=-1`）返回 **HTTP 422** 与具体的校验信息；
活动不存在返回 **HTTP 404**。

---

## 4. 项目结构

```text
changan-play-guide/
├── app/
│   ├── __init__.py            # 包信息与版本号
│   ├── config.py              # 集中配置：路径、站点信息、分类、数据库地址
│   ├── database.py            # Engine / Session 工厂 / get_db 依赖注入
│   ├── models.py              # SQLAlchemy 模型（Event）
│   ├── schemas.py             # Pydantic 请求响应结构
│   ├── crud.py                # 数据查询：列表、筛选、搜索、分页、详情
│   ├── seed.py                # 15 条演示数据（集中在此，便于修改）
│   ├── templating.py          # Jinja2 配置、日期过滤器、404 渲染
│   ├── main.py                # FastAPI 应用装配与生命周期
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── pages.py           # 首页、详情页路由
│   │   └── api.py             # /api/* 路由
│   ├── templates/
│   │   ├── base.html          # 统一布局、导航、页脚、PWA meta
│   │   ├── _icons.html        # 内联 SVG 图标宏（不依赖 emoji 字体）
│   │   ├── index.html         # 首页：搜索、分类、卡片、空状态
│   │   ├── event_detail.html  # 活动详情（含分类色带视觉锚点）
│   │   └── 404.html           # 统一错误页面
│   └── static/
│       ├── css/style.css      # 全部样式（含响应式断点与动效）
│       ├── js/main.js         # 体验增强：清空输入、快捷键、SW 注册、安装提示
│       ├── sw.js              # Service Worker（应用外壳缓存）
│       ├── manifest.json      # PWA 应用清单
│       ├── offline.html       # 离线提示页
│       ├── icons/             # 应用图标（SVG + PNG，含 maskable）
│       └── images/            # 预留的本地图片目录
├── tests/
│   ├── conftest.py            # 每个测试独立临时数据库
│   ├── test_pages.py          # 页面、搜索、分类、详情、404
│   ├── test_api.py            # API、分页、参数校验
│   └── test_database.py       # 建表、种子数据、持久化、模型约束
├── data/
│   └── .gitkeep               # SQLite 数据库文件生成在这里（已被 .gitignore 忽略）
├── requirements.txt
├── .gitignore
├── README.md
└── run.py                     # 本地启动脚本
```

### 关键设计说明

- **页面与 API 共用查询逻辑**：两者都调用 `app/crud.py`，
  筛选和搜索代码只有一份实现，不会出现「网页能搜到、接口搜不到」的不一致。
- **数据库路径稳定**：SQLite 文件固定解析到项目根目录下的 `data/changan.db`，
  无论从哪个工作目录启动都不会生成多个数据库。
- **数据初始化幂等**：应用启动时建表；只有活动表为空时才导入示例数据，
  重启不会重复插入，已有数据不会丢失。
- **查询全部参数化**：所有用户输入都通过 SQLAlchemy 表达式传入，
  不存在拼接 SQL 字符串。

---

## 5. 数据库

- 文件位置：`data/changan.db`（首次启动自动创建）
- 表 `events` 的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | 整数主键 | 活动唯一标识 |
| `title` | 字符串，非空 | 活动标题 |
| `category` | 字符串，非空 | 活动分类（建索引） |
| `venue` | 字符串，非空 | 活动地点 |
| `start_time` | 日期时间，非空 | 开始时间（建索引，用于排序） |
| `end_time` | 日期时间，可空 | 结束时间；提供时必须 ≥ 开始时间 |
| `price` | 字符串，非空 | 价格或免费说明 |
| `description` | 文本，非空 | 活动简介 |
| `source` | 字符串，非空 | 数据来源 / 演示数据声明 |
| `created_at` | 日期时间，非空 | 记录创建时间 |

- 时间统一使用**不带时区的北京时间**，全表语义一致，避免时区混用。
- 约束：必要字段 `NOT NULL`；`end_time` 若存在则必须 `>= start_time`
  （数据库 CHECK 约束 + Python 层校验双重保障）。

### 重新初始化 / 清理演示数据

> ⚠️ **先备份再删除**。删除数据库文件会**永久丢失**你自己添加或修改过的数据。

```powershell
# 1. 如果服务正在运行，先按 Ctrl+C 停止
# 2. 备份现有数据库（推荐）
Copy-Item data\changan.db data\changan.backup.db

# 3. 删除数据库文件，下次启动会自动重建并重新导入演示数据
Remove-Item data\changan.db

# 4. 重新启动
python run.py
```

只想修改演示数据的内容（增删条目、改文案）时，编辑 `app/seed.py` 中的
`DEMO_EVENTS` 列表，然后按上面的步骤删除数据库文件并重启即可。

---

## 6. 运行自动化测试

```bash
python -m pytest -q
```

测试使用**独立的临时 SQLite 数据库**（pytest 的 `tmp_path`），
每个测试函数互不影响，也不会读写、修改 `data/changan.db`。
测试覆盖：首页状态码、卡片渲染、中文搜索、分类筛选、搜索+分类组合、空状态、
详情页、不存在的 ID、健康检查、列表 / 详情 API、分页、参数校验（422）、
数据库幂等初始化、持久化与模型约束。

---

## 7. 常见问题

**Q1：提示「python 不是内部或外部命令」/ 找不到 Python？**

先检查是否安装并加入了 PATH：

```powershell
py -0p              # 列出系统里所有 Python 版本及路径
python -V           # 查看默认版本
```

如果 `py` 可用但 `python` 不可用，就用 `py -3` 代替所有命令中的 `python`。
Windows 上如果 `python` 打开的是应用商店页面，说明系统装了「应用执行别名」，
请改用 `py -3`，或在「设置 → 应用 → 高级应用设置 → 应用执行别名」中关闭
`python.exe` / `python3.exe` 的别名。

**Q2：`pip install` 失败怎么办？**

1. 确认调用的是虚拟环境里的 pip：`.\.venv\Scripts\python.exe -m pip --version`
   输出的路径应包含 `.venv`；
2. 检查网络。国内网络可加镜像：
   `python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
3. 报编译错误时，先尝试升级 pip：`python -m pip install --upgrade pip`
4. 本项目所有依赖都有预编译 wheel，**不需要** C++ 编译环境。

**Q3：端口 8000 被占用（`address already in use`）？**

换一个端口启动即可，不需要修改代码：

```powershell
$env:CHANGAN_PORT="8001"
python run.py
```

或者先查出占用进程并结束它：

```powershell
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
```

**Q4：数据库文件在哪里？**

`data/changan.db`（相对项目根目录）。路径由 `app/config.py` 统一管理，
始终基于项目根目录解析，与当前工作目录无关。

**Q5：如何重启服务？**

在运行服务的终端按 `Ctrl + C`，然后重新执行 `python run.py`。
重启不会丢失数据，也不会重复插入演示数据。

**Q6：如何清理演示数据或重新初始化？**

见上文「重新初始化 / 清理演示数据」一节。**删除前请先备份**。

**Q7：怎样运行自动化测试？**

`python -m pytest -q`。加 `-v` 可以看到每个用例的名字；
只想跑某一类测试可以指定文件，例如 `python -m pytest tests/test_api.py -q`。

**Q8：页面样式没有生效？**

确认服务是从项目根目录启动的（`python run.py`），并强制刷新浏览器
（Windows：`Ctrl + F5`）。静态文件通过 `/static/...` 提供，可先直接访问
<http://127.0.0.1:8000/static/css/style.css> 确认是否返回 200。

---

## 8. 第一版没有实现的功能

以下内容**故意没有做**，属于 MVP 之外的规划：

- 用户注册 / 登录 / 个人资料
- 评论、收藏、点赞等社交互动
- 在线支付与购票、实时票务库存
- 大规模网络爬虫与真实数据采集
- 个性化推荐算法
- 多城市切换
- 公网部署

---

## 9. 后续可以怎么改进

1. **数据来源**：接入正规开放数据接口（并提供缓存与失败降级），
   把 `source` 字段从「演示数据」替换为真实来源与抓取时间。
2. **管理后台**：做一个简单的活动增删改页面，替代直接编辑 `seed.py`。
3. **筛选增强**：按时间范围（本周末 / 本周）、免费场次筛选；给分类加重叠标签。
4. **地图与路线**：活动地点支持一键跳转地图，方便规划周末路线。
5. **分页 UI**：目前 API 已支持 `limit` / `offset`，页面可加「加载更多」。
6. **部署**：使用 Uvicorn + Nginx 部署到服务器，补充日志与监控。

---

## 10. 版本

v1.0.0 —— 第一个可运行的完整版本：页面浏览、搜索、分类筛选、详情、JSON API、
SQLite 持久化与自动化测试。