# 后端开发笔记

后端开发从处理一次请求开始：解析输入，验证数据，执行查询或计算，再返回约定的结果。Python 提供对象、函数和协程，FastAPI 组织接口与资源生命周期，数据库与缓存负责不同的数据访问需求。

| 主题 | 内容 |
| --- | --- |
| [Python](python.md) | 对象与容器、函数与类型提示、dataclass、生成器、异常、异步、时间与 JSON |
| [FastAPI](fastapi.md) | 路由和参数、Pydantic 校验、序列化、依赖注入、响应、生命周期与跨域 |
| [SQLAlchemy](sqlalchemy.md) | 表映射、查询结果、Session、对象状态、事务、关系加载和索引 |
| [认证](authentication.md) | 密码哈希、盐与计算成本、Token、会话与权限边界 |
| [Redis](redis.md) | 数据序列化、旁路缓存、键设计、失效与一致性 |
| [AI 对话](ai.md) | 上下文、协议适配、SSE 分帧、浏览器流读取与取消清理 |

可以先阅读 Python 和 FastAPI，再沿着数据读写理解 SQLAlchemy、认证和 Redis。AI 对话将异步生成器、HTTP 连接和前端流读取结合起来，适合在理解这些基础后继续阅读。
