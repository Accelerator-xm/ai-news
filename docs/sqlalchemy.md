# SQLAlchemy 与数据库

ORM 将 Python 对象映射到关系表，并通过会话跟踪对象变化。它减少了手工装配 SQL 和数据的工作，但数据库仍然负责事务、约束、索引和实际执行。以下使用 SQLAlchemy 2.0 的异步接口。

## 表映射与默认值

DeclarativeBase 收集一组表的 metadata，Mapped 声明映射属性，mapped_column 描述列。多个关联模型通常继承同一个 Base，便于外键解析、统一建表和结构管理。

```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Author(Base):
    __tablename__ = "author"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    articles: Mapped[list["Article"]] = relationship(back_populates="author")

class Article(Base):
    __tablename__ = "article"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))
    views: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    author: Mapped[Author] = relationship(back_populates="articles")
```

`Article.title` 在类上代表可用于 SQL 的映射属性，`article.title` 在实例上代表当前对象的值。数据库外键约束数据引用是否合法，relationship 提供对象之间的导航，两者不是同一功能。

`default=datetime.now` 把函数交给 SQLAlchemy，在生成 INSERT 默认值时调用；`default=datetime.now()` 则会在定义时计算一次。默认值通常在 INSERT / flush 时产生，刚执行 Article(...) 时不能假定已经填充 created_at。

`server_default=func.now()` 是数据库端默认表达式，括号是在构造 SQL 表达式，不是在 Python 中提前获取一个固定时间。`onupdate=datetime.now` 由 SQLAlchemy 在相应 UPDATE 时调用，不等于数据库已经定义了自动更新时间规则。[列默认值](https://docs.sqlalchemy.org/en/20/core/defaults.html)

修改模型只改变程序映射，不会自动改变既有数据库。`metadata.create_all()` 主要创建不存在的表，已有表加列、加唯一约束等仍需要对应的数据库结构变更。

## 查询结果与 CRUD

`await session.execute(stmt)` 返回 Result 系列结果对象，下一步怎么提取决定了拿到的是 ORM 实体、Row 还是映射视图。

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.news import News

async def get_news_list(db: AsyncSession, category_id: int, skip: int = 0, limit: int = 10):
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
```

这是按分类查询新闻的数据库方法：execute 得到结果对象，scalars 取出每行的 News 实体，all 收集成序列。它不负责缓存，也不会自动将 ORM 实体转换为 JSON。

offset 表示跳过多少条，limit 限制当前页数量；页码可以通过 `(page - 1) * page_size` 换算为 skip。需要稳定分页时，还应明确排序，例如 `.order_by(News.publish_time.desc(), News.id.desc())`，相同时间再按主键排序可以减少顺序不确定性。深分页会增加扫描或跳过成本，数据量大时可以考虑按有序字段和主键继续查询的游标分页。

| 查询与取法 | 返回内容 |
| --- | --- |
| `select(News)` 后 `.all()` | Row 序列，每行包含一个 News |
| 同一查询后 `.scalars().all()` | News 对象序列 |
| `select(News.id, News.title)` 后 `.all()` | 含两个选出值的 Row 序列 |
| 同一选列查询后 `.mappings().all()` | 按字段名访问的 RowMapping 序列 |
| `select(func.count(News.id))` 后 `.scalar_one()` | 一个整数 |
| `select(News)` 后 `.scalar_one_or_none()` | 一个 News 或 None，多行会报错 |

scalars 默认取每行第一项，并不是把所有列转换成字典。RowMapping 也不是普通 dict，必要时使用 `dict(row)` 转换。结果通常会被提取消费，不要先 `.all()` 再期待重新读取到同一批结果。

`where(a, b)` 表示 AND，OR 使用 `or_(a, b)`，集合过滤使用 `.in_(values)`，判断 NULL 使用 `.is_(None)`。SQL 条件不要用 Python 的 and / or 连接，因为那会触发 Python 的布尔判断，而不是构造 SQL。

新增对象先 `session.add(article)` 登记，flush 时才把待写操作发送给数据库。查询加载的持久对象可以直接修改属性；删除对象使用 `await session.delete(article)`。没有执行 SQL 的登记动作不一定需要 await。

```python
article = Article(title="事务", author_id=author_id)
session.add(article)
await session.flush()
print(article.id)

article.title = "理解事务"
await session.commit()
```

也可以用 update、delete 表达式执行直接更新。`views = views + 1` 应交给数据库计算，避免把旧值读回 Python 后再写入造成覆盖。

```python
from sqlalchemy import update

stmt = (
    update(Article)
    .where(Article.id == article_id)
    .values(views=Article.views + 1)
)
await session.execute(stmt)
await session.commit()
```

## Session 与对象状态

Engine 管理数据库连接和连接池，Session 管理事务、对象身份和变更跟踪。创建 Session 不代表立即拿走连接，执行数据库操作时才会按需获取；关闭会话会释放持有的资源。[Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)

同一会话中的相同模型和主键通常对应同一个 Python 对象，这叫身份映射。它让同一行的修改能够被统一跟踪，但不是通用查询缓存：再次执行 select 通常仍然会发送 SQL，已加载对象也不会因此自动覆盖成最新属性。

| 状态 | 含义 |
| --- | --- |
| transient | 刚构造，尚未由 Session 跟踪 |
| pending | 已 add，等待插入 |
| persistent | 已加载或 flush，处于会话跟踪中 |
| detached | 原来的持久对象已脱离会话 |

对象还有删除相关状态，可以用 `sqlalchemy.inspect(obj)` 检查。`Article(id=1, title="A")` 即使填了真实主键，也仍然只是临时对象，不能据此判断它已经查询过数据库。[对象状态](https://docs.sqlalchemy.org/en/20/orm/session_state_management.html)

从 JSON 字典执行 `Article(**data)` 只调用构造函数，不会把日期字符串自动解析为 datetime，也不会恢复会话跟踪。把这种对象直接 add 可能尝试 INSERT，造成重复主键；读缓存时可以直接使用字典或 Pydantic 数据模型，不必伪造一个可写的持久对象。

`refresh()` 会重新查询对象属性，`expire()` 则将属性标记为需要重新加载。异步环境不能任由普通属性访问悄悄发起数据库 I/O，未加载关系或过期属性可能触发 MissingGreenlet。通常应在明确的 await 点加载需要的数据。

`expire_on_commit=False` 可以让提交后保留已加载属性，减少提交后访问属性时的隐式刷新，但不会让对象永远最新。一个 AsyncSession 不应给多个并发任务共享；每个请求或并行任务应拥有自己的会话边界。[异步 ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

## 事务与工作单元

工作单元将已跟踪对象的新增、修改和删除收集起来，在 flush 时形成 SQL。commit 通常会先 flush 再提交事务；refresh 是重新查询，不是提交；flush 得到自增主键也不代表写入已经不可回滚。

```python
async def add_article(session, title: str, author_id: int):
    article = Article(title=title, author_id=author_id)
    session.add(article)
    await session.flush()
    return article

async def publish_pair(session, author_id: int):
    async with session.begin():
        first = await add_article(session, "A", author_id)
        second = await add_article(session, "B", author_id)
    return first.id, second.id
```

两次新增在同一个事务里，正常退出 begin 块才一起提交。如果 add_article 内部自行 commit，外层就失去“一起成功或一起失败”的控制能力；后面的 rollback 不能撤销此前已经提交的部分。

Session 执行查询也可能自动开启事务，这叫 autobegin。若已经执行过查询，再直接 begin 可能报“事务已存在”；显式事务块应覆盖整个业务，或由外层统一使用 try / commit / rollback。

flush 还可能在查询前自动发生，所以唯一冲突不一定等到 commit 才抛出。flush 或提交失败后，应回滚再继续使用会话，而不是捕获异常后直接发送下一条查询。

原子性解决多个操作一起提交或回滚，隔离级别决定并发事务彼此能观察到什么。事务里的“先查不存在再新增”并不自动防止另一个事务同时做同一件事，最终唯一性仍应由数据库约束保证。

## 关系加载与索引

join 描述一次查询如何连接表，relationship 描述对象间的关联属性。选出多项内容时，每行仍然包含多项，scalars 会只留下第一项：

```python
stmt = (
    select(Article, Author.name.label("author_name"))
    .join(Author, Author.id == Article.author_id)
)
rows = (await session.execute(stmt)).all()
for article, author_name in rows:
    print(article.title, author_name)
```

如果先查询 N 个作者，再逐个读取尚未加载的 articles，可能出现一次作者查询加 N 次文章查询，也就是 N+1。selectinload 通常通过额外的批量查询加载集合，joinedload 则用联表加载；集合 joinedload 会产生重复父行，需要对结果调用 unique。[关系加载](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)

```python
from sqlalchemy.orm import selectinload

stmt = select(Author).options(selectinload(Author.articles))
authors = (await session.execute(stmt)).scalars().all()
```

普通索引主要改善匹配的查找或排序，唯一约束表达不可重复的业务规则，外键约束表达引用合法性。名字叫 xxx_UNIQUE 的普通 Index 不会因此自动变成唯一索引，要看 unique 参数或实际唯一约束。

例如收藏表的 `(user_id, article_id)` 联合唯一表示同一用户只收藏同一文章一次，不能只约束 user_id，否则一个用户只能收藏一篇文章。相关列通常还应为非空，避免 NULL 语义偏离业务意图。

联合索引的列顺序与查询条件有关，`(user_id, article_id)` 通常能支持按 user_id 查找，不代表单独按 article_id 查找也同样有效。索引会增加写入维护成本，应结合实际 SQL 与执行计划判断，而不是给每列都加一个。

数据库查出的对象与对外响应仍应保留清晰边界。输出转换、字段别名和 datetime 序列化见 [FastAPI](fastapi.md)，缓存的字典与数据库对象之间的区别见 [Redis](redis.md)。
