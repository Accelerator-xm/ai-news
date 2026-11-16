from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

# 数据库URL
ASYNC_DATABASE_URL = "mysql+aiomysql://root:123456@localhost:3306/news_app?charset=utf8mb4"

# 创建异步引擎
## pool_size：连接池会维持 N 个空闲连接放在池里复用，避免反复创建 / 销毁连接（开销大）
## max_overflow：常驻连接全部被占用，又来了新请求，临时扩容。用完归还之后，直接关闭
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,  # 可选：输出SQL日志
    pool_size=10,  # 设置连接池中保持的持久连接数
    max_overflow=20  # 设置连接池允许创建的额外连接数
)

# 创建异步会话工厂
## 用于创建 AsyncSession 对象
## Session 是 SQLAlchemy 的工作单元，内部持有事务、缓存、ORM 对象，按需去连接池拿连接
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# 依赖项，用于获取数据库会话
async def get_db():
    # 获取 AsyncSession 对象
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # 第一次 await session.execute(...) 时从连接池获取连接，然后执行数据库操作
            # session.close() 时归还连接和 AsyncSession 对象
            await session.close()
