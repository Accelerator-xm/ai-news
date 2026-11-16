# FastAPI

FastAPI 把 HTTP 请求映射到 Python 函数，利用类型提示和 Pydantic 完成数据解析，再将返回值转换为响应。理解一次请求经过哪些边界，比记住装饰器名称更重要。下文使用 Pydantic 2 写法，依赖的 scope 行为以 FastAPI 0.125 为基准。

## 应用、路由与一次请求

FastAPI 应用是一个 ASGI 应用对象，Uvicorn 等 ASGI 服务器负责接受连接并驱动请求处理。路由函数描述业务行为，服务器负责网络收发，两者不是同一个组件。

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def hello(name: str = "world"):
    return {"message": f"Hello, {name}"}
```

把代码保存为 `main.py` 后，`uvicorn main:app --reload` 表示导入 main 模块并运行其中的 app。访问 `/hello?name=Python` 得到 JSON；`/docs` 展示交互式接口文档，`/openapi.json` 是机器可读的 OpenAPI 描述。文档来自声明的参数和模型，不会自动理解函数体中的全部业务规则。

`@app.get()` 在函数定义时登记路由，不是在定义时执行一次 HTTP 请求。请求到达后，框架根据 HTTP 方法和路径匹配路由，再解析参数、执行依赖并调用函数。使用 Pydantic 请求体时，不必自己先 `await request.json()` 再手工取每个字段。

HTTP 方法表达操作意图：GET 获取资源，POST 创建资源或执行动作，PUT 通常表示替换，PATCH 通常表示部分修改，DELETE 删除资源。方法名不会替业务代码实现这些语义；一个使用 GET 却写数据库的函数仍然会写数据库，缓存和重试也不会自动知道它的副作用。

相关路由可以放入 APIRouter，再由应用统一挂载。prefix 会与具体路径拼接，tags 主要影响接口文档分组，不改变实际 URL。

```python
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/api/items", tags=["items"])

@router.get("/latest")
async def latest_item():
    return {"id": 1}

@router.get("/{item_id}")
async def read_item(item_id: int):
    return {"id": item_id}

app.include_router(router)
```

静态路径 `/latest` 应在可能捕获它的 `/{item_id}` 前登记。类型为 int 会在匹配后校验路径值，不会自动保证先尝试另一个静态路由。

## 参数从哪里来

请求可以在路径、查询字符串、请求头、Cookie 和请求体里携带数据。参数放在哪里是接口契约的一部分，前端不能把查询参数随意改放 JSON 体后仍期待框架自动找到。

```python
from typing import Annotated
from fastapi import Cookie, FastAPI, Header, Path, Query

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(gt=0)],
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
    authorization: Annotated[str | None, Header()] = None,
    session_id: Annotated[str | None, Cookie()] = None,
):
    return {"id": item_id, "pageSize": page_size}
```

`item_id` 出现在路径占位符中，所以从路径取值；`pageSize` 位于 `?pageSize=20`，函数内部仍叫 page_size。`Header()` 明确从请求头读取，通常会将 Python 名字中的下划线转为连字符，也可以用 alias 指定外部名称。

普通标量参数如果不属于路径，通常被视为查询参数；BaseModel 参数通常被视为请求体。显式使用 `Path`、`Query`、`Header`、`Body` 等可以让来源和限制更清楚。`Annotated` 保留原本的 Python 类型，同时附加框架读取的元数据。

路径占位符必须与函数中对应的参数名匹配。路径写 `{item_id}`，函数却定义必填的 `id: int`，框架可能继续寻找查询参数 id，造成缺参 422。参数的名字相近并不构成自动绑定。

```python
from pydantic import BaseModel, Field
from fastapi import Body

class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)

@app.post("/items")
async def create_item(item: ItemCreate):
    return item

@app.post("/labels")
async def create_label(label: Annotated[str, Body(embed=True)]):
    return {"label": label}
```

第一个接口接收 `{"title":"键盘","price":199}`，第二个接收 `{"label":"Python"}`。不使用 embed 的单一字符串 Body 参数通常对应整个 JSON 字符串值；多个 Body 参数则会形成带各参数名字的对象，不能只根据 Python 参数数量猜请求结构。[请求体](https://fastapi.tiangolo.com/tutorial/body/)

JSON、表单和文件上传使用不同的内容编码。`Form` 读取表单字段，`UploadFile` 读取上传文件；不能把 multipart 请求当成普通 JSON 请求处理。表单和文件解析需要安装 `python-multipart`。

```python
from fastapi import UploadFile

@app.post("/files")
async def inspect_file(file: UploadFile):
    size = 0
    try:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
        return {"filename": file.filename, "size": size}
    finally:
        await file.close()
```

分块读取避免一次把大文件内容全部装入 Python 字节串。文件名和 Content-Type 都是客户端提供的元数据，不能单凭它们就认定文件内容符合要求。

`Request` 适合访问原始请求对象、连接状态或底层请求体。当希望框架自动生成校验和文档时，应尽量声明具体参数与模型；手工读请求体后，字段校验就需要自己负责。

## Pydantic 如何校验数据

BaseModel 定义数据结构，Field 定义字段约束，validator 表达额外规则。创建模型得到的是完成解析后的 Python 对象，输入字符串可能已变成整数、日期等类型；默认校验不意味着所有类型转换都被禁止。

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nickname: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=0, le=150)
    gender: Literal["male", "female", "unknown"] = "unknown"

    @field_validator("nickname")
    @classmethod
    def check_nickname(cls, value: str) -> str:
        if value.startswith("@"):
            raise ValueError("昵称不能以 @ 开头")
        return value

profile = Profile.model_validate({"nickname": " Alice ", "age": "20"})
print(profile.nickname)  # Alice
print(profile.age)       # 20
```

`str_strip_whitespace` 在字符串处理中去除首尾空白，`extra="forbid"` 拒绝未声明字段。未设置 extra 时，多余字段通常会被忽略，而不是自动进入模型。需要拒绝诸如 `"20" → 20` 的转换时，可以为字段使用 `strict=True`，或在模型层配置严格校验；不同输入来源的严格规则仍需按类型理解。[Pydantic 模型](https://docs.pydantic.dev/latest/concepts/models/)

可空与可省略是两个维度。以下声明在 Pydantic 2 中的含义不同：

| 声明 | 可以不传 | 可以传 null |
| --- | --- | --- |
| `name: str` | 否 | 否 |
| `name: str | None` | 否 | 是 |
| `name: str | None = None` | 是 | 是 |
| `name: str = ""` | 是 | 否 |

嵌套 BaseModel 会递归校验内部结构，`list[ChatMessage]` 会校验每一条消息，而不是只确认外层是列表。出现错误时，错误位置可以指向列表索引和嵌套字段，前端可据此定位具体输入。

跨字段或整个对象的规则使用 model_validator。例如聊天请求既要限制单条消息，还要检查最后一条消息的角色和全部内容的总长度：

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)

class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def validate_conversation(self):
        if self.messages[-1].role != "user":
            raise ValueError("对话必须以用户消息结束")
        if sum(len(message.content) for message in self.messages) > 100000:
            raise ValueError("对话过长，请开启新对话")
        return self
```

字段规则先确保消息列表非空、最多 60 条，单条内容去除首尾空白后长度在 1～20000 之间。模型校验器随后检查“以用户消息结束”和“总长度不超过 100000”，这些字符限制不等于模型的 token 限制。

`mode="after"` 表示基础字段解析完成后执行，拿到的通常已经是目标 Python 类型；before 校验器面对的可能仍是原始输入。校验器应返回处理后的值或模型。普通数据不合法使用 ValueError 等校验异常，不要把校验器里的编程错误一律包装成用户输错。[自定义校验](https://docs.pydantic.dev/latest/concepts/validators/)

结构正确并不代表业务一定允许。模型可以保证年龄是非负整数，但“用户名是否已注册”“旧密码是否正确”还要依赖业务数据；唯一性、外键等最终约束仍由数据库保证。

## 输出模型、别名与部分更新

输入模型和输出模型表达不同边界。注册输入可能包含密码，用户公开信息不应该包含密码或哈希；数据库对象拥有某个字段，也不代表响应应公开它。

```python
from pydantic import BaseModel

class UserPublic(BaseModel):
    id: int
    username: str

@app.get("/users/{user_id}", response_model=UserPublic)
async def read_user(user_id: int):
    return {"id": user_id, "username": "alice", "password_hash": "internal-value"}
```

正常响应处理会按照 UserPublic 校验、过滤和序列化返回值，多余的 password_hash 不会进入响应。请求输入校验失败通常是 422；返回值违反响应模型通常是服务端程序错误，不应解释成调用方输入有问题。[响应模型](https://fastapi.tiangolo.com/tutorial/response-model/)

Pydantic 可以从字典读取值，也可以在配置 `from_attributes=True` 后从普通对象或 ORM 对象的属性读取。这个过程不会替你执行数据库查询，更不会保证尚未加载的关联属性可以安全访问。

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class NewsItemBase(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: Optional[datetime] = Field(None, alias="publishTime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

news = NewsItemBase.model_validate({
    "id": 1,
    "title": "理解异步编程",
    "category_id": 2,
    "views": 0,
    "publish_time": "2026-01-01T12:00:00",
})
payload = news.model_dump(mode="json", by_alias=True)
```

Python 属性仍叫 `publish_time`、`category_id`，对外输出为 `publishTime`、`categoryId`。`populate_by_name=True` 允许使用 Python 字段名填充，输入也可以使用 alias。新闻列表从 ORM 对象读取时，同样通过 `model_validate(item)` 构造模型，再用 `model_dump(mode="json", by_alias=True)` 生成响应数据。

alias 同时参与输入别名和启用别名时的输出；validation_alias 与 serialization_alias 则分别控制输入和输出。Pydantic 2.11 起也可以用 `validate_by_name=True` 与 `validate_by_alias=True` 表达按字段名和别名校验。

不同序列化方法的结果类型必须分清，尤其是缓存和 HTTP 响应之间的数据转换：

| 操作 | 得到什么 |
| --- | --- |
| `model_validate(data)` | 经校验的 Pydantic 对象 |
| `model_dump()` | Python 字典，datetime 通常仍是 datetime |
| `model_dump(mode="json")` | JSON 兼容字典，时间等值已转换 |
| `model_dump_json()` | JSON 字符串 |

`mode="json"` 不代表结果已变成字符串。手工调用 model_dump 时，是否使用别名要明确选择 by_alias；不要仅因为模型上设置了 alias 就假定所有输出入口都启用它。[序列化](https://docs.pydantic.dev/latest/concepts/serialization/)

部分更新还必须区分“没有提交”和“主动提交 null”。Pydantic 会记录字段是否被显式设置，`exclude_unset=True` 可以只提取提交过的字段：

```python
class ProfilePatch(BaseModel):
    nickname: str | None = None
    bio: str | None = None

patch = ProfilePatch.model_validate({"bio": None})
print(patch.model_dump(exclude_unset=True))  # {'bio': None}
print(patch.model_dump(exclude_none=True))   # {}
```

前一种保留“清空 bio”的意图，后一种过滤全部 None。如果两种过滤一起使用，null 就会变成“不更新”。是否允许清空应由接口约定决定，不能把某种过滤写法当成所有更新接口的固定模板。

## 依赖注入与资源生命周期

Depends 声明“这个参数由另一个组件提供”。FastAPI 负责调用依赖、解析依赖自己的参数，并把结果传给路由。公共分页、当前用户、配置和数据库会话都适合通过依赖复用。

```python
from typing import Annotated
from fastapi import Depends, Query

def pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict[str, int]:
    return {"offset": (page - 1) * size, "limit": size}

PageParams = Annotated[dict[str, int], Depends(pagination)]

@app.get("/articles")
async def read_articles(params: PageParams):
    return params
```

写 `Depends(pagination)` 是把函数交给框架；写 `Depends(pagination())` 会提前执行，失去按请求解析参数的意义。依赖还可以依赖其他依赖，形成依赖图；相同依赖在一次请求中默认复用结果，这个缓存不是跨请求缓存。

普通依赖返回值即可，需要管理资源时使用 yield，将获取资源和释放资源放在同一生命周期中：

```python
import httpx

async def get_http_client():
    async with httpx.AsyncClient() as client:
        yield client

HttpClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]

@app.get("/client-ready")
async def client_ready(client: HttpClient):
    return {"ready": not client.is_closed}
```

yield 前创建资源，yield 的对象交给路由，后续退出上下文时关闭。路由抛出的异常也会经过依赖的退出过程，捕获后不应无理由吞掉，否则可能破坏外层错误处理。

包含 yield 的依赖默认使用 request scope，清理在响应发送后执行；`Depends(get_http_client, scope="function")` 可以改为路由函数结束后、响应发送前退出。流式响应如果仍需使用该资源，就不能提前关闭。[yield 依赖](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)

数据库会话的获取和事务提交不必放在同一层。关键业务应在发送成功响应前确认提交成功；把 commit 全部留给响应后的依赖清理，会使提交失败时无法再改变已经发送的响应。一个业务跨多个 CRUD 时，也应有明确的事务负责人。

## 响应类型与异常

普通返回值由 FastAPI 的响应处理流程编码；声明 response_model 可以约束输出。直接返回 Response 子类则交给框架发送这个响应对象，不再走通常的响应模型过滤。因此 JSONResponse 的内容应在构造前就整理为允许公开的结构。

```python
from datetime import datetime, timezone
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

@app.get("/clock")
async def clock():
    content = {"time": datetime.now(timezone.utc)}
    return JSONResponse(content=jsonable_encoder(content))
```

jsonable_encoder 将 datetime、Pydantic 对象等转换为 JSON 兼容数据，不负责判断密码哈希之类的字段是否应该公开。把 model_dump_json 得到的字符串交给 JSONResponse，通常会再次编码成 JSON 字符串，而不是期待的 JSON 对象。

HTTP 状态在响应状态行里，JSON 中的 `code` 只是接口自己的字段。返回 `{"code":404}` 不会自动把 HTTP 200 改成 404。常见语义中，401 表示认证问题，403 表示已识别身份但不允许操作，404 表示资源不存在，422 表示请求校验失败，500 表示服务内部错误。

```python
from fastapi import HTTPException

@app.get("/available/{item_id}")
async def available_item(item_id: int):
    if item_id != 1:
        raise HTTPException(status_code=404, detail="资源不存在")
    return {"id": item_id}
```

必须 raise 异常才能中断正常流程，把 HTTPException 当普通返回值没有同样的作用。异常处理器负责将已抛出的异常转换为响应；如需同时处理路由主动抛出的异常和底层的 HTTP 异常，可以注册 Starlette 的 HTTPException 基类。

```python
from fastapi import Request
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )
```

请求校验由 RequestValidationError 表达，有自己的默认处理器。只注册普通 HTTPException 处理器，不会自动让 422 也使用同一个 JSON 结构。读取错误时，`loc` 可以区分 body、query、path 以及嵌套字段，`msg` 描述失败原因。

HTMLResponse 返回 HTML，FileResponse 发送文件，RedirectResponse 返回重定向。它们改变的是响应表示或传输方式，不改变认证和业务权限要求。

## 异步执行与应用级资源

`async def` 路由适合调用异步数据库驱动和 HTTP 客户端。FastAPI 会将普通 def 路由和普通 def 依赖放到工作线程执行，但不会自动把 async 函数直接调用的同步工具函数也放进线程池。

```python
from starlette.concurrency import run_in_threadpool
from passlib.context import CryptContext

passwords = CryptContext(schemes=["bcrypt"])

def calculate_digest(value: str) -> str:
    return passwords.hash(value)

async def prepare_digest(value: str) -> str:
    return await run_in_threadpool(calculate_digest, value)
```

封装的目的在于不阻塞事件循环线程，不表示哈希计算本身变快。异步代码也不能并发共享同一个有状态的 AsyncSession，资源能否共享应看组件自己的并发约定。[FastAPI 异步执行](https://fastapi.tiangolo.com/async/)

请求级依赖负责一次请求的资源；HTTP 连接池等可复用资源也可以在应用 lifespan 中创建，在应用退出时释放。

```python
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=30) as client:
        app.state.http_client = client
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/ready")
async def ready(request: Request):
    client = request.app.state.http_client
    return {"ready": not client.is_closed}
```

yield 前对应启动，yield 后对应关闭。应用级对象通常每个工作进程各有一份，不能把它理解成所有进程共享的全局状态。连接池可以复用，不等于所有请求共享同一个事务。[应用生命周期](https://fastapi.tiangolo.com/advanced/events/)

BackgroundTasks 可以在响应发送后执行一些进程内任务，但任务不因此具备持久化、重试或跨进程调度能力。任务如果仍需要数据库等资源，应建立自己的有效生命周期，而不是依赖已经关闭的请求资源。

## 中间件、跨域与流式响应

中间件用于统一处理进入应用的请求，例如添加响应头、记录耗时和处理跨域。调用 `call_next(request)` 把请求交给后续处理，再拿到响应对象。

```python
import time

@app.middleware("http")
async def add_timing(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.perf_counter() - started)
    return response
```

后添加的中间件处在更外层，请求从外向内，响应从内向外。对流式响应，拿到响应对象不代表整个响应体已经传完，因此这里的耗时不能当作完整 AI 生成时长。依赖注入更适合“这个路由需要当前用户”一类局部需求，不必把所有认证都硬塞进全局中间件。

Origin 由协议、主机和端口共同组成，`http://127.0.0.1:5173` 与 `http://127.0.0.1:8000` 不同源，localhost 与 127.0.0.1 也不是同一个主机名。浏览器对部分跨源请求会先发送 OPTIONS 预检，请求中使用 JSON 或 Authorization 时应检查允许的头和方法。

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

CORS 决定浏览器是否允许网页读取跨源响应，不能替代身份认证；命令行客户端通常不受浏览器同源策略约束。需要携带 Cookie 等凭据时，还应按实际来源配置 credentials，不能把任意源放行当成完整方案。[CORS](https://fastapi.tiangolo.com/tutorial/cors/)

StreamingResponse 接受普通或异步迭代器，把每次产出的内容继续发送给客户端。下面把文本逐段编码为 SSE，空行用于结束一条事件：

```python
import asyncio
import json
from fastapi.responses import StreamingResponse

async def text_events():
    for text in ["你好", "，世界"]:
        await asyncio.sleep(0.1)
        payload = json.dumps({"content": text}, ensure_ascii=False)
        yield f"event: delta\ndata: {payload}\n\n"
    yield 'event: done\ndata: {}\n\n'

@app.get("/events")
async def events():
    return StreamingResponse(
        text_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
```

`text_events()` 返回异步生成器，不能写成 await text_events。生成器由响应流程持续迭代，每次 yield 不等于浏览器一定收到相同边界的网络块。

发送响应头之前的错误可以返回普通 HTTP 错误；流已开始后，通常只能按协议发送错误事件或中断连接，不能再把状态码改成另一个 JSON 响应。取消、异常和正常结束都应释放持有的上游资源，相关的分帧与终止判断见 [AI 对话与流式输出](ai.md)。
