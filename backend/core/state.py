"""HiveState — LangGraph 全局状态定义"""

from typing import TypedDict


class HiveState(TypedDict, total=False):
    # 用户目标
    goal: str
    # Decomposer 输出的任务图谱
    task_graph: dict
    # Spawner 生成的 Agent 配置列表
    agent_configs: list[dict]
    # 各 Agent 配置的 hash（用于增量执行判断）
    agent_configs_hash: dict[str, str]
    # 各 Agent 的执行结果
    agent_results: dict[str, dict]
    # 辩论摘要（压缩后，传入 LLM 用）
    debate_history: list[dict]
    # 完整辩论原文（仅用于最终报告，不传入 LLM）
    debate_history_full: list[dict]
    # 当前辩论轮次
    debate_round: int
    # 当前进化轮次（上限 2）
    evolution_cycle: int
    # 裁判 LLM 的共识评估
    consensus_report: dict
    # 各 Agent 修正后的结构化结论（Phase C 输出）
    structured_conclusions: dict[str, dict]
    # 团队重组日志
    evolution_log: list[dict]
    # Evolver 检测到的能力缺口（Council → Evolver 传递）
    gaps: list[str]
    # 最终报告
    final_report: dict
    # 总 token 预算
    token_budget: int
    # 已使用 token
    token_used: int
    # 是否强制共识（辩论超轮次或 token 耗尽）
    forced_consensus: bool
    # 未覆盖的能力缺口（进化次数达上限时记录）
    uncovered_gaps: list[str]
    # 运行模式（demo / standard / deep）
    mode: str
    # 最大辩论轮次（demo=1, standard=3, deep=3）
    max_debate_rounds: int
    # 最大 Agent 数量（demo=3, standard=7, deep=10）
    max_agents: int
