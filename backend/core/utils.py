"""通用工具函数 — 全引擎共享"""

import json
import re


def extract_json(text: str) -> dict:
    """从 LLM 返回的文本中提取 JSON（兼容 markdown 代码块包裹）。

    提取策略（按优先级）：
    1. 直接 json.loads
    2. 从 ```json ... ``` 代码块提取
    3. 从第一个 { 到最后一个 } 截取

    Raises:
        ValueError: 无法提取 JSON
    """
    if not text or not text.strip():
        raise ValueError("LLM 返回内容为空")

    text = text.strip()

    # 策略 1：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 策略 2：从 ```json ... ``` 代码块中提取
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 策略 3：找到第一个 { 到最后一个 } 的范围
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从 LLM 返回内容中提取 JSON：{text[:200]}")


def extract_json_safe(text: str, default: dict | None = None) -> dict:
    """extract_json 的安全版本，解析失败返回 default 而非抛异常。"""
    try:
        return extract_json(text)
    except (ValueError, json.JSONDecodeError):
        return default if default is not None else {}
