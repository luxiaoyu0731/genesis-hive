"""Evolver 引擎集成测试

场景：
1. 初始团队 4 个 Agent（市场、技术、竞品、魔鬼代言人）
2. 第一轮辩论后裁判检测到缺少"数据隐私"视角
3. Evolver 检测到缺口 + 1 个低贡献 Agent，生成隐私专家
4. 增量执行：只有隐私专家重新执行，其他复用上轮结果
5. 第二轮辩论在更完整的团队中进行
"""

import asyncio
import json
import time

from backend.engines.evolver import evolver_engine, detect_low_contribution, MAX_EVOLUTION_CYCLES
from backend.engines.spawner import spawner_engine, _spawn_agent_for_subtask
from backend.engines.executor import executor_engine
from backend.engines.council import council_engine
from backend.core.state import HiveState


async def main():
    # ══════════════════════════════════════════════════════════
    # 阶段 0：构造初始团队（4 Agent，跳过 Decomposer/Spawner 用预设配置加速测试）
    # ══════════════════════════════════════════════════════════
    print("=" * 70)
    print("阶段 0：构造初始团队（4 Agent + 魔鬼代言人）")
    print("=" * 70)

    task_graph = {
        "goal": "分析小红书做AI搜索的可行性",
        "subtasks": [
            {"id": "market_research", "name": "市场需求调研", "capability": "market_research", "dependencies": [], "priority": "high"},
            {"id": "tech_assessment", "name": "技术可行性评估", "capability": "technical_analysis", "dependencies": [], "priority": "high"},
            {"id": "competitor_analysis", "name": "竞品分析", "capability": "competitive_intelligence", "dependencies": [], "priority": "medium"},
        ],
    }

    # 用 Spawner 为 3 个子任务 + 魔鬼代言人生成配置
    init_state: HiveState = {
        "goal": "分析小红书做AI搜索的可行性",
        "task_graph": task_graph,
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
        "token_budget": 80000,
        "token_used": 0,
        "forced_consensus": False,
        "uncovered_gaps": [],
    }

    print("  Spawner 生成 Agent 团队...")
    spawner_result = await spawner_engine(init_state)
    state: HiveState = {**init_state, **spawner_result}
    configs = state["agent_configs"]
    print(f"  → 生成 {len(configs)} 个 Agent：{[c['agent_id'] for c in configs]}")
    print(f"  → Token: {state['token_used']}")

    # ══════════════════════════════════════════════════════════
    # 阶段 1：第一轮执行 + 辩论
    # ══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("阶段 1：第一轮执行 + 辩论")
    print("=" * 70)

    print("  Executor 并发执行...")
    exec_result = await executor_engine(state)
    state = {**state, **exec_result}
    print(f"  → Token: {state['token_used']}")

    print("  Council 圆桌辩论...")
    council_result = await council_engine(state)
    state = {**state, **council_result}
    consensus = state["consensus_report"]
    print(f"  → 共识类型：{consensus.get('consensus_type', 'N/A')}")
    print(f"  → 推荐操作：{consensus.get('recommendation', 'N/A')}")
    print(f"  → 能力缺口检测：{consensus.get('capability_gap_detected', False)}")
    print(f"  → 缺口详情：{consensus.get('gaps', [])}")
    print(f"  → Token: {state['token_used']}")

    # ══════════════════════════════════════════════════════════
    # 阶段 1.5：强制注入测试条件（确保 Evolver 被触发）
    # ══════════════════════════════════════════════════════════
    # 如果裁判恰好没检测到缺口，我们手动注入一个"数据隐私"缺口
    # 以确保测试场景完整覆盖 Evolver 逻辑
    if not consensus.get("capability_gap_detected"):
        print(f"\n  [测试注入] 裁判未检测到缺口，手动注入'数据隐私合规'缺口")
        consensus["capability_gap_detected"] = True
        consensus["gaps"] = ["数据隐私与合规分析"]
        state["consensus_report"] = consensus

    # 同样确保有一个低贡献 Agent（用于测试退场逻辑）
    scores = consensus.get("contribution_scores", {})
    # 找一个非魔鬼代言人且分数最低的 Agent，人为压低其分数
    non_devil = [c for c in configs if c["agent_id"] != "devil_advocate_01"]
    if non_devil and scores:
        # 找分数最低的
        lowest_aid = None
        lowest_score = 999
        for c in non_devil:
            aid = c["agent_id"]
            s = scores.get(aid, {})
            sc = s.get("score", 1.0) if isinstance(s, dict) else 1.0
            if sc < lowest_score:
                lowest_score = sc
                lowest_aid = aid
        if lowest_aid and lowest_score > 0.2:
            print(f"  [测试注入] 将 {lowest_aid} 的贡献分从 {lowest_score:.2f} 压低到 0.1")
            if isinstance(scores.get(lowest_aid), dict):
                scores[lowest_aid]["score"] = 0.1
                scores[lowest_aid]["referenced_by_count"] = 0
            else:
                scores[lowest_aid] = {"score": 0.1, "referenced_by_count": 0, "unique_information": False}
            state["consensus_report"]["contribution_scores"] = scores

    # ══════════════════════════════════════════════════════════
    # 阶段 2：Evolver 动态重组
    # ══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("阶段 2：Evolver 动态重组")
    print("=" * 70)

    # 检测低贡献
    low = detect_low_contribution(state["agent_configs"], state["consensus_report"])
    print(f"  低贡献 Agent：{[l['agent_id'] for l in low] if low else '无'}")
    for l in low:
        print(f"    → {l['agent_id']}: score={l['score']:.2f}, reason={l['reason']}")

    # 运行 Evolver
    evolver_result = await evolver_engine(state)
    state = {**state, **evolver_result}

    new_configs = state["agent_configs"]
    print(f"\n  重组后团队：{[c['agent_id'] for c in new_configs]}")
    print(f"  进化轮次：{state['evolution_cycle']}")
    print(f"  Token: {state['token_used']}")

    # 打印 evolution_log
    print(f"\n  {'─' * 60}")
    print(f"  Evolution Log：")
    print(f"  {'─' * 60}")
    for entry in state["evolution_log"]:
        print(f"  Cycle {entry.get('cycle', '?')} (辩论轮 {entry.get('debate_round', '?')}):")
        print(f"    操作：{entry.get('action', 'N/A')}")
        reason = entry.get("reason", {})
        if isinstance(reason, dict):
            if reason.get("capability_gaps"):
                print(f"    能力缺口：{reason['capability_gaps']}")
            if reason.get("low_contribution_agents"):
                for lca in reason["low_contribution_agents"]:
                    print(f"    退场：{lca['agent_id']} (score={lca['score']:.2f}, {lca['reason']})")
        print(f"    新增：{entry.get('added', [])}")
        print(f"    移除：{entry.get('removed', [])}")
        print(f"    团队规模：{entry.get('team_size_before', '?')} → {entry.get('team_size_after', '?')}")

    # ══════════════════════════════════════════════════════════
    # 阶段 3：增量执行（只跑新增 Agent）
    # ══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("阶段 3：增量执行（只跑新增 Agent）")
    print("=" * 70)

    # 更新 task_graph 加入新子任务（Evolver 生成的 Agent 的 subtask_id）
    new_subtasks = list(task_graph["subtasks"])
    for c in new_configs:
        sid = c.get("subtask_id", "")
        if sid.startswith("gap_") and not any(s["id"] == sid for s in new_subtasks):
            new_subtasks.append({
                "id": sid,
                "name": c.get("role", sid),
                "capability": c.get("capability", "legal_compliance"),
                "dependencies": [],
                "priority": "high",
            })
    state["task_graph"] = {**task_graph, "subtasks": new_subtasks}

    t0 = time.monotonic()
    exec_result2 = await executor_engine(state)
    elapsed = time.monotonic() - t0
    state = {**state, **exec_result2}

    # 判断哪些是新执行的，哪些是复用的
    old_hashes = evolver_result.get("agent_configs_hash", state.get("agent_configs_hash", {}))
    new_results = exec_result2["agent_results"]
    executed = []
    reused = []
    for c in new_configs:
        aid = c["agent_id"]
        # 如果这个 Agent 在上一轮不存在或 hash 变了，就是新执行的
        if aid not in old_hashes:
            executed.append(aid)
        else:
            reused.append(aid)

    # 更准确地判断：上轮有结果的 Agent 如果 hash 未变就是复用
    prev_results = state.get("agent_results", {})
    actually_reused = []
    actually_executed = []
    for c in new_configs:
        aid = c["agent_id"]
        old_hash = exec_result.get("agent_configs_hash", {}).get(aid)
        new_hash = exec_result2["agent_configs_hash"].get(aid)
        if old_hash and old_hash == new_hash:
            actually_reused.append(aid)
        else:
            actually_executed.append(aid)

    print(f"  重新执行：{actually_executed}")
    print(f"  复用结果：{actually_reused}")
    print(f"  执行耗时：{elapsed:.1f}s")
    print(f"  Token: {state['token_used']}")

    # ══════════════════════════════════════════════════════════
    # 阶段 4：第二轮辩论
    # ══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("阶段 4：第二轮辩论（含新加入的隐私专家）")
    print("=" * 70)

    council_result2 = await council_engine(state)
    state = {**state, **council_result2}
    consensus2 = state["consensus_report"]
    print(f"  辩论轮次：{state['debate_round']}")
    print(f"  共识类型：{consensus2.get('consensus_type', 'N/A')}")
    print(f"  推荐操作：{consensus2.get('recommendation', 'N/A')}")
    print(f"  Token: {state['token_used']}")

    # ══════════════════════════════════════════════════════════
    # 阶段 5：验证进化上限
    # ══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("阶段 5：验证进化次数上限（强制第 3 次进化）")
    print("=" * 70)

    # 模拟已经进化了 2 次，尝试第 3 次
    state["evolution_cycle"] = MAX_EVOLUTION_CYCLES
    state["consensus_report"]["capability_gap_detected"] = True
    state["consensus_report"]["gaps"] = ["国际市场分析"]

    evolver_result3 = await evolver_engine(state)
    state = {**state, **evolver_result3}

    last_log = state["evolution_log"][-1]
    blocked = last_log.get("action") == "evolution_limit_reached"
    print(f"  进化被阻止：{'✅' if blocked else '❌'}")
    print(f"  forced_consensus：{state.get('forced_consensus', False)}")
    print(f"  uncovered_gaps：{state.get('uncovered_gaps', [])}")

    # ══════════════════════════════════════════════════════════
    # 最终验证
    # ══════════════════════════════════════════════════════════
    print(f"\n{'═' * 70}")
    print("验证清单")
    print(f"{'═' * 70}")

    # 1. 能力缺口触发了新 Agent 生成
    added_in_cycle1 = state["evolution_log"][0].get("added", [])
    print(f"  [缺口补充] 第1次进化新增 Agent：{added_in_cycle1}",
          "✅" if added_in_cycle1 else "❌")

    # 2. 低贡献 Agent 被移除
    removed_in_cycle1 = state["evolution_log"][0].get("removed", [])
    print(f"  [低贡献退场] 第1次进化移除 Agent：{removed_in_cycle1}",
          "✅" if removed_in_cycle1 else "⚠️ 无低贡献 Agent")

    # 3. 增量执行只跑了新增 Agent
    new_agent_in_executed = any(
        a in actually_executed for a in added_in_cycle1
    )
    print(f"  [增量执行] 新 Agent 被执行：{'✅' if new_agent_in_executed else '❌'}")
    print(f"  [增量执行] 老 Agent 被复用：{'✅' if actually_reused else '❌'}")

    # 4. 进化上限阻止第 3 次进化
    print(f"  [进化上限] 第 3 次进化被阻止：{'✅' if blocked else '❌'}")
    print(f"  [未覆盖缺口] 标注在报告中：{'✅' if state.get('uncovered_gaps') else '❌'}")

    # 5. Evolution log 完整
    print(f"  [重组日志] 共 {len(state['evolution_log'])} 条记录")
    for i, entry in enumerate(state["evolution_log"]):
        print(f"    Log {i+1}: cycle={entry.get('cycle')}, action={entry.get('action')}, "
              f"+{len(entry.get('added', []))} -{len(entry.get('removed', []))}")

    print(f"\n  Token 总消耗：{state['token_used']} / {state['token_budget']}")


if __name__ == "__main__":
    asyncio.run(main())
