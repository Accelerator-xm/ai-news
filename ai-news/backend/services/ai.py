import asyncio
import json
import logging
from collections.abc import AsyncIterator

import anyio
import httpx

from config.ai_conf import AISettings
from schemas.ai import ChatMessage

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


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


# 适配器封装
# build_request(settings, messages) : 构造供应商需要的参数, 返回请求头和请求体
# parse(data)  : 从供应商事件取出文字、完成标记

class OpenAIAdapter:
    def build_request(self, settings: AISettings, messages: list[ChatMessage]):
        """构造供应商需要的参数"""

        # 解包请求头 extra_headers
        headers = {
            "Authorization": f"Bearer {settings.api_key}", 
            **settings.extra_headers
        }
        # 解包请求体 extra_body
        body = {
            **settings.extra_body,
            "model": settings.model,
            "messages": [
                *([{"role": "system", "content": settings.system_prompt}] if settings.system_prompt else []),
                *[message.model_dump() for message in messages],
            ],
            "stream": True,
            settings.token_parameter: settings.max_tokens,
        }
        return headers, body

    def parse(self, data: dict) -> tuple[str, bool]:
        choices = data.get("choices") or []
        if not choices:
            return "", False
        choice = choices[0]
        content = (choice.get("delta") or {}).get("content") or ""
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict) and isinstance(part.get("text"), str))
        return content if isinstance(content, str) else "", choice.get("finish_reason") is not None


class AnthropicAdapter:
    def build_request(self, settings: AISettings, messages: list[ChatMessage]):
        """构造供应商需要的参数"""

        # 解包请求头 extra_headers
        headers = {
            "x-api-key": settings.api_key,
            "anthropic-version": "2023-06-01",
            **settings.extra_headers,
        }
        # 解包请求体 extra_body
        body = {
            **settings.extra_body,
            "model": settings.model,
            "messages": [message.model_dump() for message in messages],
            "max_tokens": settings.max_tokens,
            "stream": True,
        }
        if settings.system_prompt:
            body["system"] = settings.system_prompt
        return headers, body

    def parse(self, data: dict) -> tuple[str, bool]:
        if data.get("type") == "content_block_delta":
            delta = data.get("delta", {})
            return delta.get("text", "") if delta.get("type") == "text_delta" else "", False
        if data.get("type") == "content_block_start":
            block = data.get("content_block", {})
            return block.get("text", "") if block.get("type") == "text" else "", False
        return "", data.get("type") == "message_stop"


ADAPTERS = {"openai": OpenAIAdapter, "anthropic": AnthropicAdapter}


def create_http_client(settings: AISettings) -> httpx.AsyncClient:
    """创建 HTTP 请求对象"""
    return httpx.AsyncClient(timeout=httpx.Timeout(settings.timeout, connect=15))


class AIStream:
    def __init__(self, client: httpx.AsyncClient, response: httpx.Response, adapter):
        self.client = client
        self.response = response
        self.adapter = adapter
        self.closed = False

    async def aclose(self):
        if not self.closed:
            self.closed = True
            with anyio.CancelScope(shield=True):
                await self.response.aclose()
                await self.client.aclose()

    async def events(self):
        """
        读取、转换和判断结束
        
        逻辑：
        → HTTPX 读取上游内容
        → aiter_lines() 得到文本行
        → iter_sse_data() 拼出一条 SSE 的 data
        → json.loads() 得到字典
        → adapter.parse() 得到文字与完成标记
        → encode_event() 编码成本项目的 SSE
        """

        received_text = False
        completed = False
        try:
            async for raw in iter_sse_data(self.response.aiter_lines()):
                if raw.strip() == "[DONE]":
                    completed = True
                    break
                
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    raise AIServiceError("AI 服务返回了无法识别的流式数据，请检查供应商协议。") from None
                if not isinstance(data, dict):
                    raise AIServiceError("AI 服务返回格式有误。")
                if data.get("error") or data.get("type") == "error":
                    raise AIServiceError("AI 服务暂时无法继续生成，请稍后重试。")
                
                text, done = self.adapter.parse(data)
                
                if text:
                    received_text = True
                    yield encode_event("delta", {"content": text})
                
                if done:
                    completed = True
                    break
            if not received_text:
                raise AIServiceError("AI 服务没有返回文字，请检查模型配置或重试。")
            if not completed:
                raise AIServiceError("生成连接意外中断，已保留收到的内容，请重试。")
            yield encode_event("done", {})
        except asyncio.CancelledError:
            raise
        except (httpx.HTTPError, AIServiceError, KeyError, TypeError, AttributeError) as error:
            message = str(error) if isinstance(error, AIServiceError) else "生成连接中断，已保留收到的内容，请重试。"
            logger.warning("AI stream interrupted: %s", type(error).__name__)
            yield encode_event("error", {"message": message})
        finally:
            await self.aclose()


async def open_chat_stream(settings: AISettings, messages: list[ChatMessage]) -> AIStream:
    """
    连接供应商，检查响应状态和类型，得到 AIStream 对象
    
    执行流程：
    → 检查必要配置
    → 选择 adapter
    → 构造请求头、请求体
    → 创建 HTTPX 客户端
    → 发送请求，保留响应流
    → 检查上游状态与 Content-Type
    → 返回 AIStream
    """
    
    if not settings.configured:
        raise AIServiceError("AI 助手尚未配置，请先在后端 .env 中设置服务密钥和模型。", 503)
    
    # 选择适配器
    adapter = ADAPTERS[settings.provider]()
    # 获取请求头请求体
    headers, body = adapter.build_request(settings, messages)
    # 创建http请求对象
    client = create_http_client(settings)
    try:
        request = client.build_request("POST", settings.endpoint, headers={"Accept": "text/event-stream", **headers}, json=body)
        
        # 流式输出
        # 请求体的 stream: true	    告诉供应商采用流式输出
        # HTTPX 的 stream=True	    不等待完整响应体下载完再处理
        # FastAPI 的 StreamingResponse	    把后端产生的内容逐段发送给浏览器
        response = await client.send(request, stream=True)
    except asyncio.CancelledError:
        with anyio.CancelScope(shield=True):
            await client.aclose()
        raise
    except httpx.HTTPError as error:
        await client.aclose()
        logger.warning("AI connection failed: %s", type(error).__name__)
        raise AIServiceError("暂时无法连接 AI 服务，请检查后端地址、网络或稍后重试。", 504 if isinstance(error, httpx.TimeoutException) else 502) from None
    if response.status_code >= 400:
        status = response.status_code
        await response.aclose()
        await client.aclose()
        message = {
            401: "AI 服务鉴权失败，请检查后端密钥。",
            403: "当前密钥没有访问该模型的权限。",
            404: "AI 服务地址或模型不存在，请检查后端配置。",
            429: "AI 服务请求过于频繁或额度不足，请稍后重试。",
        }.get(status, "AI 服务暂时不可用，请稍后重试。")
        raise AIServiceError(message, 429 if status == 429 else 502)
    if "text/event-stream" not in response.headers.get("content-type", "").lower():
        await response.aclose()
        await client.aclose()
        raise AIServiceError("供应商未返回 SSE 流，请检查接口地址和流式配置。")
    return AIStream(client, response, adapter)
