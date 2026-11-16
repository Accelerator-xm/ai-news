"""模块化路由 → API 接口规范文档"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from crud import news
from crud import news_cache
from schemas.news import NewsItemBase


# 创建 APIRouter 实例
## prefix 路由前缀（API 接口规范文档）
## tags 分组 标签
router = APIRouter(prefix="/api/news", tags=["news"])


# Depends: 依赖注入
## 共享通用逻辑，封装可复用组件

@router.get("/categories")
async def get_categories(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """获取数据库里面新闻分类数据"""

    # 分类列表一般是全部获取无需分页
    # skip、limit实际没用只是为了介绍分页逻辑，实际业务一般是传 pageId + pageSize
    categories = await news_cache.get_categories(db, skip, limit)
    return {
        "code": 200,
        "message": "获取新闻分类成功",
        "data": categories
    }


@router.get("/list")
async def get_news_list(
        category_id: int = Query(..., alias="categoryId"),
        page: int = 1,
        page_size: int = Query(10, alias="pageSize", le=100),
        db: AsyncSession = Depends(get_db)
):
    """获取新闻列表: 分页"""
    # 前端请求和后端字段不一致，Query 中设置别名（alias=前端传递的字段名）

    # 计算偏移量
    offset = (page - 1) * page_size
    news_list = await news_cache.get_news_list(db, category_id, offset, page_size)
    total = await news.get_news_count(db, category_id)
    # (跳过的 + 当前列表里面的数量) < 总量
    has_more = (offset + len(news_list)) < total
    return {
        "code": 200,
        "message": "获取新闻列表成功",
        "data": {
            "list": [
                NewsItemBase.model_validate(item).model_dump(mode="json", by_alias=True)
                for item in news_list
            ],
            "total": total,
            "hasMore": has_more
        }
    }


@router.get("/detail")
async def get_news_detail(news_id: int = Query(..., alias="id"), db: AsyncSession = Depends(get_db)):
    """
    获取新闻详细内容：
    获取新闻详情 + 浏览量+1 + 相关新闻
    """

    news_detail = await news_cache.get_news_detail(db, news_id)
    if not news_detail:
        # 异常响应处理
        raise HTTPException(status_code=404, detail="新闻不存在")

    views_res = await news.increase_news_views(db, news_detail.id)
    if not views_res:
        raise HTTPException(status_code=404, detail="新闻不存在")

    related_news = await news_cache.get_related_news(db, news_detail.id, news_detail.category_id)

    return {
      "code": 200,
      "message": "success",
      "data": {
        "id": news_detail.id,
        "title": news_detail.title,
        "content": news_detail.content,
        "image": news_detail.image,
        "author": news_detail.author,
        "publishTime": news_detail.publish_time,
        "categoryId": news_detail.category_id,
        "views": news_detail.views,
        "relatedNews": related_news
      }
    }
