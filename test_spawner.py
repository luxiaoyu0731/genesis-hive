"""Spawner 引擎端到端测试：Decomposer → Spawner"""

import asyncio
import json

from backend.engines.decomposer import decomposer_engine
from backend.engines.spawner import spawner_engine
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

    # ── L1 Decomposer ──
    print("=" * 70)
    print("L1 Decomposer: 分解任务...")
    print("=" * 70)
    decomposer_result = await decomposer_engine(state)
    state = {**state, **decomposer_result}
    subtasks = state["task_graph"]["subtasks"]
    print(f"分解出 {len(subtasks)} 个子任务：")
    for s in subtasks:
        print(f"  - {s['id']} ({s['capability']})")

    # ── L2 Spawner ──
    print("\n" + "=" * 70)
    print("L2 Spawner: 生成 Agent 团队...")
    print("=" * 70)
    spawner_result = await spawner_engine(state)
    state = {**state, **spawner_result}
    configs = state["agent_configs"]

    print(f"\n共生成 {len(configs)} 个 Agent（含魔鬼代言人）\n")

    # 打印每个 Agent 的关键信息
    for i, c in enumerate(configs, 1):
        print(f"{'─' * 70}")
        print(f"Agent #{i}: {c.get('agent_id', 'N/A')}")
        print(f"  角色：{c.get('role', 'N/A')}")
        print(f"  性格：{c.get('personality', 'N/A')}")
        print(f"  模型：{c.get('model_env_key', 'N/A')}")
        print(f"  工具：{c.get('tools', [])}")
        print(f"  思维框架：{c.get('framework', 'N/A')}")
        print(f"  辩论风格：{c.get('debate_style', 'N/A')}")
        print(f"  信息源：{c.get('search_strategy', {}).get('sources', [])}")
        prompt = c.get("system_prompt", "")
        print(f"  System Prompt（前 120 字）：{prompt[:120]}...")

    # ── 验证 ──
    print(f"\n{'=' * 70}")
    print("验证结果：")
    print(f"{'=' * 70}")

    # 1. 模型异构检查
    models = [c["model_env_key"] for c in configs]
    unique_models = set(models)
    print(f"\n[模型异构] 使用的模型类型：{unique_models}")
    print(f"  模型数量：{len(unique_models)} 种", "✅" if len(unique_models) >= 2 else "❌")
    for c in configs:
        print(f"    {c['agent_id']:30s} → {c['model_env_key']}")

    # 2. 思维框架差异检查
    frameworks = [c.get("framework", "N/A") for c in configs]
    unique_frameworks = set(frameworks)
    print(f"\n[思维框架] 使用的框架：")
    for c in configs:
        print(f"    {c['agent_id']:30s} → {c.get('framework', 'N/A')}")
    print(f"  框架数量：{len(unique_frameworks)} 种", "✅" if len(unique_frameworks) >= 3 else "❌")

    # 3. 魔鬼代言人检查
    adversary = [c for c in configs if c.get("model_env_key") == "MODEL_ADVERSARY"]
    print(f"\n[魔鬼代言人] 存在：{'是' if adversary else '否'}", "✅" if adversary else "❌")
    if adversary:
        a = adversary[0]
        print(f"    ID：{a['agent_id']}")
        print(f"    模型：{a['model_env_key']}（Gemini — 与其他 Agent 不同）")
        print(f"    框架：{a.get('framework')}")

    # 4. 工具分配检查
    print(f"\n[工具分配]")
    for c in configs:
        print(f"    {c['agent_id']:30s} → {c.get('tools', [])}")

    # 5. Token 消耗
    print(f"\n[Token 消耗] 总计：{state['token_used']}")


if __name__ == "__main__":
    asyncio.run(main())
