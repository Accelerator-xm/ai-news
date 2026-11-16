# Python

Python 的对象、函数和协程共同构成了后端代码的基础。理解变量绑定、函数调用与资源生命周期后，类型校验、依赖注入和异步数据库操作会更容易读懂。以下示例采用 Python 3.12 语法。

## 对象、变量与容器

变量名绑定到对象，赋值通常不会复制对象。一个对象有自己的类型、值和身份；`==` 比较值是否相等，`is` 比较是不是同一个对象。判断空值通常写 `value is None`，不要用 `is` 比较字符串或数字内容。[Python 数据模型](https://docs.python.org/3.12/reference/datamodel.html#objects-values-and-types)

```python
first = ["Python"]
second = first
second.append("FastAPI")

print(first)            # ['Python', 'FastAPI']
print(first is second)  # True

third = first.copy()
print(first == third)   # True
print(first is third)   # False
```

列表、字典和集合是可变对象，可以原地修改。字符串、整数和元组本身不可变；对字符串重新赋值，是让变量改为指向另一个字符串。元组不可变只限制其元素引用，元组内的列表仍可以修改。

`list.copy()`、切片和 `dict.copy()` 都是浅复制：外层容器独立，内部对象仍可能共享。需要复制嵌套可变结构时，可以使用 `copy.deepcopy()`，但对数据库会话、网络连接等资源对象不能靠深复制获得另一个有效资源。

```python
original = {"tags": ["Python"]}
copied = original.copy()
copied["tags"].append("asyncio")

print(original["tags"])  # ['Python', 'asyncio']
```

字典通过键取值，对象通过属性取值。`data["title"]` 在键不存在时抛出 `KeyError`，`data.get("title")` 默认返回 `None`。如果键存在且值就是 `None`，`get()` 同样返回 `None`；要区分“没这个键”和“键值为空”，使用 `"title" in data`，或使用独立的哨兵对象作为默认值。

Python 的条件判断还会把空字符串、空容器、零和 `None` 都视为假值。因此 `if cached:` 无法区分缓存未命中与已缓存的空列表。需要表达“不是空值”时，写 `cached is not None` 更准确。

列表推导式适合把一个集合转换成另一个集合。表达式先指定输出值，`for` 指定数据来源，末尾的 `if` 负责过滤：

```python
items = [{"title": "A", "visible": True}, {"title": "B", "visible": False}]
titles = [item["title"] for item in items if item["visible"]]
print(titles)  # ['A']
```

字符串 `str` 表示 Unicode 文本，`bytes` 表示字节序列。网络传输和文件存储最终处理字节，`text.encode("utf-8")` 把文字编码成字节，`raw.decode("utf-8")` 反向解码。`len(text)` 与 UTF-8 字节长度不是一个概念，限制密码字节数、解析流式中文时尤其需要区分。

## 函数、参数与类型提示

函数可以赋给变量、作为参数传入，也可以作为返回值。这意味着 `datetime.now` 是一个可以稍后调用的函数，`datetime.now()` 则是现在执行后得到的时间对象。向框架登记依赖、默认值工厂或回调时，通常传函数本身。

参数既可以按位置传，也可以按名字传。`*` 后面的参数必须按名字传，适合避免一串布尔值或数字造成调用歧义；`**` 则能把字典展开为关键字参数。

```python
def make_label(title: str, *, prefix: str = "") -> str:
    return f"{prefix}{title}"

print(make_label("Python", prefix="学习："))

options = {"title": "FastAPI", "prefix": "学习："}
print(make_label(**options))
```

`*args` 接收额外的位置参数，得到元组；`**kwargs` 接收额外的关键字参数，得到字典。它们常用于包装函数，但接口明确时，显式参数更容易理解。合并字典 `{**first, **second}` 时后面的同名键覆盖前面；函数调用中重复传同一个关键字参数则会报错。[Python 函数参数](https://docs.python.org/3.12/tutorial/controlflow.html#more-on-defining-functions)

默认参数在执行函数定义时计算一次，不会在每次调用时重新创建。下面的默认列表会在调用之间共享：

```python
def append_tag(tag, tags=None):
    if tags is None:
        tags = []
    tags.append(tag)
    return tags

print(append_tag("Python"))   # ['Python']
print(append_tag("FastAPI"))  # ['FastAPI']
```

这里用 `None` 表示“调用方没提供列表”，每次再创建新列表。直接写 `tags=[]` 会复用同一列表。时间默认值也有相同问题：函数参数中的 `created_at=datetime.now()` 会固定为定义时刻，需要每次计算时应在函数体内调用，或交给支持工厂函数的机制处理。

类型提示描述预期的数据形状，不会让普通 Python 函数自动执行运行时校验。下面的调用仍然会执行字符串重复：

```python
def double(value: int) -> int:
    return value * 2

print(double("3"))  # '33'
```

编辑器和类型检查器可以发现这类问题。FastAPI、Pydantic 会进一步读取类型提示执行参数解析和校验，但这是框架的行为。

`str | None` 表示允许字符串或 `None`，和 `Optional[str]` 含义一致；是否允许省略还取决于默认值。`list[str]` 表示字符串列表，`dict[str, int]` 表示字符串键和整数值。`Literal["user", "assistant"]` 表示有限取值，`Annotated[int, ...]` 则在原类型上附加其他组件可读取的元数据。

装饰器接收一个函数并返回另一个可调用对象，`@decorate` 可以理解为定义后执行 `function = decorate(function)`。包装器里的 `*args`、`**kwargs` 用来转发调用，`functools.wraps()` 保留原函数的名称、文档和可供工具追溯的信息：

```python
from functools import wraps

def trace(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        print(f"calling {function.__name__}")
        return function(*args, **kwargs)
    return wrapper

@trace
def add(left: int, right: int) -> int:
    return left + right

print(add(2, 3))
```

异步函数的包装器通常也要写成 `async def` 并 `await` 原函数，才能在真正完成后执行后续逻辑。单纯在同步包装器里返回协程对象，只是把协程交给调用方，并没有等待它完成。

## 类、dataclass 与属性

类把状态与相关操作组织在一起。`__init__()` 初始化新实例，`self` 指向当前实例；`self.name` 是实例属性，而写在类体中的属性通常由实例共享。共享只读配置可以放在类上，每个对象各自变化的列表或字典应在初始化时创建。[Python 类](https://docs.python.org/3.12/tutorial/classes.html)

```python
class Conversation:
    def __init__(self):
        self.messages = []

    def add(self, content: str):
        self.messages.append(content)

first = Conversation()
second = Conversation()
first.add("你好")
print(second.messages)  # []
```

如果把 `messages = []` 放在类体中，并让实例都对它 append，就会共享同一份消息。实例属性虽然可以覆盖同名类属性，但这种隐含差异容易让代码行为难以判断。

以数据保存为主的类可以使用 dataclass 自动生成 `__init__`、`__repr__`、比较方法等。字段仍然只是类型声明，不会自动把字符串转换为整数，也不会执行接口级校验。

`@property` 把一个无显式参数的方法暴露为属性访问，适合由已有状态计算出的值。例如 AI 配置类将请求地址补全和必要字段检查封装为属性：

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class AISettings:
    provider: str
    base_url: str
    api_key: str = field(repr=False)
    model: str
    system_prompt: str
    timeout: float = 120
    max_tokens: int = 4096
    token_parameter: str = "max_tokens"
    extra_headers: dict = field(default_factory=dict, repr=False)
    extra_body: dict = field(default_factory=dict)

    @property
    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith(("/chat/completions", "/messages")):
            return base
        return base + ("/messages" if self.provider == "anthropic" else "/chat/completions")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model and self.api_key)

settings = AISettings(
    provider="openai",
    base_url="https://example.com/v1/",
    api_key="example-key",
    model="example-model",
    system_prompt="",
)
print(settings.endpoint)
print(settings.configured)
print(settings)
```

访问 `settings.endpoint` 时才会运行地址计算；`configured` 只检查字段是否有值，不会发送请求验证密钥。属性中仍然是在执行代码，因此不要把昂贵网络请求藏在看似普通的数据读取后面。

`repr=False` 只控制对象打印时是否显示字段，不是加密；`default_factory=dict` 为每个实例创建独立字典。`frozen=True` 阻止对字段重新赋值，但不会冻结字典内部，`settings.extra_body["temperature"] = 0.7` 仍能改变内容。[dataclass](https://docs.python.org/3.12/library/dataclasses.html)

## 迭代、生成器与上下文管理

可迭代对象能产生迭代器，迭代器通过 `next()` 提供下一个值。列表可以反复创建迭代器，一个具体迭代器则会随着读取被消耗；到结尾后抛出 `StopIteration`，`for` 循环负责处理这个信号。

包含 `yield` 的普通函数是生成器函数。调用时得到生成器，函数体会在开始迭代后执行；每次 yield 暂停在当前位置，下次迭代从那里继续。因此可以逐条处理数据，而不必先把全部结果存进列表。

```python
def valid_titles(rows):
    for row in rows:
        title = row.get("title", "").strip()
        if title:
            yield title

titles = valid_titles([{"title": " A "}, {"title": ""}, {"title": "B"}])
print(next(titles))  # A
print(list(titles))  # ['B']
print(list(titles))  # []
```

`return` 结束函数，`yield` 则允许后续继续执行。把生成器转换成 `list` 会一次性消费剩余结果，也会失去逐条处理带来的内存优势。

文件、连接与锁都需要释放资源，`with` 把获取和清理绑定在同一个语法结构里。`with open(...)` 离开代码块时会关闭文件，即使块内发生异常也会执行退出逻辑；是否吞掉异常则取决于上下文管理器自己的实现。

```python
from contextlib import contextmanager

@contextmanager
def managed_resource():
    resource = {"closed": False}
    try:
        yield resource
    finally:
        resource["closed"] = True

with managed_resource() as resource:
    print(resource["closed"])  # False

print(resource["closed"])      # True
```

这里的 yield 不是在返回多条业务数据，而是把资源暂时交给 with 块使用。`@contextmanager` 要求一次上下文使用恰好 yield 一次。需要异步获取和释放资源时，使用 `@asynccontextmanager`、`async with` 和异步清理函数。[contextlib](https://docs.python.org/3.12/library/contextlib.html)

## 异常与模块

异常让错误沿调用链传播，由能够决定如何处理它的一层接住。`try` 包含可能失败的操作，`except` 处理指定异常，`else` 在没有异常时执行，`finally` 用于无论正常或异常退出都需要完成的清理。

```python
def parse_page(value: str) -> int:
    try:
        page = int(value)
    except ValueError as error:
        raise ValueError("页码必须是整数") from error
    if page < 1:
        raise ValueError("页码必须大于零")
    return page
```

`raise` 不带参数时重新抛出当前异常，保留原有信息；`raise NewError(...) from error` 表达转换后的错误由谁引起；`from None` 隐藏展示中的原始异常链。处理错误时应保留有用的诊断信息，同时避免把密码、密钥或内部 SQL 原样返回外部。

不要把 `except Exception: return None` 当成通用容错，否则调用方无法区分“没有数据”和“查询失败”。也不要在 finally 中随意 return，它可能覆盖原本的返回值或异常。

模块通常是一个 `.py` 文件，导入会执行其顶层代码；在常规导入流程中，已经加载的模块会从模块缓存复用。数据库连接池等模块级对象通常在同一进程内共享，但不同工作进程各有自己的内存，并不是跨进程单例。

`if __name__ == "__main__":` 让某段代码只在直接运行模块时执行，而不是被导入时执行。模块导入路径与启动方式有关，`python -m package.module` 按包结构执行；把导入问题全靠修改工作目录或拼接 `sys.path` 处理，会让代码难以复用。[Python 模块](https://docs.python.org/3.12/tutorial/modules.html)

## 协程、事件循环与并发

`async def` 定义协程函数。调用它得到协程对象，不会像普通函数那样立刻把函数体执行完；`await` 协程或把它交给 Task 调度，才会推动执行。

事件循环在多个任务之间协作调度。某个任务等待网络、数据库或定时器时，其他就绪任务可以继续运行；如果一个任务长时间执行同步代码、不交出控制权，事件循环上的其他任务也会受影响。`await` 表达“等待一个可等待对象”，但不是任何 await 都必然发生切换：被等待对象可能已经就绪。

```python
import asyncio

async def fetch_value(name: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return name

async def sequential():
    first = await fetch_value("A", 1)
    second = await fetch_value("B", 1)
    return first, second

async def concurrent():
    return await asyncio.gather(
        fetch_value("A", 1),
        fetch_value("B", 1),
    )

print(asyncio.run(concurrent()))
```

顺序版本先等 A 再启动 B，约需两秒；并发版本让两个等待重叠，约需一秒。并发改善的是等待的利用率，不会把同一个 CPU 计算自动拆给多个核心。[协程与任务](https://docs.python.org/3.12/library/asyncio-task.html)

Task 是由事件循环调度的协程执行单元，`asyncio.create_task()` 会安排协程运行。创建后仍应明确谁等待它、接收异常和负责取消，不能认为“已经创建 Task”就等于业务完成。

Python 3.11 起可以用 `TaskGroup` 约束一组相关任务的生命周期。退出上下文会等待组内任务；一个任务出现非取消异常时，组会取消其余任务并组织异常传播，适合要求“一组任务一起管理”的逻辑。

```python
async def grouped():
    async with asyncio.TaskGroup() as group:
        first = group.create_task(fetch_value("A", 1))
        second = group.create_task(fetch_value("B", 1))
    return first.result(), second.result()
```

`asyncio.run()` 用于同步程序的顶层入口，会管理事件循环。已经运行在 FastAPI 等异步环境里时，直接 await，不要在路由内再次调用 `asyncio.run()`。

异步生成器把等待与逐段产出结合在一起，适合读取网络流。`async def` 中出现 yield 后，调用得到的是异步生成器，需要 `async for` 消费，而不是 await 整个生成器。

```python
async def pieces():
    for text in ["你", "好"]:
        await asyncio.sleep(0.1)
        yield text

async def read_pieces():
    async for text in pieces():
        print(text)
```

## 超时、取消与阻塞操作

超时是一种控制任务生命周期的方式。`asyncio.timeout()` 为一段异步代码设置时间范围，超时后通过取消推动退出，并在上下文外表现为 `TimeoutError`。

```python
async def limited_request():
    try:
        async with asyncio.timeout(0.1):
            await fetch_value("slow", 1)
    except TimeoutError:
        return "请求超时"
```

取消是协作式的，请求取消后，任务通常在下一个可取消的等待点收到 `CancelledError`。应在 finally 里关闭连接等资源，确实捕获取消异常时，清理后通常继续抛出，而不是把停止操作伪装成成功返回。

```python
async def use_connection(connection):
    try:
        return await connection.read()
    except asyncio.CancelledError:
        raise
    finally:
        await connection.aclose()
```

`CancelledError` 继承自 `BaseException`，普通 `except Exception` 不会捕获它。如果外层使用会反复触发取消的取消域，清理中的 await 也需要相应保护；保护清理不等于让整个任务忽略用户取消。

`time.sleep()`、同步 HTTP 请求和直接执行的密码哈希不会因为写在 async 函数里就变成异步。对于需要兼容的阻塞调用，可以交给工作线程，避免占住事件循环线程：

```python
from pathlib import Path

async def read_document(path: Path) -> str:
    return await asyncio.to_thread(path.read_text, encoding="utf-8")
```

线程封装主要解决事件循环被阻塞的问题，不保证 Python 的 CPU 密集计算获得多核加速，也不保证取消等待时底层线程就立刻停止。计算量大时需要单独考虑执行方式和任务生命周期。[异步运行与线程](https://docs.python.org/3.12/library/asyncio-task.html#running-in-threads)

## JSON、时间与配置

Python 字典是内存对象，JSON 是文本交换格式。`json.dumps()` 把对象编码成字符串，`json.loads()` 把 JSON 文本解析成 Python 对象；字典、列表不能因为内容看起来像 JSON 就直接当网络字节发送。

```python
import json

payload = {"title": "你好", "visible": True}
text = json.dumps(payload, ensure_ascii=False)
restored = json.loads(text)

print(type(text).__name__)      # str
print(type(restored).__name__)  # dict
```

`ensure_ascii=False` 让中文直接保留在 JSON 文本里，不负责网络编码。真正传输时还需要 UTF-8 等编码。标准 JSON 不直接支持 datetime，要先按约定转换为字符串，或交给提供序列化能力的模型处理。[JSON](https://docs.python.org/3.12/library/json.html)

时间对象既可能有时区信息，也可能没有。`datetime.now()` 返回不带时区的本地时间，`datetime.now(timezone.utc)` 返回带 UTC 时区的时间；带时区与不带时区的时间不应混在一起直接比较。

```python
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)
expires_at = now + timedelta(days=7)
text = expires_at.isoformat()
restored = datetime.fromisoformat(text)
```

`.isoformat()` 的结果有没有时区偏移，取决于原对象有没有时区信息；字符串长得像时间不代表自动具有 UTC 语义。数据库、服务端和前端应约定同一种解释方式。Python 3.12 中 `datetime.utcnow()` 已弃用，新代码可使用带时区的 UTC 时间。[datetime](https://docs.python.org/3.12/library/datetime.html)

环境变量通常以字符串形式存在，`os.getenv("TIMEOUT", "30")` 在变量不存在时返回默认值，变量显式设为空字符串时不会回退。读取超时、开关或扩展参数时，要按目标类型转换并检查范围。

```python
import os

timeout = float(os.getenv("HTTP_TIMEOUT", "30"))
if timeout <= 0:
    raise ValueError("HTTP_TIMEOUT 必须大于零")
```

`bool("false")` 仍是 True，因为它是非空字符串，布尔配置应约定可接受的文本再解析。JSON 对象形式的扩展配置除了能成功解析，还应检查解析结果确实是字典，而不是列表或数字。

外部数据进入程序后，接下来通常需要结构校验与明确的输入输出边界，可继续阅读 [FastAPI](fastapi.md)。
