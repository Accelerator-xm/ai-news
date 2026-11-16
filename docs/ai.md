# AI 对话与流式输出

AI 聊天通常由浏览器管理交互，后端管理供应商配置与请求，上游模型生成内容。把对话数据、供应商协议和传输协议分开，可以在不重写页面的情况下切换模型服务。

## 消息与上下文

模型请求通常包含按顺序排列的 messages。user 表示用户输入，assistant 表示模型回答；系统提示用于设定行为，是否使用以及放在哪里取决于供应商协议。通用问答不需要自动附带新闻或其他业务数据，模型能看到什么由本次实际发送的内容决定。

```json
{
  "messages": [
    {"role": "user", "content": "什么是协程？"},
    {"role": "assistant", "content": "协程可以在等待时暂停并恢复执行。"},
    {"role": "user", "content": "和线程有什么区别？"}
  ]
}
```

每次请求附带历史消息，模型才能利用前文。另一种方式是由服务端保存会话，客户端发送会话 ID，再由服务端组装历史；一个 ID 本身不会让供应商自动知道未提交的内容。

浏览器里的 id、loading、error、status 用于界面管理，不必原样发给供应商。请求前可以只选择 role 和 content，并排除最后一条正在等待回答的空占位消息。

消息长度不等于 token 数量，模型的输入上下文和输出预算也不是同一个限制。应用可以先限制消息条数和字符总数，再按需要采用裁剪、摘要等上下文策略；不能让对话无限增长并假定供应商会永远接收。

## 后端配置与协议适配

供应商地址、密钥、模型和默认参数由后端管理，浏览器只调用自己的聊天接口。浏览器环境中的构建变量会进入客户端代码，因此适合保存 API 地址，不适合保存供应商密钥。

不同服务的认证头、请求体和结束标记可能不同。适配器负责把统一消息转换为供应商请求，再把供应商事件转换为统一的“文字片段、是否完成”等信息。网络连接、超时和资源关闭则可以由共享的传输层处理。

```python
class AnthropicAdapter:
    def parse(self, data: dict) -> tuple[str, bool]:
        if data.get("type") == "content_block_delta":
            delta = data.get("delta", {})
            return delta.get("text", "") if delta.get("type") == "text_delta" else "", False
        if data.get("type") == "content_block_start":
            block = data.get("content_block", {})
            return block.get("text", "") if block.get("type") == "text" else "", False
        return "", data.get("type") == "message_stop"
```

这里摘取 Anthropic 适配器的解析方法：文本开始或增量事件返回文字，message_stop 表示正常结束，其他事件返回空文字和未完成。Chat Completions 适配器则从 choices 中提取 delta 和 finish_reason；两者最终都返回 `(文字, 是否完成)`，前端只需处理后端统一的事件。某家供应商兼容一种接口格式，不代表它兼容该品牌所有接口或所有模型参数。

“配置已填写”与“服务实际可用”应分开：存在地址、密钥和模型只满足本地检查，权限、额度和网络状态要在真实请求中才能确认。前端配置检查只需拿到必要状态，不必获取密钥或完整上游地址。

## SSE 与逐段传输

SSE 在 HTTP 响应中按文本事件传输数据，Content-Type 为 `text/event-stream`。event 指定事件名，data 包含事件内容，空行结束一条事件；一条事件也可以有多行 data。事件名 delta、done、error 可以由应用自行约定。[SSE 格式](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

```text
event: delta
data: {"content":"你好"}

event: done
data: {}

```

流式输出需要整条链路都持续转发：请求体中的 stream 参数告诉模型生成流；HTTP 客户端的流式读取选项让后端不先等待完整响应体；StreamingResponse 再把生成器的内容逐段发送给浏览器。

```python
import json
from collections.abc import AsyncIterator

def encode_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

async def iter_sse_data(lines: AsyncIterator[str]) -> AsyncIterator[str]:
    data = []
    async for line in lines:
        if not line:
            if data:
                yield "\n".join(data)
                data = []
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    if data:
        yield "\n".join(data)
```

iter_sse_data 接收 HTTPX `response.aiter_lines()` 产生的文本行，用空行划分事件，将多行 data 拼接后 yield。随后由调用方执行 json.loads 和适配器解析；encode_event 再把提取的文字包装为向浏览器发送的事件。

流结束时，生成器会交出剩余的 data，但这不代表模型正常完成。调用方还需要检查 `[DONE]` 或适配器返回的完成标记，再发送 done；不能只因为迭代结束就认定成功。

网络块、字符、SSE 事件与 JSON 对象是四种边界。上游每次产生的内容不一定是一整个词或一个字，后端一次读取也不一定恰好获得一条事件。应先增量解码和分帧，再解析 JSON。

代理缓冲可能使后端已经逐段 yield，浏览器却最后一次收到大量内容。禁用相关缓冲、避免响应转换和配置合理读取超时，都是让流真正及时到达的组成部分；单独设置一个 stream 参数并不足够。

## 浏览器如何消费流

原生 EventSource 主要提供 GET 订阅，聊天常需要 POST JSON 消息，因此可以用 fetch 获取响应流，再自行解析 SSE。

```javascript
const controller = new AbortController()
const response = await fetch('/api/ai/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  },
  body: JSON.stringify({ messages }),
  signal: controller.signal,
})
```

先检查 HTTP 状态，错误响应可能仍是普通 JSON；成功后再读取 response.body。TextDecoder 的 stream 选项保留不完整 UTF-8 字节，避免一个汉字被两个网络块拆开时产生乱码。

```javascript
const reader = response.body.getReader()
const decoder = new TextDecoder()
let buffer = ''

const { done, value } = await reader.read()
buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
```

实际处理要循环读取，将 buffer 中完整的空行分隔事件逐个取出，保留未完成部分；然后合并 data 行并解析 JSON。不能直接对每次 read 的结果调用 JSON.parse，也不能因为它看起来是纯文本就丢掉事件边界。

收到 delta 后把 content 追加到同一条回答，收到 done 才标记成功。Markdown 可以随着内容增长重新渲染，但 HTML 输出还需要清理，避免把模型或用户提供的 HTML 不经处理插入页面。

消息状态通常区分生成中、完成、停止和失败。失败时保留已经生成的文字，有助于表达“回答生成到这里中断”，而不是把它伪装成完整答案或直接丢掉。

## 错误、取消与资源释放

流开始之前，配置错误、请求校验错误和上游连接错误可以通过普通 HTTP 错误响应表达。流开始之后，状态码和响应头通常已经发出，应使用 error 事件或断开连接表达失败，不能再替换成另一份 JSON 响应。

供应商返回的鉴权失败是后端调用上游失败，不等于网站访问者的登录 Token 无效。错误转换应保留足够明确的提示，同时避免原始上游错误包含密钥或内部请求细节。

用户点击停止时，AbortController 取消浏览器请求；后端还需要停止读取上游并关闭客户端资源。只停止页面上追加文字，不能保证上游不再继续生成。

```python
async def read_upstream(response):
    try:
        async for line in response.aiter_lines():
            yield line
    finally:
        await response.aclose()
```

这是资源生命周期示例，实际转发还应先按 SSE 分帧。取消异常应在必要清理后继续传播，某些取消模型中还需要保护清理阶段的 await，避免再次取消导致关闭未完成。

“重新生成”通常重新提交最后一个用户问题，是否携带之前中断的回答要有明确策略；“新对话”则清除旧上下文并终止当前请求。界面可以缓存消息，但没有服务端持久化时，刷新页面不会自动恢复完整对话。
