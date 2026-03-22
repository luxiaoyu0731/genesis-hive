"""Executor 端到端测试：Decomposer → Spawner → Executor（真实 LLM）"""

import asyncio
import json

from backend.engines.decomposer import decomposer_engine
from backend.engines.spawner import spawner_engine
from backend.engines.executor import executor_engine
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
        "token_budget": 30000,
        "token_used": 0,
        "forced_consensus": False,
        "uncovered_gaps": [],
    }

    # L1
    print("L1 Decomposer...")
    r = await decomposer_engine(state)
    state = {**state, **r}
    subtasks = state["task_graph"]["subtasks"]
    print(f"  → {len(subtasks)} 个子任务，Token: {state['token_used']}")

    # L2
    print("L2 Spawner...")
    r = await spawner_engine(state)
    state = {**state, **r}
    configs = state["agent_configs"]
    print(f"  → {len(configs)} 个 Agent，Token: {state['token_used']}")

    # L3
    print("L3 Executor（真实 LLM 并发调用）...")
    r = await executor_engine(state)
    state = {**state, **r}

    print(f"\n{'=' * 70}")
    print(f"执行完成！Token 总消耗：{state['token_used']}")
    print(f"{'=' * 70}\n")

    for aid, res in state["agent_results"].items():
        print(f"{'─' * 70}")
        print(f"Agent: {aid}")
        print(f"  置信度：{res.get('confidence', 'N/A')}")
        print(f"  耗时：{res.get('time_ms', 0)}ms")
        print(f"  Token：{res.get('tokens_used', 0)}")
        # 只打印结果前 150 字
        pr = res.get("preliminary_result", "")
        print(f"  结果（前150字）：{pr[:150]}...")


if __name__ == "__main__":
    asyncio.run(main())
