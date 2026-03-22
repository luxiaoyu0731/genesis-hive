"""多模型 LLM 调用服务 — 统一走 OpenRouter 网关"""

import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# 全局 AsyncOpenAI 客户端，base_url 指向 OpenRouter
client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENROUTER_BASE_URL"),
)

# OpenRouter 推荐的额外 header
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/genesis-hive",
    "X-Title": "Genesis Hive",
}

# 模型环境变量 → 用途映射（仅用于文档和日志）
MODEL_ROLES = {
    "MODEL_RESEARCH": "调研型 Agent（速度优先）",
    "MODEL_ANALYSIS": "分析型 Agent（深度推理优先）",
    "MODEL_ADVERSARY": "魔鬼代言人（制造认知差异）",
    "MODEL_META": "元决策 Agent（Decomposer/Spawner/Evolver）",
    "MODEL_JUDGE": "裁判 LLM（共识检测）",
    "MODEL_COMPRESS": "摘要压缩（轻量模型）",
}


async def call_llm(
    model_env_key: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_format: dict | None = None,
    **kwargs,
) -> dict:
    """
    统一 LLM 调用入口。

    Args:
        model_env_key: 环境变量名（如 "MODEL_RESEARCH"），从 .env 解析实际模型 ID
        messages: OpenAI 格式的消息列表
        temperature: 采样温度
        max_tokens: 最大输出 token 数
        response_format: JSON Schema 约束输出格式（可选）

    Returns:
        dict 包含 content、model、usage 等信息
    """
    model = os.getenv(model_env_key)
    if not model:
        raise ValueError(f"环境变量 {model_env_key} 未配置，请检查 .env 文件")

    create_kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "extra_headers": OPENROUTER_HEADERS,
        **kwargs,
    }
    if response_format is not None:
        create_kwargs["response_format"] = response_format

    response = await client.chat.completions.create(**create_kwargs)

    # 提取 token 用量
    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "content": response.choices[0].message.content,
        "model": model,
        "usage": usage,
    }


async def call_llm_text(
    model_env_key: str,
    messages: list[dict],
    **kwargs,
) -> str:
    """简化版：只返回文本内容"""
    result = await call_llm(model_env_key, messages, **kwargs)
    return result["content"]
