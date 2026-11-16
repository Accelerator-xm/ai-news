from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def success_response(message: str = "success", data=None):
    """
    封装成功响应格式
    目标：把任何的 FastAPI、Pydantic、ORM 对象 都要正常响应 → code、message、data
    """
    content = {
        "code": 200,
        "message": message,
        "data": data
    }

    return JSONResponse(content=jsonable_encoder(content))
