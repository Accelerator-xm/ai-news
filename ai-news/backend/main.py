from fastapi import FastAPI
from routers import news, users, favorite, history, ai
from fastapi.middleware.cors import CORSMiddleware

from utils.exception_handlers import register_exception_handlers

app = FastAPI()

# 注册异常处理器
register_exception_handlers(app)


# 中间件：每次请求进入应用前都执行的函数
# 使用装饰器
# 自底向上执行, 看成栈操作，CORSMiddlewar开始 -> middleware1开始 -> 业务执行 ->  middleware1结束 -> CORSMiddlewar结束

# @app.middleware("http")
# async def middleware1(request, call_next):
#     # 请求 -> 中间件处理
#     print("开始")
#     # -> 实际请求的业务处理（对应路由执行）
#     response = await call_next(request)
#     # -> 中间件处理
#     print("结束")
#     # 返回
#     return response


# 跨域资源共享cors: 允许一个源的应用向另一个源的服务器发起跨域请求，获取资源
# 同源：协议（http、httpx）、域名（127.0.0.1、localhost）、端口全部一样
# 不同源访问数据就是跨域
# *表示任意源
app.add_middleware(
    # 自带中间件
    CORSMiddleware,
    allow_origins=["*"],     # 允许的源，开发阶段允许所有源，生产环境需要指定源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],     # 允许的请求方法，get\post\put等
    allow_headers=["*"],     # 允许的请求头
)


@app.get("/")
async def root():
    return {"message": "Hello World"}

# 挂载路由/注册路由
app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(ai.router)
