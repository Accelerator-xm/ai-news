from datetime import datetime
from typing import Optional

from pydantic import Field, ConfigDict, BaseModel


class NewsItemBase(BaseModel):
    """新闻模型类"""

    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: Optional[datetime] = Field(None, alias="publishTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class RelatedNewsResponse(BaseModel):
    """
    相关新闻响应（简化版，只包含必要字段）
    """
    id: int
    title: str
    image: Optional[str] = None
    views: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class NewsDetailResponse(NewsItemBase):
    """
    新闻详情响应（继承自 NewsItemResponse，新增 content 和 related_news）
    """
    content: str  # 新增：新闻内容
    related_news: list[RelatedNewsResponse] = Field(default_factory=list, alias="relatedNews")  # 新增相关新闻：

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )



