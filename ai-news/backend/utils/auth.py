from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_conf import get_db
from crud import users


async def get_current_user(
        authorization: str = Header(..., alias="Authorization"),
        db: AsyncSession = Depends(get_db)
):
    """
    认证：

    前端请求头中携带token信息："Authorization: Bearer <token>"
    """
    # 获取 token
    # - 按照空格切分，取第二个：token = authorization.split(" ")[1]
    # - 把 "Bearer " 替换成空串
    token = authorization.replace("Bearer ", "")
    
    # 根据 Token 查询用户
    user = await users.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌或已经过期的令牌")

    return user
