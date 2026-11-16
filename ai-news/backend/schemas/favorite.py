from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from schemas.news import NewsItemBase


class FavoriteCheckResponse(BaseModel):
    is_favorite: bool = Field(..., alias="isFavorite")


class FavoriteAddRequest(BaseModel):
    news_id: int = Field(..., alias="newsId")


class FavoriteNewsItemResponse(NewsItemBase):
    """
    收藏模型类
    新闻模型类NewsItemBase + 收藏字段
    """

    favorite_id: int = Field(alias="favoriteId")
    favorite_time: datetime = Field(alias="favoriteTime")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


class FavoriteListResponse(BaseModel):
    """收藏列表接口响应"""

    list: list[FavoriteNewsItemResponse]
    total: int
    has_more: bool = Field(alias="hasMore")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
