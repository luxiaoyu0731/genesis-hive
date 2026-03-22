"""Executor 引擎 Mock 并发测试

验证：
1. 无依赖的任务几乎同时开始
2. 有依赖的任务等待前置完成后才开始
3. 增量执行：未变更的 Agent 复用上轮结果
"""

import asyncio
import time

from backend.engines.executor import executor_engine, _hash_config
from backend.core.state import HiveState

# 记录每个 Agent 的开始/结束时间
timeline: dict[str, dict] = {}
T0 = 0.0


async def mock_agent_runner(config: dict, goal: str, token_budget: int) -> dict:
    """Mock Agent 执行器：用 sleep 模拟 LLM 调用延迟"""
    agent_id = config["agent_id"]
    start = time.monotonic() - T0
    timeline[agent_id] = {"start": round(start, 2)}

    # 模拟不同 Agent 的执行时间
    delay = {"A": 0.5, "B": 0.3, "C": 0.4, "D": 0.2, "E": 0.3}.get(agent_id, 0.3)
    await asyncio.sleep(delay)

    end = time.monotonic() - T0
    timeline[agent_id]["end"] = round(end, 2)
    timeline[agent_id]["duration"] = round(end - start, 2)

    return {
        "agent_id": agent_id,
        "actions": [{"type": "mock", "content": f"{agent_id} done"}],
        "preliminary_result": f"Mock result from {agent_id}",
        "confidence": 0.8,
        "tokens_used": 100,
        "time_ms": int(delay * 1000),
    }


async def test_concurrency():
    """测试 1：并发执行 + 依赖等待"""
    global T0, timeline
    timeline = {}

    # 构造任务图谱：
    #   A (无依赖)  B (无依赖)  C (无依赖)
    #         \         |        /
    #          D (依赖 A, B)
    #                 |
    #          E (依赖 D)
    task_graph = {
        "goal": "测试并发",
        "subtasks": [
            {"id": "task_a", "name": "任务A", "capability": "market_research", "dependencies": [], "priority": "high"},
            {"id": "task_b", "name": "任务B", "capability": "technical_analysis", "dependencies": [], "priority": "high"},
            {"id": "task_c", "name": "任务C", "capability": "competitive_intelligence", "dependencies": [], "priority": "medium"},
            {"id": "task_d", "name": "任务D", "capability": "financial_analysis", "dependencies": ["task_a", "task_b"], "priority": "medium"},
            {"id": "task_e", "name": "任务E", "capability": "risk_analysis", "dependencies": ["task_d"], "priority": "low"},
        ],
    }

    agent_configs = [
        {"agent_id": "A", "subtask_id": "task_a", "system_prompt": "a", "model_env_key": "MODEL_RESEARCH", "tools": [], "capability": "market_research"},
        {"agent_id": "B", "subtask_id": "task_b", "system_prompt": "b", "model_env_key": "MODEL_ANALYSIS", "tools": [], "capability": "technical_analysis"},
        {"agent_id": "C", "subtask_id": "task_c", "system_prompt": "c", "model_env_key": "MODEL_RESEARCH", "tools": [], "capability": "competitive_intelligence"},
        {"agent_id": "D", "subtask_id": "task_d", "system_prompt": "d", "model_env_key": "MODEL_ANALYSIS", "tools": [], "capability": "financial_analysis"},
        {"agent_id": "E", "subtask_id": "task_e", "system_prompt": "e", "model_env_key": "MODEL_ANALYSIS", "tools": [], "capability": "risk_analysis"},
    ]

    state: HiveState = {
        "goal": "测试并发",
        "task_graph": task_graph,
        "agent_configs": agent_configs,
        "agent_configs_hash": {},
        "agent_results": {},
        "debate_history": [],
        "debate_history_full": [],
        "debate_round": 0,
        "evolution_cycle": 0,
        "consensus_report": {},
        "evolution_log": [],
        "final_report": {},
        "token_budget": 30000,
        "token_used": 0,
        "forced_consensus": False,
        "uncovered_gaps": [],
    }

    print("=" * 70)
    print("测试 1：并发执行 + 依赖等待")
    print("=" * 70)
    print()
    print("依赖关系：")
    print("  A (0.5s, 无依赖)  B (0.3s, 无依赖)  C (0.4s, 无依赖)")
    print("        \\                |")
    print("         D (0.2s, 依赖 A+B)")
    print("                |")
    print("         E (0.3s, 依赖 D)")
    print()

    T0 = time.monotonic()
    result = await executor_engine(state, agent_runner=mock_agent_runner)

    print("执行时间线（秒）：")
    print(f"  {'Agent':<8} {'开始':>8} {'结束':>8} {'耗时':>8}")
    print(f"  {'─' * 36}")
    for aid in ["A", "B", "C", "D", "E"]:
        t = timeline[aid]
        print(f"  {aid:<8} {t['start']:>8.2f} {t['end']:>8.2f} {t['duration']:>8.2f}")

    total_time = max(t["end"] for t in timeline.values())
    print(f"\n  总耗时：{total_time:.2f}s")

    # 验证
    print("\n验证：")

    # A, B, C 应该几乎同时开始（start < 0.05s）
    abc_starts = [timeline[x]["start"] for x in ["A", "B", "C"]]
    abc_parallel = max(abc_starts) < 0.05
    print(f"  [并发] A,B,C 几乎同时开始（最大启动差 {max(abc_starts):.3f}s < 0.05s）：{'✅' if abc_parallel else '❌'}")

    # D 应该在 A 和 B 都完成后才开始（A 耗时 0.5s，B 耗时 0.3s → D 至少在 0.5s 后）
    d_after_ab = timeline["D"]["start"] >= timeline["A"]["end"] - 0.02 and timeline["D"]["start"] >= timeline["B"]["end"] - 0.02
    print(f"  [依赖] D 在 A({timeline['A']['end']:.2f}s) 和 B({timeline['B']['end']:.2f}s) 完成后开始({timeline['D']['start']:.2f}s)：{'✅' if d_after_ab else '❌'}")

    # E 应该在 D 完成后才开始
    e_after_d = timeline["E"]["start"] >= timeline["D"]["end"] - 0.02
    print(f"  [依赖] E 在 D({timeline['D']['end']:.2f}s) 完成后开始({timeline['E']['start']:.2f}s)：{'✅' if e_after_d else '❌'}")

    # 总耗时应该 ≈ 关键路径 A(0.5) + D(0.2) + E(0.3) = 1.0s，而非串行 1.7s
    is_parallel = total_time < 1.3  # 留点余量
    serial_time = 0.5 + 0.3 + 0.4 + 0.2 + 0.3
    print(f"  [效率] 总耗时 {total_time:.2f}s vs 串行 {serial_time}s（加速比 {serial_time / total_time:.1f}x）：{'✅' if is_parallel else '❌'}")

    return result, state


async def test_incremental():
    """测试 2：增量执行 — 未变更的 Agent 复用结果"""
    global T0, timeline
    timeline = {}

    task_graph = {
        "goal": "测试增量",
        "subtasks": [
            {"id": "task_a", "name": "任务A", "capability": "market_research", "dependencies": [], "priority": "high"},
            {"id": "task_b", "name": "任务B", "capability": "technical_analysis", "dependencies": [], "priority": "high"},
            {"id": "task_c", "name": "任务C", "capability": "competitive_intelligence", "dependencies": [], "priority": "medium"},
        ],
    }

    configs_v1 = [
        {"agent_id": "A", "subtask_id": "task_a", "system_prompt": "a_v1", "model_env_key": "MODEL_RESEARCH", "tools": [], "capability": "market_research"},
        {"agent_id": "B", "subtask_id": "task_b", "system_prompt": "b_v1", "model_env_key": "MODEL_ANALYSIS", "tools": [], "capability": "technical_analysis"},
        {"agent_id": "C", "subtask_id": "task_c", "system_prompt": "c_v1", "model_env_key": "MODEL_RESEARCH", "tools": [], "capability": "competitive_intelligence"},
    ]

    state: HiveState = {
        "goal": "测试增量",
        "task_graph": task_graph,
        "agent_configs": configs_v1,
        "agent_configs_hash": {},
        "agent_results": {},
        "debate_history": [],
        "debate_history_full": [],
        "debate_round": 0,
        "evolution_cycle": 0,
        "consensus_report": {},
        "evolution_log": [],
        "final_report": {},
        "token_budget": 30000,
        "token_used": 0,
        "forced_consensus": False,
        "uncovered_gaps": [],
    }

    print("\n" + "=" * 70)
    print("测试 2：增量执行 — 未变更的 Agent 复用结果")
    print("=" * 70)

    # 第一轮：全量执行
    print("\n--- 第一轮（全量执行）---")
    T0 = time.monotonic()
    result_v1 = await executor_engine(state, agent_runner=mock_agent_runner)
    print(f"  执行了：{list(timeline.keys())}")
    print(f"  Token 消耗：{result_v1['token_used'] - state['token_used']}")

    # 第二轮：只修改 B 的 prompt，A 和 C 应该复用
    print("\n--- 第二轮（只修改 B，A/C 应复用）---")
    timeline = {}
    configs_v2 = [
        {"agent_id": "A", "subtask_id": "task_a", "system_prompt": "a_v1", "model_env_key": "MODEL_RESEARCH", "tools": [], "capability": "market_research"},  # 未变
        {"agent_id": "B", "subtask_id": "task_b", "system_prompt": "b_v2_changed", "model_env_key": "MODEL_ANALYSIS", "tools": [], "capability": "technical_analysis"},  # 变更！
        {"agent_id": "C", "subtask_id": "task_c", "system_prompt": "c_v1", "model_env_key": "MODEL_RESEARCH", "tools": [], "capability": "competitive_intelligence"},  # 未变
    ]

    state_v2: HiveState = {
        **state,
        "agent_configs": configs_v2,
        "agent_configs_hash": result_v1["agent_configs_hash"],
        "agent_results": result_v1["agent_results"],
        "token_used": result_v1["token_used"],
    }

    T0 = time.monotonic()
    result_v2 = await executor_engine(state_v2, agent_runner=mock_agent_runner)

    executed = list(timeline.keys())
    reused = [aid for aid in ["A", "B", "C"] if aid not in executed]
    print(f"  重新执行：{executed}")
    print(f"  复用结果：{reused}")

    # 验证
    only_b_ran = executed == ["B"]
    a_c_reused = set(reused) == {"A", "C"}
    print(f"\n验证：")
    print(f"  [增量] 只有 B 重新执行：{'✅' if only_b_ran else '❌'}")
    print(f"  [复用] A 和 C 复用上轮结果：{'✅' if a_c_reused else '❌'}")
    # A 的结果应该和第一轮一致
    a_result_same = result_v2["agent_results"]["A"] == result_v1["agent_results"]["A"]
    print(f"  [一致] A 的结果与第一轮完全一致：{'✅' if a_result_same else '❌'}")


async def main():
    await test_concurrency()
    await test_incremental()
    print("\n" + "=" * 70)
    print("所有 Mock 测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
