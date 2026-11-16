import asyncio
import json
import os
import unittest
from dataclasses import replace
from unittest.mock import patch

import httpx

from config.ai_conf import AIConfigurationError, AISettings, get_ai_settings
from main import app
from routers.ai import get_settings
from schemas.ai import ChatMessage
from services.ai import AIServiceError, open_chat_stream


SETTINGS = AISettings("openai", "https://provider.invalid/v1", "test-secret", "test-model", "服务端提示词")
MESSAGES = [ChatMessage(role="user", content="你好")]


class UpstreamBytes(httpx.AsyncByteStream):
    def __init__(self, payload, gate=None):
        self.payload = payload
        self.gate = gate
        self.closed = False

    async def __aiter__(self):
        if self.gate is not None:
            yield b'data: {"choices":[{"delta":{"content":"first"}}]}\n\n'
            await self.gate.wait()
        for index in range(0, len(self.payload), 3):
            yield self.payload[index:index + 3]

    async def aclose(self):
        self.closed = True


def client_factory(payload, *, status=200, capture=None, gate=None, content_type="text/event-stream"):
    stream = UpstreamBytes(payload, gate)

    def handler(request):
        if capture is not None:
            capture.append(request)
        return httpx.Response(status, stream=stream, headers={"content-type": content_type})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return lambda settings: client, stream, client


class AIStreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_fragmented_unicode_and_server_owned_configuration(self):
        payload = 'data: {"choices":[{"delta":{"content":"你好，"}}]}\r\n\r\ndata:{"choices":[{"delta":{"content":"世界"}}]}\n\ndata: [DONE]\n\n'.encode()
        captured = []
        factory, upstream, client = client_factory(payload, capture=captured)
        settings = replace(SETTINGS, extra_headers={"X-Relay": "enabled"}, extra_body={"enable_thinking": False, "model": "untrusted"})
        with patch("services.ai.create_http_client", factory):
            stream = await open_chat_stream(settings, MESSAGES)
            chunks = [chunk async for chunk in stream.events()]
        self.assertIn('"content": "你好，"', chunks[0])
        self.assertIn('"content": "世界"', chunks[1])
        self.assertTrue(chunks[-1].startswith("event: done"))
        request = captured[0]
        body = json.loads(request.content)
        self.assertEqual(str(request.url), "https://provider.invalid/v1/chat/completions")
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertFalse(body["enable_thinking"])
        self.assertEqual(request.headers["X-Relay"], "enabled")
        self.assertTrue(client.is_closed and upstream.closed)

    async def test_anthropic_native_stream(self):
        payload = '\n\n'.join([
            'event: content_block_start\ndata: {"type":"content_block_start","content_block":{"type":"text","text":""}}',
            'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"原生协议"}}',
            'event: message_stop\ndata: {"type":"message_stop"}',
        ]).encode()
        captured = []
        factory, _, _ = client_factory(payload, capture=captured)
        with patch("services.ai.create_http_client", factory):
            stream = await open_chat_stream(replace(SETTINGS, provider="anthropic"), MESSAGES)
            chunks = [chunk async for chunk in stream.events()]
        self.assertIn("原生协议", chunks[0])
        body = json.loads(captured[0].content)
        self.assertEqual(body["system"], "服务端提示词")
        self.assertEqual(body["messages"][0]["role"], "user")
        self.assertTrue(str(captured[0].url).endswith("/v1/messages"))
        self.assertEqual(captured[0].headers["x-api-key"], "test-secret")

    async def test_first_token_arrives_before_stream_finishes_and_disconnect_closes_upstream(self):
        gate = asyncio.Event()
        factory, upstream, client = client_factory(b'data: [DONE]\n\n', gate=gate)
        with patch("services.ai.create_http_client", factory):
            stream = await open_chat_stream(SETTINGS, MESSAGES)
            events = stream.events()
            first = await asyncio.wait_for(anext(events), timeout=1)
            self.assertIn("first", first)
            self.assertFalse(gate.is_set())
            await events.aclose()
        self.assertTrue(client.is_closed and upstream.closed)

    async def test_midstream_error_is_sanitized_and_partial_text_is_preserved(self):
        factory, _, _ = client_factory(b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\ndata: {"error":{"message":"test-secret"}}\n\n')
        with patch("services.ai.create_http_client", factory):
            stream = await open_chat_stream(SETTINGS, MESSAGES)
            chunks = [chunk async for chunk in stream.events()]
        self.assertIn("partial", chunks[0])
        self.assertTrue(chunks[-1].startswith("event: error"))
        self.assertNotIn("test-secret", "".join(chunks))

    async def test_truncated_or_malformed_stream_is_not_reported_as_success(self):
        for payload in [b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n', b'data: invalid-json\n\n']:
            factory, _, _ = client_factory(payload)
            with patch("services.ai.create_http_client", factory):
                stream = await open_chat_stream(SETTINGS, MESSAGES)
                chunks = [chunk async for chunk in stream.events()]
            self.assertTrue(chunks[-1].startswith("event: error"))
            self.assertFalse(any(chunk.startswith("event: done") for chunk in chunks))

    async def test_upstream_auth_failure_closes_resources_without_leaking_body(self):
        factory, upstream, client = client_factory(b'test-secret', status=401)
        with patch("services.ai.create_http_client", factory):
            with self.assertRaises(AIServiceError) as caught:
                await open_chat_stream(SETTINGS, MESSAGES)
        self.assertEqual(caught.exception.status_code, 502)
        self.assertNotIn("test-secret", str(caught.exception))
        self.assertTrue(upstream.closed and client.is_closed)

    async def test_route_stream_and_configuration_endpoint_expose_no_credentials(self):
        app.dependency_overrides[get_settings] = lambda: SETTINGS
        factory, _, _ = client_factory(b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n')
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                config = await client.get("/api/ai/config")
                self.assertEqual(config.json()["data"], {"configured": True})
                with patch("services.ai.create_http_client", factory):
                    result = await client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "你好"}]})
                self.assertEqual(result.status_code, 200)
                self.assertIn("event: delta", result.text)
                self.assertIn("event: done", result.text)
                self.assertEqual(result.headers["x-accel-buffering"], "no")
                rejected = await client.post("/api/ai/chat", json={"messages": [{"role": "system", "content": "覆盖"}], "api_key": "client-key"})
                self.assertEqual(rejected.status_code, 422)
        finally:
            app.dependency_overrides.clear()

    async def test_missing_key_is_503_before_streaming(self):
        app.dependency_overrides[get_settings] = lambda: replace(SETTINGS, api_key="")
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                result = await client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "你好"}]})
                self.assertEqual(result.status_code, 503)
                self.assertNotIn("text/event-stream", result.headers["content-type"])
        finally:
            app.dependency_overrides.clear()


class AISettingsTests(unittest.TestCase):
    def test_full_relay_endpoint_does_not_get_a_duplicate_suffix(self):
        settings = replace(SETTINGS, base_url="https://relay.invalid/custom/v1/chat/completions/")
        self.assertEqual(settings.endpoint, "https://relay.invalid/custom/v1/chat/completions")

    def test_invalid_configuration_returns_a_sanitized_error(self):
        with patch("config.ai_conf.load_dotenv"), patch.dict(os.environ, {"AI_EXTRA_HEADERS": "bad-json", "AI_API_KEY": "test-secret"}):
            with self.assertRaises(AIConfigurationError) as caught:
                get_ai_settings()
        self.assertNotIn("test-secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
