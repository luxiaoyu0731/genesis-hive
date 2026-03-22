"""LangGraph 编排测试 — 三条路径验证

路径 1：Decomposer → Spawner → Executor → Council（共识达成）→ Synthesizer
路径 2：Council → Evolver → Spawner → Executor → Council → Synthesizer
路径 3：3轮辩论未共识 → forced_consensus → Synthesizer
"""

import asyncio
import json
import time

from backend.graph import build_hive_graph, create_initial_state
from backend.engines.council import council_engine as _council_inner
from backend.engines.evolver import evolver_engine as _evolver_inner


# ══════════════════════════════════════════════════════════════
# 路径 1：Happy Path — 1 轮共识直达 Synthesizer
# ══════════════════════════════════════════════════════════════

async def test_path_1_happy():
    print("=" * 70)
    print("路径 1：Happy Path — 共识达成 → Synthesizer")
    print("=" * 70)

    graph = build_hive_graph()
    state = create_initial_state(
        goal="分析小红书做AI搜索的可行性",
        mode="standard",
    )

    t0 = time.monotonic()

    # 收集经过的节点
    visited = []
    async for event in graph.astream(state, stream_mode="updates"):
        for node_name, update in event.items():
            visited.append(node_name)
            token = update.get("token_used", "?")
            print(f"  [{node_name}] token_used={token}")

            # 提取最终 state
            if node_name == "synthesizer":
                final_state = update

    elapsed = time.monotonic() - t0
    print(f"\n  路径：{' → '.join(visited)}")
    print(f"  耗时：{elapsed:.1f}s")

    # 验证
    has_synth = "synthesizer" in visited
    report = final_state.get("final_report", {}) if final_state else {}
    has_report = bool(report.get("conclusion") or report.get("executive_summary"))

    print(f"\n  [到达 synthesizer]：{'✅' if has_synth else '❌'}")
    print(f"  [最终报告存在]：{'✅' if has_report else '❌'}")
    if report:
        print(f"  [报告结论]：{report.get('conclusion', 'N/A')}")
        print(f"  [报告置信度]：{report.get('confidence', 'N/A')}")

    return visited, report


# ══════════════════════════════════════════════════════════════
# 路径 2：Evolution — Council → Evolver → Spawner → Executor → Council → Synthesizer
# ══════════════════════════════════════════════════════════════

async def test_path_2_evolution():
    """
    用 mock 的 council_node 强制触发进化分支，
    以验证 Evolver → Spawner → Executor → Council 回路。
    """
    print(f"\n{'=' * 70}")
    print("路径 2：Evolution — 进化重组分支")
    print("=" * 70)

    from backend.graph import council_node, evolver_node
    from langgraph.graph import StateGraph
    from langgraph.types import Command
    from backend.core.state import HiveState
    from backend.engines.decomposer import decomposer_engine
    from backend.engines.spawner import spawner_engine
    from backend.engines.executor import executor_engine
    from backend.engines.synthesizer import synthesizer_engine

    call_count = {"council": 0}

    async def council_node_mock(state: HiveState):
        """第 1 次返回 evolver，第 2 次返回 synthesizer"""
        call_count["council"] += 1

        # 先运行真实辩论
        result = await _council_inner(state)
        base_update = {
            "debate_round": result.get("debate_round", 1),
            "debate_history": result.get("debate_history", []),
            "debate_history_full": result.get("debate_history_full", []),
            "consensus_report": result.get("consensus_report", {}),
            "structured_conclusions": result.get("structured_conclusions", {}),
            "token_used": result.get("token_used", 0),
        }

        if call_count["council"] == 1:
            # 第 1 次：强制走 evolver
            print(f"    Council #{call_count['council']}: → evolver（注入能力缺口）")
            return Command(goto="evolver", update={
                **base_update,
                "gaps": ["数据隐私与用户合规分析"],
            })
        else:
            # 第 2 次：走 synthesizer
            print(f"    Council #{call_count['council']}: → synthesizer（共识达成）")
            return Command(goto="synthesizer", update=base_update)

    # 构建带 mock council 的图
    graph = StateGraph(HiveState)
    graph.add_node("decomposer", decomposer_engine)
    graph.add_node("spawner", spawner_engine)
    graph.add_node("executor", executor_engine)
    graph.add_node("council", council_node_mock)
    graph.add_node("evolver", evolver_node)
    graph.add_node("synthesizer", synthesizer_engine)

    graph.add_edge("decomposer", "spawner")
    graph.add_edge("spawner", "executor")
    graph.add_edge("executor", "council")
    graph.set_entry_point("decomposer")
    graph.set_finish_point("synthesizer")

    compiled = graph.compile()
    state = create_initial_state(goal="分析小红书做AI搜索的可行性", mode="standard")

    t0 = time.monotonic()
    visited = []
    final_state = {}

    async for event in compiled.astream(state, stream_mode="updates"):
        for node_name, update in event.items():
            visited.append(node_name)
            token = update.get("token_used", "?")
            evo = update.get("evolution_cycle", "")
            extra = f", evolution_cycle={evo}" if evo != "" else ""
            print(f"  [{node_name}] token_used={token}{extra}")

            if node_name == "synthesizer":
                final_state = update

    elapsed = time.monotonic() - t0
    print(f"\n  路径：{' → '.join(visited)}")
    print(f"  耗时：{elapsed:.1f}s")

    # 验证
    has_evolver = "evolver" in visited
    # spawner 应该出现 2 次（初始 + 进化后）
    spawner_count = visited.count("spawner")
    executor_count = visited.count("executor")
    council_count = visited.count("council")

    print(f"\n  [经过 evolver]：{'✅' if has_evolver else '❌'}")
    print(f"  [spawner 调用次数]：{spawner_count}（期望 2）{'✅' if spawner_count == 2 else '❌'}")
    print(f"  [executor 调用次数]：{executor_count}（期望 2）{'✅' if executor_count == 2 else '❌'}")
    print(f"  [council 调用次数]：{council_count}（期望 2）{'✅' if council_count == 2 else '❌'}")

    report = final_state.get("final_report", {})
    if report:
        print(f"  [报告结论]：{report.get('conclusion', 'N/A')}")
        print(f"  [进化轮次]：{report.get('evolution_cycles', 0)}")

    return visited


# ══════════════════════════════════════════════════════════════
# 路径 3：Forced Consensus — 3 轮辩论未共识
# ══════════════════════════════════════════════════════════════

async def test_path_3_forced():
    """
    用 mock 的 council_node 模拟 3 轮辩论均未达成共识，
    验证第 3 轮后 forced_consensus → synthesizer。
    """
    print(f"\n{'=' * 70}")
    print("路径 3：Forced Consensus — 3 轮辩论未共识")
    print("=" * 70)

    from langgraph.graph import StateGraph
    from langgraph.types import Command
    from backend.core.state import HiveState
    from backend.engines.decomposer import decomposer_engine
    from backend.engines.spawner import spawner_engine
    from backend.engines.executor import executor_engine
    from backend.engines.synthesizer import synthesizer_engine

    call_count = {"council": 0}

    async def council_node_no_consensus(state: HiveState):
        """每次都返回未共识，让辩论循环到第 3 轮"""
        call_count["council"] += 1

        # 运行真实辩论
        result = await _council_inner(state)
        debate_round = result.get("debate_round", call_count["council"])

        base_update = {
            "debate_round": debate_round,
            "debate_history": result.get("debate_history", []),
            "debate_history_full": result.get("debate_history_full", []),
            "consensus_report": result.get("consensus_report", {}),
            "structured_conclusions": result.get("structured_conclusions", {}),
            "token_used": result.get("token_used", 0),
        }

        if debate_round >= 3:
            print(f"    Council #{call_count['council']} (round={debate_round}): → synthesizer（强制共识）")
            return Command(goto="synthesizer", update={
                **base_update,
                "forced_consensus": True,
            })
        else:
            print(f"    Council #{call_count['council']} (round={debate_round}): → council（继续辩论）")
            return Command(goto="council", update=base_update)

    # 构建图
    graph = StateGraph(HiveState)
    graph.add_node("decomposer", decomposer_engine)
    graph.add_node("spawner", spawner_engine)
    graph.add_node("executor", executor_engine)
    graph.add_node("council", council_node_no_consensus)
    graph.add_node("synthesizer", synthesizer_engine)

    graph.add_edge("decomposer", "spawner")
    graph.add_edge("spawner", "executor")
    graph.add_edge("executor", "council")
    graph.set_entry_point("decomposer")
    graph.set_finish_point("synthesizer")

    compiled = graph.compile()
    state = create_initial_state(goal="分析小红书做AI搜索的可行性", mode="standard")

    t0 = time.monotonic()
    visited = []
    final_state = {}

    async for event in compiled.astream(state, stream_mode="updates"):
        for node_name, update in event.items():
            visited.append(node_name)
            dr = update.get("debate_round", "")
            fc = update.get("forced_consensus", "")
            extra = ""
            if dr != "":
                extra += f", round={dr}"
            if fc:
                extra += f", forced={fc}"
            print(f"  [{node_name}] token_used={update.get('token_used', '?')}{extra}")

            if node_name == "synthesizer":
                final_state = update

    elapsed = time.monotonic() - t0
    print(f"\n  路径：{' → '.join(visited)}")
    print(f"  耗时：{elapsed:.1f}s")

    council_count = visited.count("council")
    has_forced = final_state.get("forced_consensus", False) if final_state else False
    report = final_state.get("final_report", {}) if final_state else {}

    print(f"\n  [council 调用次数]：{council_count}（期望 3）{'✅' if council_count == 3 else '❌'}")
    print(f"  [forced_consensus]：{has_forced} {'✅' if has_forced else '❌'}")
    if report:
        print(f"  [报告结论]：{report.get('conclusion', 'N/A')}")
        print(f"  [报告标注强制共识]：{report.get('forced_consensus', False)}")

    return visited


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

async def main():
    # 路径 1
    visited1, report1 = await test_path_1_happy()

    # 路径 2
    visited2 = await test_path_2_evolution()

    # 路径 3
    visited3 = await test_path_3_forced()

    # 总结
    print(f"\n{'═' * 70}")
    print("三条路径验证总结")
    print(f"{'═' * 70}")
    print(f"  路径 1 (Happy)：    {' → '.join(visited1)}")
    print(f"  路径 2 (Evolution)：{' → '.join(visited2)}")
    print(f"  路径 3 (Forced)：   {' → '.join(visited3)}")

    p1_ok = "synthesizer" in visited1 and "evolver" not in visited1
    p2_ok = "evolver" in visited2 and visited2.count("spawner") >= 2
    p3_ok = visited3.count("council") >= 3

    print(f"\n  路径 1 正确（直达 synthesizer）：{'✅' if p1_ok else '❌'}")
    print(f"  路径 2 正确（经过 evolver 回路）：{'✅' if p2_ok else '❌'}")
    print(f"  路径 3 正确（3 轮后强制共识）：{'✅' if p3_ok else '❌'}")

    # ASCII 图可视化
    print(f"\n{'═' * 70}")
    print("LangGraph ASCII 可视化")
    print(f"{'═' * 70}")
    graph = build_hive_graph()
    try:
        print(graph.get_graph().draw_ascii())
    except Exception as e:
        # 如果 draw_ascii 不可用，手动画
        print(f"  (draw_ascii 不可用: {e})")
        print_manual_ascii()


def print_manual_ascii():
    print("""
         ┌──────────────┐
         │  __start__   │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  decomposer  │ L1 任务分解
         └──────┬───────┘
                │
                ▼
    ┌──→ ┌──────────────┐
    │    │   spawner     │ L2 Agent 生成
    │    └──────┬───────┘
    │           │
    │           ▼
    │    ┌──────────────┐
    │    │   executor    │ L3 并行执行
    │    └──────┬───────┘
    │           │
    │           ▼
    │    ┌──────────────┐ ──── Command ────→ ┌──────────────┐
    │    │   council     │ (共识达成)         │ synthesizer  │ → __end__
    │    └──────┬───────┘ ──── Command ────→ └──────────────┘
    │           │ (能力缺口)      (强制共识/辩论≥3轮)
    │           │
    │           │ Command       ┌─────────┐
    │           └──────────────→│ council  │ (继续辩论，自环)
    │           │               └─────────┘
    │           ▼
    │    ┌──────────────┐
    │    │   evolver     │ L5 动态重组
    │    └──────┬───────┘
    │           │ Command(goto="spawner")
    └───────────┘
    """)


if __name__ == "__main__":
    asyncio.run(main())
