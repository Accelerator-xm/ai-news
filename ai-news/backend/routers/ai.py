from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from config.ai_conf import AIConfigurationError, AISettings, get_ai_settings
from schemas.ai import ChatRequest
from services.ai import AIServiceError, open_chat_stream
from utils.response import success_response

router = APIRouter(prefix="/api/ai", tags=["ai"])

# 聊天逻辑
# GET /api/ai/config: 先检查必要配置是否存在
# POST /api/ai/chat: 再提交对话，接收回答（SSE 流）


def get_settings() -> AISettings:
    try:
        return get_ai_settings()
    except AIConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None


@router.get("/config")
async def get_config(settings: AISettings = Depends(get_settings)):
    """
    检查配置
    
    有配置返回true
    """
    return success_response(data={"configured": settings.configured})


@router.post("/chat")
async def chat(body: ChatRequest, settings: AISettings = Depends(get_settings)):
    """对话请求：sse"""
    try:
        stream = await open_chat_stream(settings, body.messages)
    except AIServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    return StreamingResponse(
        stream.events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        background=BackgroundTask(stream.aclose),
    )
