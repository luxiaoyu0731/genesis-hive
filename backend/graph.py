"""Genesis Hive — LangGraph 编排

轮次间重编译方案：每轮辩论结束后如需重组团队，
重新构建并编译新图。重编译耗时毫秒级。

所有动态路由使用 Command API，不使用 conditional_edges。
"""

from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.types import Command

from backend.core.state import HiveState
from backend.engines.decomposer import decomposer_engine
from backend.engines.spawner import spawner_engine
from backend.engines.executor import executor_engine
from backend.engines.council import council_engine as _council_engine_inner
from backend.engines.evolver import evolver_engine as _evolver_engine_inner, MAX_EVOLUTION_CYCLES
from backend.engines.synthesizer import synthesizer_engine


# ── LangGraph 节点包装器（返回 Command 实现动态路由） ──────


async def council_node(state: HiveState) -> Command[Literal["synthesizer", "evolver", "council"]]:
    """
    Council 节点：执行一轮辩论，然后用 Command 做动态路由。

    路由逻辑：
    1. 共识达成 → synthesizer
    2. 辩论 ≥3 轮 或 token ≥90% → 强制 synthesizer
    3. 能力缺口 且 进化<2 → evolver
    4. 能力缺口 且 进化≥2 → 强制 synthesizer（标注未覆盖缺口）
    5. 未共识 → 继续 council
    """
    # 执行辩论（Phase A → E）
    result = await _council_engine_inner(state)

    consensus = result.get("consensus_report", {})
    debate_round = result.get("debate_round", 1)
    token_used = result.get("token_used", state.get("token_used", 0))
    token_budget = state.get("token_budget", 100000)
    evolution_cycle = state.get("evolution_cycle", 0)

    # 基础更新字段（所有路径共享）
    base_update = {
        "debate_round": debate_round,
        "debate_history": result.get("debate_history", []),
        "debate_history_full": result.get("debate_history_full", []),
        "consensus_report": consensus,
        "structured_conclusions": result.get("structured_conclusions", {}),
        "token_used": token_used,
    }

    # 路由决策
    if consensus.get("consensus_reached"):
        # 路径 1：共识达成 → synthesizer
        return Command(goto="synthesizer", update=base_update)

    max_rounds = state.get("max_debate_rounds", 3)
    if debate_round >= max_rounds or token_used > token_budget * 0.9:
        # 路径 2：强制终止 → synthesizer
        return Command(goto="synthesizer", update={
            **base_update,
            "forced_consensus": True,
        })

    if consensus.get("capability_gap_detected") and evolution_cycle < MAX_EVOLUTION_CYCLES:
        # 路径 3：能力缺口 → evolver
        return Command(goto="evolver", update={
            **base_update,
            "gaps": consensus.get("gaps", []),
        })

    if consensus.get("capability_gap_detected") and evolution_cycle >= MAX_EVOLUTION_CYCLES:
        # 路径 4：进化上限 → 强制 synthesizer
        return Command(goto="synthesizer", update={
            **base_update,
            "forced_consensus": True,
            "uncovered_gaps": consensus.get("gaps", []),
        })

    # 路径 5：继续辩论
    return Command(goto="council", update=base_update)


async def evolver_node(state: HiveState) -> Command[Literal["spawner"]]:
    """
    Evolver 节点：动态重组团队，然后回到 Spawner 重新生成。
    """
    result = await _evolver_engine_inner(state)

    return Command(goto="spawner", update={
        "agent_configs": result.get("agent_configs", state.get("agent_configs", [])),
        "evolution_cycle": result.get("evolution_cycle", 0),
        "evolution_log": result.get("evolution_log", []),
        "token_used": result.get("token_used", state.get("token_used", 0)),
    })


# ── 图构建函数 ─────────────────────────────────────────────


def build_hive_graph(agent_configs: list[dict] | None = None):
    """
    构建 Genesis Hive 的 LangGraph 图。

    每轮进化后可能重新调用此函数（轮次间重编译）。
    agent_configs 参数用于 Executor 根据当前配置构建。

    Returns:
        CompiledGraph
    """
    graph = StateGraph(HiveState)

    # 固定节点
    graph.add_node("decomposer", decomposer_engine)
    graph.add_node("spawner", spawner_engine)
    graph.add_node("executor", executor_engine)
    graph.add_node("council", council_node)       # Command 路由
    graph.add_node("evolver", evolver_node)        # Command 路由
    graph.add_node("synthesizer", synthesizer_engine)

    # 固定边（线性流程部分）
    graph.add_edge("decomposer", "spawner")
    graph.add_edge("spawner", "executor")
    graph.add_edge("executor", "council")
    # council → synthesizer/evolver/council 由 Command 动态路由
    # evolver → spawner 由 Command 动态路由

    graph.set_entry_point("decomposer")
    graph.set_finish_point("synthesizer")

    return graph.compile()


def create_initial_state(
    goal: str,
    mode: str = "demo",
) -> HiveState:
    """创建初始状态"""
    budget_map = {
        "demo": 30000,
        "standard": 100000,
        "deep": 250000,
    }
    rounds_map = {
        "demo": 1,
        "standard": 3,
        "deep": 3,
    }
    agents_map = {
        "demo": 3,
        "standard": 7,
        "deep": 10,
    }
    return {
        "goal": goal,
        "task_graph": {},
        "agent_configs": [],
        "agent_configs_hash": {},
        "agent_results": {},
        "debate_history": [],
        "debate_history_full": [],
        "debate_round": 0,
        "evolution_cycle": 0,
        "consensus_report": {},
        "structured_conclusions": {},
        "evolution_log": [],
        "gaps": [],
        "final_report": {},
        "token_budget": budget_map.get(mode, 100000),
        "token_used": 0,
        "forced_consensus": False,
        "uncovered_gaps": [],
        "mode": mode,
        "max_debate_rounds": rounds_map.get(mode, 3),
        "max_agents": agents_map.get(mode, 7),
    }
