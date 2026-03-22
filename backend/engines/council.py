"""L4 Council — 圆桌辩论引擎（Hive 核心）

五阶段辩论流程：
  Phase A 独立呈述 → Phase B 圆桌辩论 → Phase C 修正更新
  → Phase D 共识检测（裁判 LLM） → Phase E 辩论历史摘要压缩
"""

import asyncio
import json
import re

from backend.core.llm_service import call_llm
from backend.core.message_bus import MessageBus, BusMessage
from backend.core.state import HiveState
from backend.core.utils import extract_json as _extract_json


# ── Phase A：独立呈述 ──────────────────────────────────────

async def phase_a_present(
    agent_configs: list[dict],
    agent_results: dict[str, dict],
    bus: MessageBus,
) -> None:
    """每个 Agent 将初步结果以 preliminary_result 消息发布到总线"""
    for config in agent_configs:
        aid = config["agent_id"]
        result = agent_results.get(aid, {})
        preliminary = result.get("preliminary_result", "无结果")
        # 截断过长内容避免后续 token 爆炸
        if len(preliminary) > 1500:
            preliminary = preliminary[:1500] + "…（已截断）"
        bus.publish(BusMessage(
            from_agent=aid,
            to_agent="broadcast",
            type="preliminary_result",
            content=preliminary,
            confidence=result.get("confidence", 0.5),
        ))


# ── Phase B：圆桌辩论 ──────────────────────────────────────

DEBATE_SYSTEM_PROMPT = """你是一位参与圆桌辩论的专家。你已经听取了所有团队成员的初步观点。

## 你的任务

阅读其他 Agent 的初步结果，针对性地发表你的意见。你必须输出一个 JSON 数组，每个元素代表你对一位同事观点的回应。

## 输出格式（JSON 数组）

[
  {
    "to": "目标 agent_id",
    "type": "challenge | support | rebuttal | supplement | question",
    "content": "你的观点（中文，100-200字）",
    "references": ["被引用的 agent_id.preliminary_result"]
  }
]

## 发言类型说明

- challenge（质疑）：指出对方论证的薄弱环节或逻辑漏洞
- support（支持）：认同并补充支撑证据
- rebuttal（反驳）：直接反驳对方的结论或假设
- supplement（补充）：提供对方未覆盖的新视角或数据
- question（提问）：对不清楚的细节追问

## 规则

1. 你必须至少回应 2 位不同的同事
2. 不要回应自己
3. 发言必须有实质内容，不要空洞的"同意"或"不同意"
4. 回应时要引用具体的观点或数据
5. 魔鬼代言人应该更多使用 challenge 和 rebuttal

只输出 JSON 数组，不要输出其他内容。"""


async def phase_b_debate(
    agent_configs: list[dict],
    agent_results: dict[str, dict],
    bus: MessageBus,
    debate_history_summary: list[dict],
    goal: str,
) -> int:
    """
    圆桌辩论：每个 Agent 对其他 Agent 的结论发表意见。
    返回本轮消耗的 token 数。
    """
    # 收集所有 Agent 的初步结果摘要
    all_presentations = []
    for config in agent_configs:
        aid = config["agent_id"]
        result = agent_results.get(aid, {})
        pr = result.get("preliminary_result", "无结果")
        if len(pr) > 800:
            pr = pr[:800] + "…"
        all_presentations.append(f"[{aid}]（{config.get('role', '未知角色')}）：\n{pr}")

    presentations_text = "\n\n".join(all_presentations)

    # 如果有历史摘要，附加上
    history_text = ""
    if debate_history_summary:
        history_text = "\n\n## 前轮辩论摘要\n" + json.dumps(
            debate_history_summary, ensure_ascii=False, indent=2
        )

    total_tokens = 0

    # 每个 Agent 并发发言
    async def _agent_debate(config: dict) -> int:
        aid = config["agent_id"]
        model_key = config.get("model_env_key", "MODEL_RESEARCH")
        system_prompt = config.get("system_prompt", "")

        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}\n\n{DEBATE_SYSTEM_PROMPT}",
            },
            {
                "role": "user",
                "content": (
                    f"项目目标：{goal}\n\n"
                    f"## 所有团队成员的初步结果\n\n{presentations_text}"
                    f"{history_text}\n\n"
                    f"你是 {aid}（{config.get('role', '')}）。"
                    f"请对其他团队成员的观点发表你的意见。"
                ),
            },
        ]

        result = await call_llm(
            model_env_key=model_key,
            messages=messages,
            temperature=0.6,
            max_tokens=1000,
        )

        tokens = result["usage"].get("total_tokens", 0)

        # 解析回应
        try:
            # 尝试提取 JSON 数组
            content = result["content"].strip()
            # 处理 markdown 包裹
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()
            # 尝试找数组
            arr_start = content.find("[")
            arr_end = content.rfind("]")
            if arr_start != -1 and arr_end != -1:
                responses = json.loads(content[arr_start : arr_end + 1])
            else:
                responses = json.loads(content)

            for resp in responses:
                if resp.get("to") == aid:
                    continue  # 不回应自己
                bus.publish(BusMessage(
                    from_agent=aid,
                    to_agent=resp.get("to", "broadcast"),
                    type=resp.get("type", "supplement"),
                    content=resp.get("content", ""),
                    references=resp.get("references", []),
                    confidence=config.get("confidence", 0.7),
                ))
        except (json.JSONDecodeError, TypeError, KeyError):
            # LLM 输出格式异常时，作为一条 broadcast 发布
            bus.publish(BusMessage(
                from_agent=aid,
                to_agent="broadcast",
                type="supplement",
                content=result["content"][:500],
            ))

        return tokens

    token_results = await asyncio.gather(
        *[_agent_debate(c) for c in agent_configs]
    )
    total_tokens = sum(token_results)
    return total_tokens


# ── Phase C：修正更新 ──────────────────────────────────────

REVISION_PROMPT = """基于刚才的圆桌辩论，你收到了以下来自同事的反馈。
请修正你的初步结论。

## 输出格式（JSON）
{
  "conclusion": "可行 / 不可行 / 有条件可行",
  "confidence": 0.xx,
  "key_reasons": ["理由1", "理由2", "理由3"],
  "conditions": ["前提条件1（如有）"],
  "risks": ["风险1", "风险2"],
  "revised_analysis": "修正后的完整分析（200-400字）"
}

只输出 JSON。"""


async def phase_c_revise(
    agent_configs: list[dict],
    agent_results: dict[str, dict],
    bus: MessageBus,
    goal: str,
) -> tuple[dict[str, dict], int]:
    """
    每个 Agent 基于辩论反馈修正结论。
    返回 (修正后的结构化结论 dict, token 消耗)。
    """
    structured_conclusions: dict[str, dict] = {}
    total_tokens = 0

    async def _revise_one(config: dict) -> int:
        aid = config["agent_id"]
        model_key = config.get("model_env_key", "MODEL_RESEARCH")
        system_prompt = config.get("system_prompt", "")
        preliminary = agent_results.get(aid, {}).get("preliminary_result", "")

        # 收集发给该 Agent 的辩论消息
        feedback_msgs = bus.get_messages_for(aid)
        feedback_text = "\n".join(
            f"[{m.from_agent}] ({m.type}): {m.content}"
            for m in feedback_msgs
            if m.type != "preliminary_result" and m.from_agent != aid
        )
        if not feedback_text:
            feedback_text = "（本轮未收到针对性反馈）"

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"项目目标：{goal}\n\n"
                    f"## 你的初步结论\n{preliminary[:1000]}\n\n"
                    f"## 来自同事的辩论反馈\n{feedback_text}\n\n"
                    f"{REVISION_PROMPT}"
                ),
            },
        ]

        result = await call_llm(
            model_env_key=model_key,
            messages=messages,
            temperature=0.4,
            max_tokens=1000,
        )

        tokens = result["usage"].get("total_tokens", 0)

        try:
            conclusion = _extract_json(result["content"])
        except (ValueError, json.JSONDecodeError):
            conclusion = {
                "conclusion": "有条件可行",
                "confidence": 0.5,
                "key_reasons": ["结论提取失败"],
                "conditions": [],
                "risks": [],
                "revised_analysis": result["content"][:500],
            }

        structured_conclusions[aid] = conclusion

        # 将修正结果发布到总线
        bus.publish(BusMessage(
            from_agent=aid,
            to_agent="broadcast",
            type="revision",
            content=json.dumps(conclusion, ensure_ascii=False),
            confidence=conclusion.get("confidence", 0.5),
        ))

        return tokens

    token_results = await asyncio.gather(
        *[_revise_one(c) for c in agent_configs]
    )
    total_tokens = sum(token_results)
    return structured_conclusions, total_tokens


# ── Phase D：共识检测（裁判 LLM） ─────────────────────────

JUDGE_SYSTEM_PROMPT = """你是一个独立的裁判 LLM，不参与辩论，只负责客观评估共识状态。

## 你的任务

阅读多个专家 Agent 的结构化结论，判断他们是否达成共识。

## 关键区分

你必须区分"讨论同一话题"和"得出相同结论"：
- 所有 Agent 都在讨论"小红书AI搜索" ≠ 共识（只是同一话题）
- 所有 Agent 都认为"有条件可行" = 共识（结论一致）
- 3个说"可行"、2个说"不可行" = 无共识（结论分歧）

## 输出格式（JSON）

{
  "consensus_reached": true/false,
  "consensus_type": "full / partial / none",
  "core_position": "对核心立场的总结（一句话）",
  "agreement_points": ["各方都同意的要点"],
  "disagreement_points": ["各方仍有分歧的要点"],
  "capability_gap_detected": true/false,
  "gaps": ["未被任何 Agent 覆盖的分析维度（如有）"],
  "marginal_value_of_next_round": "high / medium / low",
  "recommendation": "continue_debate / evolve_team / synthesize",
  "contribution_scores": {
    "agent_id": {
      "score": 0.xx,
      "referenced_by_count": 0,
      "unique_information": true/false,
      "conclusion_influence": "该 Agent 的观点是否导致其他 Agent 修正结论"
    }
  }
}

## 判断标准

- full consensus：所有 Agent 的核心结论方向一致（全"可行"或全"不可行"）
- partial consensus：多数 Agent 结论一致但有少数分歧，或结论一致但条件/风险不同
- none：核心立场存在根本性分歧

只输出 JSON。"""


async def phase_d_judge(
    structured_conclusions: dict[str, dict],
    bus: MessageBus,
    agent_configs: list[dict],
) -> tuple[dict, int]:
    """
    裁判 LLM 评估共识状态。使用 MODEL_JUDGE（独立第三方模型）。
    返回 (consensus_report, token 消耗)。
    """
    # 组装所有 Agent 的结构化结论
    conclusions_text = ""
    for config in agent_configs:
        aid = config["agent_id"]
        role = config.get("role", "未知")
        conclusion = structured_conclusions.get(aid, {})
        conclusions_text += (
            f"\n[{aid}]（{role}）：\n"
            f"{json.dumps(conclusion, ensure_ascii=False, indent=2)}\n"
        )

    # 引用统计（用于 contribution_scores）
    reference_counts = {}
    for config in agent_configs:
        aid = config["agent_id"]
        reference_counts[aid] = bus.count_references_to(aid)

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"## 各 Agent 的结构化结论\n{conclusions_text}\n\n"
                f"## 引用统计（其他 Agent 引用该 Agent 的次数）\n"
                f"{json.dumps(reference_counts, ensure_ascii=False)}\n\n"
                f"请评估共识状态。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_JUDGE",
        messages=messages,
        temperature=0.3,
        max_tokens=2000,
    )

    tokens = result["usage"].get("total_tokens", 0)

    try:
        consensus = _extract_json(result["content"])
    except (ValueError, json.JSONDecodeError):
        consensus = {
            "consensus_reached": False,
            "consensus_type": "none",
            "recommendation": "synthesize",
            "capability_gap_detected": False,
            "gaps": [],
        }

    return consensus, tokens


# ── Phase E：辩论历史摘要压缩 ──────────────────────────────

COMPRESS_PROMPT = """你是一个辩论摘要压缩器。将一轮辩论的完整记录压缩为结构化摘要。

## 输出格式（JSON）

{
  "round": 1,
  "agent_summaries": {
    "agent_id": "该 Agent 的核心论点（不超过100字）"
  },
  "key_disagreements": ["主要分歧点1", "主要分歧点2"],
  "agreements_reached": ["已达成的共识点1"],
  "open_questions": ["尚未解决的问题"],
  "token_count_before": 0,
  "token_count_after": 0
}

只输出 JSON。"""


async def phase_e_compress(
    bus: MessageBus,
    debate_round: int,
) -> tuple[dict, int]:
    """
    用轻量模型将本轮完整辩论记录压缩为结构化摘要。
    返回 (摘要 dict, token 消耗)。
    """
    all_messages = bus.to_dict_list()
    # 过滤本轮辩论消息（排除 preliminary_result）
    debate_msgs = [
        m for m in all_messages if m.get("type") != "preliminary_result"
    ]

    full_text = json.dumps(debate_msgs, ensure_ascii=False)
    original_char_count = len(full_text)

    messages = [
        {"role": "system", "content": COMPRESS_PROMPT},
        {
            "role": "user",
            "content": (
                f"第 {debate_round} 轮辩论完整记录：\n\n"
                f"{full_text[:8000]}\n\n"  # 截断防止过长
                f"请压缩为结构化摘要。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_COMPRESS",
        messages=messages,
        temperature=0.2,
        max_tokens=1500,
    )

    tokens = result["usage"].get("total_tokens", 0)

    try:
        summary = _extract_json(result["content"])
    except (ValueError, json.JSONDecodeError):
        summary = {
            "round": debate_round,
            "agent_summaries": {},
            "key_disagreements": [],
            "agreements_reached": [],
            "open_questions": [],
        }

    summary["round"] = debate_round
    summary["token_count_before"] = original_char_count
    summary["token_count_after"] = len(json.dumps(summary, ensure_ascii=False))

    return summary, tokens


# ── Council 主入口 ─────────────────────────────────────────

async def council_engine(state: HiveState) -> dict:
    """
    L4 Council 引擎：执行一轮完整辩论（Phase A → E）。

    返回更新后的 state 字段，包含辩论结果和路由决策。
    路由决策放在 consensus_report["recommendation"] 中，
    由 LangGraph 的 Command 路由读取。
    """
    agent_configs = state["agent_configs"]
    agent_results = state["agent_results"]
    goal = state["goal"]
    debate_round = state.get("debate_round", 0) + 1
    debate_history = list(state.get("debate_history", []))
    debate_history_full = list(state.get("debate_history_full", []))
    total_tokens = 0

    bus = MessageBus()

    # ── Phase A：独立呈述 ──
    await phase_a_present(agent_configs, agent_results, bus)

    # ── Phase B：圆桌辩论 ──
    debate_tokens = await phase_b_debate(
        agent_configs, agent_results, bus, debate_history, goal
    )
    total_tokens += debate_tokens

    # ── Phase C：修正更新 ──
    structured_conclusions, revise_tokens = await phase_c_revise(
        agent_configs, agent_results, bus, goal
    )
    total_tokens += revise_tokens

    # ── Phase D：共识检测 ──
    consensus, judge_tokens = await phase_d_judge(
        structured_conclusions, bus, agent_configs
    )
    total_tokens += judge_tokens

    # ── Phase E：辩论历史压缩 ──
    full_round_record = bus.to_dict_list()
    summary, compress_tokens = await phase_e_compress(bus, debate_round)
    total_tokens += compress_tokens

    # 存储辩论记录
    debate_history.append(summary)
    debate_history_full.append(full_round_record)

    # 计算压缩率
    compression_ratio = 0.0
    if summary.get("token_count_before", 0) > 0:
        compression_ratio = 1.0 - (
            summary["token_count_after"] / summary["token_count_before"]
        )

    # 组装返回值
    return {
        "debate_round": debate_round,
        "debate_history": debate_history,
        "debate_history_full": debate_history_full,
        "consensus_report": consensus,
        "structured_conclusions": structured_conclusions,
        "token_used": state.get("token_used", 0) + total_tokens,
        "_council_meta": {
            "debate_tokens": debate_tokens,
            "revise_tokens": revise_tokens,
            "judge_tokens": judge_tokens,
            "compress_tokens": compress_tokens,
            "total_messages": len(full_round_record),
            "compression_ratio": round(compression_ratio, 2),
        },
    }
