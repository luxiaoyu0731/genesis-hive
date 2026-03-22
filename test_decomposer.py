"""Decomposer 引擎测试脚本"""

import asyncio
import json
import sys

from backend.engines.decomposer import decomposer_engine
from backend.core.state import HiveState


async def main():
    # 构造初始 state
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

    print(f"输入目标：{state['goal']}")
    print("=" * 60)
    print("调用 Decomposer 引擎...\n")

    result = await decomposer_engine(state)

    task_graph = result["task_graph"]
    print(json.dumps(task_graph, ensure_ascii=False, indent=2))

    # 验证
    print("\n" + "=" * 60)
    print("验证结果：")
    subtasks = task_graph.get("subtasks", [])
    subtask_ids = [s["id"] for s in subtasks]
    capabilities = [s["capability"] for s in subtasks]

    print(f"  子任务数量：{len(subtasks)}（要求 3-7）", "✅" if 3 <= len(subtasks) <= 7 else "❌")
    print(f"  required_adversary：{task_graph.get('required_adversary')}", "✅" if task_graph.get("required_adversary") else "❌")
    print(f"  子任务 ID 列表：{subtask_ids}")
    print(f"  能力类型列表：{capabilities}")
    print(f"  Token 消耗：{result['token_used']}")


if __name__ == "__main__":
    asyncio.run(main())
