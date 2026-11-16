from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatMessage(BaseModel):
    """单条消息"""
    # extra="forbid": 拒绝未声明字段
    # str_strip_whitespace=True: 去掉字符串首尾空
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    # Literal[...]: 可选项
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ChatRequest(BaseModel):
    """对话请求"""

    model_config = ConfigDict(extra="forbid")
    # 消息列表
    messages: list[ChatMessage] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def validate_conversation(self):
        if self.messages[-1].role != "user":
            # 最后一条必须是 user
            raise ValueError("对话必须以用户消息结束")
        if sum(len(message.content) for message in self.messages) > 100000:
            # 所有消息内容合计不超过 100000 个字符
            raise ValueError("对话过长，请开启新对话")
        return self
