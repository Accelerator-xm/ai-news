"""封装操作数据库的方法"""

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.news import Category, News


async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    """获取分类列表"""

    # 查询操作：select(模型类)
    ## 分页查询：.offset(偏移量).limit(获取大小)
    stmt = select(Category).offset(skip).limit(limit)
    # await db.execute(数据库操作)
    result = await db.execute(stmt)
    # 获取全部值 all()
    return result.scalars().all()


async def get_news_list(db: AsyncSession, category_id: int, skip: int = 0, limit: int = 10):
    """查询的是指定分类下的新闻"""

    # 条件查询：where(条件)
    ## 条件：比较、模糊查询 like()、逻辑、包含 in_()
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_news_count(db: AsyncSession, category_id: int):
    """查询的是指定分类下的新闻数量"""

    # 聚合计算：func.方法(模型类.属性)
    ## 方法：统计总量count、avg、max、min、sum
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    # scalar返回一个标量
    return result.scalar_one()  # 只能有一个结果，否则报错


async def get_news_detail(db: AsyncSession, news_id: int):
    """获取新闻详情"""

    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  # 最多一个结果


async def increase_news_views(db: AsyncSession, news_id: int):
    """
    增加浏览量：
    更新 → 检查数据库是否真的命中了数据 → 命中了返回True
    """

    # 更新操作：update(News).values(更新值)
    stmt = update(News).where(News.id == news_id).values(views=News.views + 1)
    result = await db.execute(stmt)
    await db.commit()

    # result.rowcount 命中的行数
    return result.rowcount > 0


async def get_related_news(db: AsyncSession, news_id: int, category_id: int, limit: int = 5):
    """
    获取相关新闻
    同类新闻 + 排除自身
    """
    # order_by 排序 → 浏览量最多 + 发布时间最新
    stmt = select(News).where(
        News.category_id == category_id,
        News.id != news_id
    ).order_by(
        News.views.desc(),  # 默认是升序，desc 表示降序
        News.publish_time.desc()
    ).limit(limit)
    result = await db.execute(stmt)
    
    related_news = result.scalars().all()
    # 列表推导式 推导出新闻的核心数据，然后再 return
    return [{
        "id": news_detail.id,
        "title": news_detail.title,
        "content": news_detail.content,
        "image": news_detail.image,
        "author": news_detail.author,
        "publishTime": news_detail.publish_time,
        "categoryId": news_detail.category_id,
        "views": news_detail.views
    } for news_detail in related_news]
