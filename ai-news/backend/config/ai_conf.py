import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


class AIConfigurationError(ValueError):
    pass


# dataclass 自动生成构造函数等方法
# frozen=True 表示创建后不能直接重新赋值
@dataclass(frozen=True)
class AISettings:
    provider: str
    base_url: str
    # field(repr=False)：打印配置对象时不显示密钥
    api_key: str = field(repr=False)
    model: str
    system_prompt: str
    timeout: float = 120
    max_tokens: int = 4096
    token_parameter: str = "max_tokens"
    # field(default_factory=dict)：没有传值时，调用 dict()
    extra_headers: dict = field(default_factory=dict, repr=False)
    extra_body: dict = field(default_factory=dict)

    # @property 允许像访问属性一样调用：settings.endpoint
    @property
    def endpoint(self) -> str:
        """
        计算最终请求地址
        
        兼容opneai的请求地址: chat/completions
        anthropic地址: /messages
        """
        # 去掉地址末尾的 /
        base = self.base_url.rstrip("/")

        if base.endswith(("/chat/completions", "/messages")):
            # 已经是完整地址
            return base
        
        # 只是基础地址，根据协议补全路径
        return base + ("/messages" if self.provider == "anthropic" else "/chat/completions")

    @property
    def configured(self) -> bool:
        """
        判断必要配置有没有填写:

        地址、模型、密钥
        """
        return bool(self.base_url and self.model and self.api_key)


def get_ai_settings() -> AISettings:
    """获取ai配置"""

    # 加载 .env 配置
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    
    try:
        settings = AISettings(
            provider=os.getenv("AI_PROVIDER", "openai").strip().lower(),
            base_url=os.getenv("AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip(),
            api_key=os.getenv("AI_API_KEY", "").strip(),
            model=os.getenv("AI_MODEL", "qwen3-max-preview").strip(),
            system_prompt=os.getenv("AI_SYSTEM_PROMPT", ""),
            timeout=float(os.getenv("AI_TIMEOUT", "120")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
            token_parameter=os.getenv("AI_TOKEN_PARAMETER", "max_tokens"),
            extra_headers=json.loads(os.getenv("AI_EXTRA_HEADERS", "{}")),
            extra_body=json.loads(os.getenv("AI_EXTRA_BODY", "{}")),
        )

        # 检查配置是否合法：
        # - provider 必须是已支持的协议。
        # - 地址必须使用 HTTP 或 HTTPS，并具有主机名。
        # - timeout、max_tokens 必须大于零。
        # - token 参数名必须是允许的两种之一。
        # - extra_headers 必须是字典，且键和值都是字符串。
        # - extra_body 必须是字典。
        url = urlsplit(settings.base_url)
        if (settings.provider not in {"openai", "anthropic"}
                or url.scheme not in {"http", "https"} or not url.hostname
                or settings.timeout <= 0 or settings.max_tokens <= 0
                or settings.token_parameter not in {"max_tokens", "max_completion_tokens"}
                or not isinstance(settings.extra_headers, dict)
                or not all(isinstance(k, str) and isinstance(v, str) for k, v in settings.extra_headers.items())
                or not isinstance(settings.extra_body, dict)):
            raise ValueError
        return settings
    except (ValueError, TypeError):
        raise AIConfigurationError("AI 服务配置有误，请检查后端 .env 文件。") from None
