"""Synthesizer — 共识整合与最终报告生成

在辩论达成共识（或强制共识）后，整合所有 Agent 的观点，
生成包含完整决策路径的最终报告。
"""

import json

from backend.core.llm_service import call_llm
from backend.core.state import HiveState
from backend.core.utils import extract_json_safe as _extract_json


SYNTHESIZER_PROMPT = """你是 Genesis Hive 的最终报告整合器（Synthesizer）。

基于多个专家 Agent 的辩论结果，生成一份完整的决策报告。

## 输出格式（JSON）

{
  "title": "报告标题",
  "executive_summary": "执行摘要（200-300字）",
  "conclusion": "可行 / 不可行 / 有条件可行",
  "confidence": 0.xx,
  "key_findings": [
    {"topic": "发现主题", "content": "发现内容", "source_agents": ["agent_id"]}
  ],
  "consensus_points": ["共识要点1", "共识要点2"],
  "disagreement_points": ["分歧要点1（含各方观点）"],
  "risks": [
    {"risk": "风险描述", "severity": "high/medium/low", "mitigation": "缓解措施"}
  ],
  "recommendations": ["建议1", "建议2"],
  "decision_path": "决策路径描述：从最初分析到最终结论的推理链",
  "team_evolution": "团队进化记录：哪些 Agent 加入/退出，为什么",
  "token_cost": {"total": 0, "breakdown": {}}
}

只输出 JSON。"""


async def synthesizer_engine(state: HiveState) -> dict:
    """整合所有辩论结果，生成最终报告"""
    goal = state.get("goal", "")
    consensus = state.get("consensus_report", {})
    conclusions = state.get("structured_conclusions", {})
    evolution_log = state.get("evolution_log", [])
    forced = state.get("forced_consensus", False)
    uncovered = state.get("uncovered_gaps", [])
    debate_round = state.get("debate_round", 0)
    token_used = state.get("token_used", 0)

    # 整理各 Agent 的结论摘要
    conclusions_text = ""
    for aid, c in conclusions.items():
        conclusions_text += f"\n[{aid}]：{json.dumps(c, ensure_ascii=False)}\n"

    # 整理进化日志
    evo_text = ""
    if evolution_log:
        evo_text = "\n进化日志：\n" + json.dumps(evolution_log, ensure_ascii=False, indent=2)

    forced_note = ""
    if forced:
        forced_note = "\n注意：本次为强制共识（辩论轮次或 token 预算达上限），报告中需标注分歧。"
    if uncovered:
        forced_note += f"\n未覆盖的分析维度：{uncovered}"

    messages = [
        {"role": "system", "content": SYNTHESIZER_PROMPT},
        {
            "role": "user",
            "content": (
                f"项目目标：{goal}\n\n"
                f"辩论轮次：{debate_round}\n"
                f"共识评估：{json.dumps(consensus, ensure_ascii=False)}\n\n"
                f"各 Agent 最终结论：\n{conclusions_text}\n"
                f"{evo_text}"
                f"{forced_note}\n\n"
                f"已消耗 Token：{token_used}\n\n"
                f"请生成最终报告。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_META",
        messages=messages,
        temperature=0.4,
        max_tokens=3000,
    )

    tokens = result["usage"].get("total_tokens", 0)
    report = _extract_json(result["content"])

    if not report:
        report = {
            "title": f"分析报告：{goal}",
            "executive_summary": result["content"][:500],
            "conclusion": "有条件可行",
            "confidence": 0.7,
        }

    # 补充元信息
    report["token_cost"] = {
        "total": token_used + tokens,
        "synthesizer": tokens,
    }
    report["debate_rounds"] = debate_round
    report["evolution_cycles"] = state.get("evolution_cycle", 0)
    report["forced_consensus"] = forced
    if uncovered:
        report["uncovered_gaps"] = uncovered

    return {
        "final_report": report,
        "token_used": token_used + tokens,
    }
