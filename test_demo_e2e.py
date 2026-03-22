"""Demo 模式端到端测试

输入："分析小红书做AI搜索的可行性"
验证完整流程：分解 → 生成 → 执行 → 辩论 → 共识 → 报告
记录总耗时和总 token 消耗
"""

import asyncio
import json
import time
import sys

from backend.graph import build_hive_graph, create_initial_state


DIVIDER = "=" * 70


async def main():
    goal = "分析小红书做AI搜索的可行性"
    mode = "demo"

    print(f"\n{DIVIDER}")
    print(f"  Genesis Hive — Demo 模式端到端测试")
    print(f"  目标：{goal}")
    print(f"  模式：{mode}（3 Agent / 1 轮辩论 / 30k token 预算）")
    print(f"{DIVIDER}\n")

    # ── 初始化 ──
    state = create_initial_state(goal, mode=mode)
    graph = build_hive_graph()

    start_time = time.time()

    # ── 执行完整流程 ──
    print("🚀 开始执行完整流程...\n")

    result = await graph.ainvoke(state)

    elapsed = time.time() - start_time

    # ── 输出结果 ──
    print(f"\n{DIVIDER}")
    print("  ✅ 流程执行完毕")
    print(f"{DIVIDER}\n")

    # 1. 分解结果
    task_graph = result.get("task_graph", {})
    print("📋 【L1 Decomposer — 任务分解】")
    subtasks = task_graph.get("subtasks", [])
    print(f"   目标领域：{task_graph.get('domain', 'N/A')}")
    print(f"   复杂度：{task_graph.get('complexity', 'N/A')}")
    print(f"   需要魔鬼代言人：{task_graph.get('required_adversary', 'N/A')}")
    print(f"   子任务数量：{len(subtasks)}")
    for i, st in enumerate(subtasks, 1):
        print(f"   {i}. [{st.get('id')}] {st.get('name')} ({st.get('capability')}) — 优先级 {st.get('priority')}")
    print()

    # 2. Agent 配置
    configs = result.get("agent_configs", [])
    print("🧬 【L2 Spawner — Agent 生成】")
    print(f"   生成 Agent 数量：{len(configs)}")
    for c in configs:
        print(f"   • {c.get('agent_id')} — {c.get('role', 'N/A')}")
        print(f"     模型：{c.get('model_env_key')}, 框架：{c.get('framework')}")
    print()

    # 3. 执行结果
    agent_results = result.get("agent_results", {})
    print("⚡ 【L3 Executor — 并行执行】")
    print(f"   执行 Agent 数量：{len(agent_results)}")
    for aid, ar in agent_results.items():
        conf = ar.get("confidence", 0)
        time_ms = ar.get("time_ms", 0)
        tokens = ar.get("tokens_used", 0)
        print(f"   • {aid}: 置信度={conf:.2f}, 耗时={time_ms}ms, tokens={tokens}")
        # 输出初步结论的前 100 字
        pr = ar.get("preliminary_result", "")
        if pr:
            preview = pr[:150].replace("\n", " ")
            print(f"     结论预览：{preview}...")
    print()

    # 4. 辩论与共识
    consensus = result.get("consensus_report", {})
    debate_round = result.get("debate_round", 0)
    print("🏛️  【L4 Council — 圆桌辩论】")
    print(f"   辩论轮次：{debate_round}")
    print(f"   共识达成：{consensus.get('consensus_reached', 'N/A')}")
    print(f"   共识类型：{consensus.get('consensus_type', 'N/A')}")
    print(f"   核心立场：{consensus.get('core_position', 'N/A')}")
    print(f"   下轮边际价值：{consensus.get('marginal_value_of_next_round', 'N/A')}")
    print(f"   推荐行动：{consensus.get('recommendation', 'N/A')}")
    agree = consensus.get("agreement_points", [])
    disagree = consensus.get("disagreement_points", [])
    if agree:
        print(f"   共识点：")
        for a in agree[:3]:
            print(f"     ✓ {a}")
    if disagree:
        print(f"   分歧点：")
        for d in disagree[:3]:
            print(f"     ✗ {d}")

    # 贡献评分
    scores = consensus.get("contribution_scores", {})
    if scores:
        print(f"   Agent 贡献评分：")
        for aid, s in scores.items():
            if isinstance(s, dict):
                print(f"     • {aid}: score={s.get('score', 'N/A')}, 引用={s.get('referenced_by_count', 'N/A')}")
            else:
                print(f"     • {aid}: score={s}")
    print()

    # 4.5 辩论压缩
    debate_history = result.get("debate_history", [])
    if debate_history:
        latest = debate_history[-1]
        before = latest.get("token_count_before", 0)
        after = latest.get("token_count_after", 0)
        ratio = (1 - after / before) * 100 if before > 0 else 0
        print(f"📦 【辩论压缩】")
        print(f"   压缩前：{before} chars → 压缩后：{after} chars")
        print(f"   压缩率：{ratio:.1f}%")
        print()

    # 5. 进化日志
    evo_log = result.get("evolution_log", [])
    print("🔄 【L5 Evolver — 团队进化】")
    if evo_log:
        for entry in evo_log:
            print(f"   轮次 {entry.get('cycle')}：{entry.get('action')}")
            print(f"   新增：{entry.get('added', [])}, 退场：{entry.get('removed', [])}")
    else:
        print(f"   Demo 模式 1 轮辩论，未触发进化")
    print()

    # 6. 最终报告
    report = result.get("final_report", {})
    print("📊 【最终报告 — Synthesizer】")
    print(f"   标题：{report.get('title', 'N/A')}")
    print(f"   结论：{report.get('conclusion', 'N/A')}")
    print(f"   置信度：{report.get('confidence', 'N/A')}")
    summary = report.get("executive_summary", "")
    if summary:
        print(f"   执行摘要：")
        # 每 60 字换行
        for i in range(0, len(summary), 60):
            print(f"     {summary[i:i+60]}")
    findings = report.get("key_findings", [])
    if findings:
        print(f"   核心发现：")
        for f in findings[:5]:
            if isinstance(f, dict):
                print(f"     • [{f.get('topic')}] {f.get('content', '')[:80]}")
            else:
                print(f"     • {str(f)[:80]}")
    risks = report.get("risks", [])
    if risks:
        print(f"   风险评估：")
        for r in risks[:3]:
            if isinstance(r, dict):
                print(f"     ⚠ [{r.get('severity', 'N/A')}] {r.get('risk', '')[:80]}")
            else:
                print(f"     ⚠ {str(r)[:80]}")
    recs = report.get("recommendations", [])
    if recs:
        print(f"   建议：")
        for r in recs[:3]:
            print(f"     → {str(r)[:80]}")
    print()

    # ── 总结统计 ──
    total_tokens = result.get("token_used", 0)
    forced = result.get("forced_consensus", False)
    print(f"{DIVIDER}")
    print(f"  📈 统计汇总")
    print(f"{DIVIDER}")
    print(f"  总耗时：{elapsed:.1f} 秒")
    print(f"  总 Token 消耗：{total_tokens:,}")
    print(f"  辩论轮次：{debate_round}")
    print(f"  进化次数：{result.get('evolution_cycle', 0)}")
    print(f"  Agent 数量：{len(configs)}")
    print(f"  强制共识：{forced}")
    print(f"  Token 预算利用率：{total_tokens / state['token_budget'] * 100:.1f}%")
    print()

    # ── 2 分钟验证 ──
    if elapsed <= 120:
        print(f"  ✅ 耗时 {elapsed:.1f}s < 120s，Demo 模式时间达标！")
    else:
        print(f"  ⚠️  耗时 {elapsed:.1f}s > 120s，Demo 模式超时！")
    print()

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
