"""L3 Executor — 并行执行引擎

用 asyncio.gather() 实现 IO 密集型协程并发，尊重任务依赖关系。
支持增量执行模式：进化重组后仅执行变更的 Agent，未变更的复用上轮结果。
"""

import asyncio
import hashlib
import json
import time
from typing import Callable, Awaitable

from backend.core.llm_service import call_llm
from backend.core.state import HiveState


# 每个 Agent 的独立 token 预算（占总预算的比例）
AGENT_TOKEN_BUDGET_RATIO = 0.12  # 单 Agent 最多用总预算的 12%

# 模型级别超时配置（秒）——慢模型独立超时
MODEL_TIMEOUT: dict[str, int] = {
    "MODEL_ANALYSIS": 30,   # Claude Sonnet — 深度推理较慢
    "MODEL_ADVERSARY": 25,  # Gemini Flash — 偶尔慢
    "MODEL_RESEARCH": 20,   # GPT-4o-mini — 通常最快
    "MODEL_META": 30,       # Claude Sonnet
}
DEFAULT_TIMEOUT = 25        # 未配置模型的默认超时

# 超时后的 fallback 模型
FALLBACK_MODEL = "MODEL_RESEARCH"  # GPT-4o-mini 作为兜底


def _hash_config(config: dict) -> str:
    """对 Agent 配置取 hash，用于增量执行判断"""
    # 只取影响执行结果的关键字段
    key_fields = {
        "agent_id": config.get("agent_id"),
        "system_prompt": config.get("system_prompt"),
        "model_env_key": config.get("model_env_key"),
        "tools": config.get("tools"),
        "capability": config.get("capability"),
    }
    raw = json.dumps(key_fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_dependency_map(
    agent_configs: list[dict], task_graph: dict
) -> dict[str, list[str]]:
    """
    构建 agent_id → 依赖的 agent_id 列表 映射。
    Decomposer 输出的依赖在 subtask 级别（subtask_id），
    需要转换为 agent 级别。
    """
    # subtask_id → agent_id 映射
    subtask_to_agent: dict[str, str] = {}
    for config in agent_configs:
        sid = config.get("subtask_id")
        if sid:
            subtask_to_agent[sid] = config["agent_id"]

    # subtask_id → dependencies 映射
    subtask_deps: dict[str, list[str]] = {}
    for subtask in task_graph.get("subtasks", []):
        subtask_deps[subtask["id"]] = subtask.get("dependencies", [])

    # 构建 agent 级别的依赖
    dep_map: dict[str, list[str]] = {}
    for config in agent_configs:
        agent_id = config["agent_id"]
        subtask_id = config.get("subtask_id", "")
        deps = subtask_deps.get(subtask_id, [])
        # 将 subtask 依赖转换为 agent 依赖
        agent_deps = [
            subtask_to_agent[d] for d in deps if d in subtask_to_agent
        ]
        dep_map[agent_id] = agent_deps

    return dep_map


async def executor_engine(
    state: HiveState,
    agent_runner: Callable[[dict, str, int], Awaitable[dict]] | None = None,
) -> dict:
    """
    L3 Executor 引擎：并行执行所有 Agent 的子任务。

    Args:
        state: HiveState
        agent_runner: 可注入的 Agent 执行函数（用于测试 mock），
                      签名 (config, goal, token_budget) -> result_dict。
                      为 None 时使用真实 LLM 调用。

    Returns:
        更新 agent_results, agent_configs_hash, token_used
    """
    agent_configs = state["agent_configs"]
    task_graph = state["task_graph"]
    goal = state["goal"]
    total_budget = state["token_budget"]
    prev_hashes = state.get("agent_configs_hash", {})
    prev_results = state.get("agent_results", {})

    if agent_runner is None:
        agent_runner = _default_agent_runner

    # 计算每个 Agent 的独立 token 预算
    per_agent_budget = int(total_budget * AGENT_TOKEN_BUDGET_RATIO)

    # 计算新的配置 hash，判断增量执行
    new_hashes: dict[str, str] = {}
    agents_to_run: list[dict] = []
    reused_results: dict[str, dict] = {}

    for config in agent_configs:
        agent_id = config["agent_id"]
        h = _hash_config(config)
        new_hashes[agent_id] = h

        if agent_id in prev_hashes and prev_hashes[agent_id] == h and agent_id in prev_results:
            # 配置未变更，复用上轮结果
            reused_results[agent_id] = prev_results[agent_id]
        else:
            agents_to_run.append(config)

    # 构建依赖关系
    dep_map = _build_dependency_map(agent_configs, task_graph)

    # 用 asyncio Event 实现依赖等待
    completion_events: dict[str, asyncio.Event] = {}
    for config in agent_configs:
        event = asyncio.Event()
        aid = config["agent_id"]
        completion_events[aid] = event
        # 复用的 Agent 立即标记完成
        if aid in reused_results:
            event.set()

    # 收集结果
    results: dict[str, dict] = dict(reused_results)
    total_tokens_used = 0

    async def _run_one(config: dict) -> None:
        nonlocal total_tokens_used
        agent_id = config["agent_id"]
        model_key = config.get("model_env_key", "MODEL_RESEARCH")

        # 等待所有依赖完成（带超时防止死锁）
        deps = dep_map.get(agent_id, [])
        if deps:
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        *(completion_events[d].wait() for d in deps if d in completion_events)
                    ),
                    timeout=60.0,  # 依赖等待最多 60 秒
                )
            except asyncio.TimeoutError:
                # 依赖超时——使用空上下文继续执行，不要 hang 住整个流程
                pass

        # 执行（带模型级别超时 + fallback）
        timeout_sec = MODEL_TIMEOUT.get(model_key, DEFAULT_TIMEOUT)
        try:
            result = await asyncio.wait_for(
                agent_runner(config, goal, per_agent_budget),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            # 超时：用轻量 fallback 模型重试一次
            fallback_config = {**config, "model_env_key": FALLBACK_MODEL}
            try:
                result = await asyncio.wait_for(
                    agent_runner(fallback_config, goal, per_agent_budget),
                    timeout=DEFAULT_TIMEOUT,
                )
                result["_fallback"] = True
                result["_original_model"] = model_key
            except (asyncio.TimeoutError, Exception):
                # fallback 也失败——返回降级结果，不阻塞流程
                result = {
                    "agent_id": agent_id,
                    "actions": [{"type": "timeout", "content": f"模型 {model_key} 和 fallback 均超时"}],
                    "preliminary_result": f"[超时] Agent {agent_id} 执行超时，未能获取结果。",
                    "confidence": 0.1,
                    "tokens_used": 0,
                    "time_ms": int(timeout_sec * 1000),
                    "_timeout": True,
                }

        results[agent_id] = result
        total_tokens_used += result.get("tokens_used", 0)

        # 标记完成
        completion_events[agent_id].set()

    # 所有待执行 Agent 同时启动（内部通过 Event 等待依赖）
    await asyncio.gather(*[_run_one(c) for c in agents_to_run])

    return {
        "agent_results": results,
        "agent_configs_hash": new_hashes,
        "token_used": state.get("token_used", 0) + total_tokens_used,
    }


async def _default_agent_runner(
    config: dict, goal: str, token_budget: int
) -> dict:
    """默认的 Agent 执行器：调用真实 LLM 完成子任务"""
    agent_id = config["agent_id"]
    system_prompt = config.get("system_prompt", "")
    model_key = config.get("model_env_key", "MODEL_RESEARCH")
    search_strategy = config.get("search_strategy", {})

    start_ms = time.monotonic_ns() // 1_000_000

    # 构建执行 prompt
    sources_hint = ", ".join(search_strategy.get("sources", []))
    focus_hint = search_strategy.get("search_focus", "")

    exec_prompt = (
        f"项目目标：{goal}\n\n"
        f"你的具体任务：{config.get('subtask_id', agent_id)}\n\n"
        f"请完成以下工作：\n"
        f"1. 基于你的专业领域和思维框架，对目标进行深度分析\n"
        f"2. 优先从以下信息源获取数据：{sources_hint}\n"
        f"3. 分析重点：{focus_hint}\n"
        f"4. 给出你的初步结论，包含置信度（0-1）\n\n"
        f"请用以下 JSON 格式输出：\n"
        f'{{"analysis": "你的详细分析", "conclusion": "核心结论（一句话）", '
        f'"key_findings": ["发现1", "发现2", ...], "confidence": 0.xx, '
        f'"evidence": ["依据1", "依据2", ...]}}'
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": exec_prompt},
    ]

    # Demo 模式降低 max_tokens 加速响应
    effective_max = min(2000, token_budget)
    if config.get("_demo_mode"):
        effective_max = min(1200, token_budget)

    result = await call_llm(
        model_env_key=model_key,
        messages=messages,
        temperature=0.5,
        max_tokens=effective_max,
    )

    end_ms = time.monotonic_ns() // 1_000_000
    tokens_used = result["usage"].get("total_tokens", 0)

    # 尝试解析结构化输出
    content = result["content"]
    confidence = 0.7
    try:
        import re
        text = content.strip()
        # 尝试提取 JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            confidence = parsed.get("confidence", 0.7)
    except (json.JSONDecodeError, AttributeError):
        pass

    return {
        "agent_id": agent_id,
        "actions": [
            {"type": "analysis", "content": f"基于 {config.get('framework', 'N/A')} 框架的深度分析"},
        ],
        "preliminary_result": content,
        "confidence": confidence,
        "tokens_used": tokens_used,
        "time_ms": end_ms - start_ms,
    }
