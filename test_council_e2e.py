"""Council 端到端测试：Decomposer → Spawner → Executor → Council"""

import asyncio
import json

from backend.engines.decomposer import decomposer_engine
from backend.engines.spawner import spawner_engine
from backend.engines.executor import executor_engine
from backend.engines.council import council_engine
from backend.core.state import HiveState


async def main():
    state: HiveState = {
        "goal": "分析小红书做AI搜索的可行性",
        "task_graph": {},
        "agent_configs": [],
        "agent_configs_hash": {},
        "agent_results": {},
        "debate_history": [],
        "debate_history_full": [],
        "debate_round": 0,
        "evolution_cycle": 0,
        "consensus_report": {},
        "evolution_log": [],
        "final_report": {},
        "token_budget": 50000,
        "token_used": 0,
        "forced_consensus": False,
        "uncovered_gaps": [],
    }

    # L1 Decomposer
    print("=" * 70)
    print("L1 Decomposer...")
    r = await decomposer_engine(state)
    state = {**state, **r}
    subtasks = state["task_graph"]["subtasks"]
    print(f"  → {len(subtasks)} 个子任务 | Token: {state['token_used']}")

    # L2 Spawner
    print("L2 Spawner...")
    r = await spawner_engine(state)
    state = {**state, **r}
    configs = state["agent_configs"]
    print(f"  → {len(configs)} 个 Agent | Token: {state['token_used']}")

    # L3 Executor
    print("L3 Executor...")
    r = await executor_engine(state)
    state = {**state, **r}
    print(f"  → 执行完成 | Token: {state['token_used']}")

    # L4 Council
    print("\n" + "=" * 70)
    print("L4 Council — 圆桌辩论")
    print("=" * 70)
    r = await council_engine(state)
    state = {**state, **r}

    # ── 打印辩论结果 ──
    meta = r.get("_council_meta", {})
    print(f"\n辩论统计：")
    print(f"  辩论消息数：{meta.get('total_messages', 0)}")
    print(f"  辩论 Token：{meta.get('debate_tokens', 0)}")
    print(f"  修正 Token：{meta.get('revise_tokens', 0)}")
    print(f"  裁判 Token：{meta.get('judge_tokens', 0)}")
    print(f"  压缩 Token：{meta.get('compress_tokens', 0)}")
    print(f"  压缩率：{meta.get('compression_ratio', 0):.0%}")
    print(f"  总 Token：{state['token_used']}")

    # ── 各 Agent 修正后的结论 ──
    print(f"\n{'─' * 70}")
    print("各 Agent 修正后的结构化结论：")
    print(f"{'─' * 70}")
    conclusions = r.get("structured_conclusions", {})
    for aid, c in conclusions.items():
        print(f"\n  [{aid}]")
        print(f"    结论：{c.get('conclusion', 'N/A')}")
        print(f"    置信度：{c.get('confidence', 'N/A')}")
        reasons = c.get("key_reasons", [])
        if reasons:
            print(f"    关键理由：{reasons[0]}")
        risks = c.get("risks", [])
        if risks:
            print(f"    主要风险：{risks[0]}")

    # ── 裁判 LLM 共识评估 ──
    print(f"\n{'═' * 70}")
    print("裁判 LLM 共识评估：")
    print(f"{'═' * 70}")
    consensus = state["consensus_report"]
    print(f"  共识达成：{consensus.get('consensus_reached', 'N/A')}")
    print(f"  共识类型：{consensus.get('consensus_type', 'N/A')}")
    print(f"  核心立场：{consensus.get('core_position', 'N/A')}")
    print(f"  继续辩论边际价值：{consensus.get('marginal_value_of_next_round', 'N/A')}")
    print(f"  推荐操作：{consensus.get('recommendation', 'N/A')}")
    print(f"  能力缺口：{consensus.get('capability_gap_detected', False)}")
    if consensus.get("gaps"):
        print(f"  缺口详情：{consensus['gaps']}")

    agree = consensus.get("agreement_points", [])
    disagree = consensus.get("disagreement_points", [])
    print(f"\n  共识要点（{len(agree)} 条）：")
    for a in agree[:3]:
        print(f"    ✓ {a}")
    print(f"\n  分歧要点（{len(disagree)} 条）：")
    for d in disagree[:3]:
        print(f"    ✗ {d}")

    # ── 贡献评分 ──
    scores = consensus.get("contribution_scores", {})
    if scores:
        print(f"\n  Agent 贡献评分：")
        for aid, s in scores.items():
            if isinstance(s, dict):
                print(f"    {aid:35s} → score={s.get('score', 'N/A')}, refs={s.get('referenced_by_count', 0)}, unique_info={s.get('unique_information', 'N/A')}")

    # ── 辩论摘要验证 ──
    print(f"\n{'─' * 70}")
    print("辩论历史摘要压缩验证：")
    print(f"{'─' * 70}")
    summary = state["debate_history"][-1] if state["debate_history"] else {}
    print(f"  摘要轮次：{summary.get('round', 'N/A')}")
    print(f"  压缩前字符数：{summary.get('token_count_before', 0)}")
    print(f"  压缩后字符数：{summary.get('token_count_after', 0)}")
    if summary.get("token_count_before", 0) > 0:
        ratio = 1 - summary["token_count_after"] / summary["token_count_before"]
        print(f"  压缩率：{ratio:.0%}", "✅" if ratio > 0.5 else "⚠️ 压缩率偏低")

    key_dis = summary.get("key_disagreements", [])
    agree_pts = summary.get("agreements_reached", [])
    print(f"  主要分歧：{key_dis[:2]}")
    print(f"  已达共识：{agree_pts[:2]}")

    # ── 完整辩论原文保留验证 ──
    full_count = len(state["debate_history_full"][-1]) if state["debate_history_full"] else 0
    print(f"\n  debate_history_full 原文消息数：{full_count}")
    print(f"  debate_history 摘要条数：{len(state['debate_history'])}")

    # ── 最终验证 ──
    print(f"\n{'═' * 70}")
    print("验证清单：")
    print(f"{'═' * 70}")

    has_consensus_type = consensus.get("consensus_type") in ("full", "partial", "none")
    print(f"  [共识类型] consensus_type ∈ {{full, partial, none}}：{'✅' if has_consensus_type else '❌'}")

    has_recommendation = consensus.get("recommendation") in ("continue_debate", "evolve_team", "synthesize")
    print(f"  [推荐操作] recommendation 有效：{'✅' if has_recommendation else '❌'}")

    # 检查辩论消息包含不同类型标签
    full_msgs = state["debate_history_full"][-1] if state["debate_history_full"] else []
    msg_types = set(m.get("type") for m in full_msgs if m.get("type") != "preliminary_result")
    print(f"  [类型标签] 辩论中出现的类型：{msg_types}")
    has_diverse_types = len(msg_types) >= 2
    print(f"  [类型多样] 至少 2 种类型标签：{'✅' if has_diverse_types else '❌'}")

    # 检查裁判是否输出了 contribution_scores
    has_scores = bool(scores)
    print(f"  [贡献评分] contribution_scores 存在：{'✅' if has_scores else '❌'}")

    # 压缩率
    has_compression = meta.get("compression_ratio", 0) > 0.3
    print(f"  [摘要压缩] 压缩率 > 30%：{'✅' if has_compression else '❌'}")

    # debate_history_full 保留原文
    has_full = len(state["debate_history_full"]) > 0 and len(state["debate_history_full"][-1]) > 0
    print(f"  [原文保留] debate_history_full 非空：{'✅' if has_full else '❌'}")

    print(f"\n  Token 总消耗：{state['token_used']} / {state['token_budget']}")


if __name__ == "__main__":
    asyncio.run(main())
