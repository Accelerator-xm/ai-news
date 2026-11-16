# AI News · 新闻 Demo 与学习笔记

一个前后端分离的新闻应用 Demo，以及围绕后端开发整理的知识笔记。应用源码集中在 `ai-news/`，笔记保存在 `docs/`，两者可以独立阅读和使用。

**在线笔记：[AI News 学习笔记](https://accelerator-xm.github.io/ai-news/)**

## 项目介绍

Demo 支持新闻分类、分页列表、详情与相关新闻、注册登录、收藏和浏览历史。AI 问答提供通用多轮对话，支持流式输出、停止生成、重新生成和复制回答。

| 部分 | 技术与职责 |
| --- | --- |
| 前端 | Vue 3、Vite、Vant、Pinia，负责页面交互与流式内容展示 |
| 后端 | FastAPI、Pydantic 2，负责接口、数据校验和身份认证 |
| 数据访问 | SQLAlchemy 2 异步 ORM、MySQL，保存新闻、用户、收藏与历史 |
| 缓存 | Redis，缓存新闻分类、列表和详情 |
| AI 服务 | 后端管理供应商配置，通过 SSE 转发回答，支持 Chat Completions 兼容接口和 Anthropic 原生接口 |

AI 调用链路为 `浏览器 → FastAPI → 模型供应商`。密钥与模型配置保存在后端，前端只提交对话消息；通用问答不会自动附带新闻内容。配置项见 [后端配置示例](ai-news/backend/.env.example)。

## 环境配置

| 环境 | 版本 |
| --- | --- |
| Python | 3.12，使用 Conda 管理环境 |
| Conda | Miniconda 或 Anaconda 均可 |
| Node.js | 推荐 22.12+，也支持 20.19+ 的 20.x 版本 |
| MySQL | 8.x，Compose 使用 8.4 |
| Redis | 7.x |
| Docker Compose | 可选，用于启动 MySQL 和 Redis |

以下终端命令使用 Linux / WSL 的 Bash，默认从仓库根目录开始。先安装 Miniconda 或 Anaconda，Python 环境在启动步骤中通过 Conda 创建。首次运行先复制配置模板；`cp -n` 会保留已有文件：

```bash
cp -n ai-news/backend/.env.example ai-news/backend/.env
cp -n ai-news/frontend/.env.example ai-news/frontend/.env
```

| 配置位置 | 内容 |
| --- | --- |
| [后端数据库配置](ai-news/backend/config/db_conf.py) | `ASYNC_DATABASE_URL`，默认连接 `localhost:3306/news_app`，用户名 `root`，密码 `123456` |
| [后端缓存配置](ai-news/backend/config/cache_conf.py) | `REDIS_HOST`、`REDIS_PORT`、`REDIS_DB`，默认 `localhost:6379`、数据库 `0` |
| `ai-news/backend/.env` | AI 供应商地址、密钥、模型及生成参数 |
| `ai-news/frontend/.env` | `VITE_API_BASE_URL`，默认 `http://127.0.0.1:8000` |

MySQL 和 Redis 当前直接读取上述 Python 配置，连接参数不从 `.env` 加载。使用自己的数据库或缓存服务时，修改对应配置文件。前端环境变量修改后需要重启开发服务器，或重新构建。

使用 AI 问答时，在 `ai-news/backend/.env` 中填写自己的配置：

```dotenv
AI_PROVIDER=openai
AI_BASE_URL=https://供应商域名/v1
AI_API_KEY=填写自己的密钥
AI_MODEL=填写该账号可用的模型名称
```

`openai` 表示 Chat Completions 兼容协议，可连接支持该协议的供应商或中转站；Anthropic 原生 Messages 协议使用 `AI_PROVIDER=anthropic`。`AI_BASE_URL` 可以填写基础地址或完整接口地址，后端会按协议补全路径。

其他参数见 [配置模板](ai-news/backend/.env.example)：`AI_TIMEOUT` 控制超时，`AI_MAX_TOKENS` 控制输出预算，`AI_TOKEN_PARAMETER` 可选 `max_tokens` 或 `max_completion_tokens`；`AI_EXTRA_HEADERS` 和 `AI_EXTRA_BODY` 接受 JSON 对象。`AI_SYSTEM_PROMPT` 默认留空。密钥仅保存在后端 `.env`，该文件已被 Git 忽略；不配置 AI 密钥也可以使用新闻功能。

## 启动 Demo

### 数据库与缓存

使用 Docker Compose 启动：

```bash
docker compose -f ai-news/compose.yaml up -d --wait
```

Compose 将 MySQL 和 Redis 分别映射到本机 `3306`、`6379` 端口，连接参数与后端默认配置一致。首次使用空数据卷时，会自动导入 `ai-news/database/database.sql`；数据卷已初始化后不会重复导入。

如果使用本机 MySQL 和 Redis，先启动这两个服务。全新数据库可以连接 MySQL 后使用 SOURCE 初始化：

```bash
mysql --default-character-set=utf8mb4 -h 127.0.0.1 -P 3306 -u root -p
```

在 MySQL 客户端中执行，将路径替换为实际仓库的绝对路径：

```sql
SOURCE /仓库绝对路径/ai-news/database/database.sql;
```


### 后端

从仓库根目录新开终端，创建并激活 Conda 环境，再安装依赖、启动接口服务：

```bash
conda create -n ai-news python=3.12 -y
conda activate ai-news
cd ai-news/backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Conda 环境只需创建一次，以后运行先执行 `conda activate ai-news`。如果已有其他 Python 3.12 的 Conda 环境，也可以直接使用。后端应在 `ai-news/backend/` 目录运行，接口文档地址为 <http://127.0.0.1:8000/docs>。

### 前端

从仓库根目录再开一个终端：

```bash
cd ai-news/frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

浏览器访问 <http://127.0.0.1:5173/>，前端通过 `VITE_API_BASE_URL` 指定的地址请求后端。

## 学习笔记

笔记以知识点和代码示例为主，部分示例取自 Demo，补充对象状态、校验与序列化、异步执行和资源管理等原理。笔记源码入口：[笔记首页](docs/index.md)。

| 主题 | 内容 |
| --- | --- |
| [Python](docs/python.md) | 对象与容器、函数与类型提示、dataclass、生成器、异常、异步、时间与 JSON |
| [FastAPI](docs/fastapi.md) | 路由和参数、Pydantic 校验、输出模型、依赖注入、响应与生命周期 |
| [SQLAlchemy](docs/sqlalchemy.md) | 表映射、查询结果、Session、对象状态、事务、关系加载与索引 |
| [密码与认证](docs/authentication.md) | 密码哈希、盐与计算成本、Token、会话与权限边界 |
| [Redis](docs/redis.md) | 序列化、旁路缓存、键设计、过期与一致性 |
| [AI 对话](docs/ai.md) | 上下文、供应商协议适配、SSE 分帧、浏览器流读取与取消清理 |

## 本地阅读笔记

笔记可以独立启动，不需要运行前后端、MySQL 或 Redis。从仓库根目录新开终端执行：

```bash
conda create -n ai-news-docs python=3.12 -y
conda activate ai-news-docs
python -m pip install -r requirements-docs.txt
python -m mkdocs serve --dev-addr 127.0.0.1:8001
```

`ai-news-docs` 环境只需创建一次，后续激活后即可启动笔记。浏览器访问 <http://127.0.0.1:8001/>，修改 Markdown 后会自动刷新页面。

## 目录

```text
./                              # 仓库根目录
├── ai-news/                     # 可运行的新闻 Demo
│   ├── backend/
│   │   ├── routers/             # API 路由
│   │   ├── schemas/             # 输入校验与输出模型
│   │   ├── models/              # 数据库表映射
│   │   ├── crud/                # 数据读写
│   │   ├── cache/               # 新闻缓存操作
│   │   ├── services/            # AI 协议适配与流转发
│   │   ├── config/              # 数据连接与 AI 配置
│   │   └── utils/               # 认证、密码哈希等工具
│   ├── frontend/               # Vue 页面
│   ├── database/               # 初始化 SQL 与迁移脚本
│   └── compose.yaml            # 本地 MySQL 与 Redis
├── docs/                        # Markdown 笔记与页面样式
├── mkdocs.yml                   # 笔记网站的主题与导航
├── requirements-docs.txt        # 文档构建依赖
├── .github/workflows/docs.yml   # 笔记构建与发布工作流
└── README.md
```
