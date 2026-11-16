"""数据校验：请求体参数"""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class UserRequest(BaseModel):
    """注册请求"""
    username: str
    password: str


# user_info 对应的类：基础类 + Info 类（id、用户名）
class UserInfoBase(BaseModel):
    """
    用户信息基础数据模型
    """
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")


class UserInfoResponse(UserInfoBase):
    """用户信息响应"""

    id: int
    username: str

    # 模型类配置
    model_config = ConfigDict(
        from_attributes=True  # 允许从 ORM 对象属性中取值
    )


class UserAuthResponse(BaseModel):
    """用户认证响应"""

    token: str
    user_info: UserInfoResponse = Field(..., alias="userInfo")

    # 模型类配置
    # from_attributes -> 可以使用 .model_validata() 序列化
    model_config = ConfigDict(
        populate_by_name=True,  # alias / 字段名兼容
        from_attributes=True  # 允许从 ORM 对象属性中取值，自动序列化
    )


class UserUpdateRequest(BaseModel):
    """更新用户信息请求"""

    nickname: str = None
    avatar: str = None
    gender: str = None
    bio: str = None
    phone: str = None


class UserChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., alias="oldPassword", description="旧密码")
    new_password: str = Field(..., min_length=6, alias="newPassword", description="新密码")
