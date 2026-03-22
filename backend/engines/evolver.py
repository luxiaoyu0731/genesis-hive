"""L5 Evolver — 动态重组引擎

团队结构不是固定的，而是活的：
1. 能力缺口触发：裁判 LLM 检测到未覆盖维度时，生成新 Agent 补充
2. 低贡献检测：量化三指标（被引用次数 + 结论变更影响 + 信息增量）
3. 进化次数上限：max_evolution_cycles = 2
4. 每次变化记录完整的重组日志
"""

import json

from backend.core.llm_service import call_llm
from backend.core.state import HiveState
from backend.core.utils import extract_json as _extract_json

# 进化次数上限
MAX_EVOLUTION_CYCLES = 2

# 低贡献阈值
LOW_CONTRIBUTION_THRESHOLD = 0.2


def detect_low_contribution(
    agent_configs: list[dict],
    consensus_report: dict,
) -> list[dict]:
    """
    低贡献检测：基于裁判 LLM 输出的 contribution_scores。

    量化标准（三指标）：
    - 被引用次数（referenced_by_count）
    - 结论变更影响（conclusion_influence）
    - 信息增量（unique_information）

    退场条件：contribution_score < 0.2 且被引用次数 == 0
    """
    scores = consensus_report.get("contribution_scores", {})
    low_contributors = []

    for config in agent_configs:
        aid = config["agent_id"]
        # 魔鬼代言人不退场——对抗机制必须保留
        if aid == "devil_advocate_01":
            continue

        agent_score = scores.get(aid, {})
        if isinstance(agent_score, dict):
            score = agent_score.get("score", 1.0)
            ref_count = agent_score.get("referenced_by_count", 1)
            unique_info = agent_score.get("unique_information", True)
        else:
            # 兼容 score 直接是数字的情况
            score = float(agent_score) if agent_score else 1.0
            ref_count = 1
            unique_info = True

        if score < LOW_CONTRIBUTION_THRESHOLD and ref_count == 0:
            low_contributors.append({
                "agent_id": aid,
                "score": score,
                "referenced_by_count": ref_count,
                "unique_information": unique_info,
                "reason": (
                    f"贡献评分 {score:.2f} < {LOW_CONTRIBUTION_THRESHOLD}，"
                    f"被引用 {ref_count} 次，无独立信息增量"
                    if not unique_info
                    else f"贡献评分 {score:.2f} < {LOW_CONTRIBUTION_THRESHOLD}，"
                    f"被引用 {ref_count} 次"
                ),
            })

    return low_contributors


def prune_low_contribution(
    agent_configs: list[dict],
    low_contributors: list[dict],
) -> list[dict]:
    """移除低贡献 Agent，返回精简后的配置列表"""
    remove_ids = {lc["agent_id"] for lc in low_contributors}
    return [c for c in agent_configs if c["agent_id"] not in remove_ids]


GAP_AGENT_PROMPT = """你是 Genesis Hive 系统的 Agent 生成引擎。
现在辩论中发现了一个能力缺口，需要生成一个新的专家 Agent 来补充这个维度。

## 输出要求

输出严格的 JSON：
{
  "agent_id": "snake_case_01",
  "role": "角色名称（中文）",
  "personality": "性格特征（一句话）",
  "system_prompt": "完整的 system prompt，包含角色定义 + 专业领域 + 工作方法",
  "capability": "能力类型",
  "debate_style": "辩论风格描述",
  "max_tokens_per_turn": 2000
}

只输出 JSON。"""


async def spawn_for_gap(
    gap: str,
    goal: str,
    existing_roles: list[str],
) -> tuple[dict, int]:
    """为单个能力缺口生成新 Agent 配置"""
    messages = [
        {"role": "system", "content": GAP_AGENT_PROMPT},
        {
            "role": "user",
            "content": (
                f"项目目标：{goal}\n\n"
                f"能力缺口：{gap}\n\n"
                f"现有团队角色：{', '.join(existing_roles)}\n\n"
                f"请生成一个能填补「{gap}」缺口的专家 Agent。\n"
                f"这个 Agent 要从现有团队未覆盖的独特视角出发。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_META",
        messages=messages,
        temperature=0.6,
        max_tokens=1500,
    )

    tokens = result["usage"].get("total_tokens", 0)
    config = _extract_json(result["content"])

    # 补充确定性字段
    if "model_env_key" not in config:
        config["model_env_key"] = "MODEL_ANALYSIS"
    if "tools" not in config:
        config["tools"] = ["web_search", "browser"]
    if "subtask_id" not in config:
        config["subtask_id"] = f"gap_{config.get('agent_id', 'new')}"
    if "search_strategy" not in config:
        config["search_strategy"] = {
            "sources": ["专业报告", "政策法规", "案例研究"],
            "search_focus": gap,
        }
    if "framework" not in config:
        config["framework"] = "专项分析"

    return config, tokens


async def evolver_engine(state: HiveState) -> dict:
    """
    L5 Evolver 引擎：动态重组团队结构。

    流程：
    1. 检查进化次数是否达上限
    2. 检测低贡献 Agent 并移除
    3. 为能力缺口生成新 Agent
    4. 记录重组日志
    5. 返回更新后的 agent_configs，回到 Spawner/Executor 重跑

    Returns:
        更新 agent_configs, evolution_log, evolution_cycle, token_used
    """
    agent_configs = list(state["agent_configs"])
    consensus_report = state.get("consensus_report", {})
    evolution_log = list(state.get("evolution_log", []))
    evolution_cycle = state.get("evolution_cycle", 0) + 1
    goal = state["goal"]
    debate_round = state.get("debate_round", 0)
    total_tokens = 0

    # ── 检查进化次数上限 ──
    if evolution_cycle > MAX_EVOLUTION_CYCLES:
        # 超过上限，强制进入 synthesizer
        gaps = consensus_report.get("gaps", [])
        evolution_log.append({
            "cycle": evolution_cycle,
            "debate_round": debate_round,
            "action": "evolution_limit_reached",
            "reason": f"进化次数已达上限 ({MAX_EVOLUTION_CYCLES})，强制整合",
            "uncovered_gaps": gaps,
            "added": [],
            "removed": [],
        })
        return {
            "evolution_cycle": evolution_cycle,
            "evolution_log": evolution_log,
            "forced_consensus": True,
            "uncovered_gaps": gaps,
            "token_used": state.get("token_used", 0),
        }

    # ── 低贡献检测与退场 ──
    low_contributors = detect_low_contribution(agent_configs, consensus_report)
    removed_ids = [lc["agent_id"] for lc in low_contributors]

    if low_contributors:
        agent_configs = prune_low_contribution(agent_configs, low_contributors)

    # ── 能力缺口补充 ──
    gaps = consensus_report.get("gaps", [])
    existing_roles = [c.get("role", "") for c in agent_configs]
    new_configs = []

    for gap in gaps:
        config, tokens = await spawn_for_gap(gap, goal, existing_roles)
        new_configs.append(config)
        existing_roles.append(config.get("role", ""))
        total_tokens += tokens

    agent_configs.extend(new_configs)
    added_ids = [c["agent_id"] for c in new_configs]

    # ── 记录重组日志 ──
    log_entry = {
        "cycle": evolution_cycle,
        "debate_round": debate_round,
        "action": "team_restructure",
        "reason": {
            "capability_gaps": gaps,
            "low_contribution_agents": [
                {"agent_id": lc["agent_id"], "score": lc["score"], "reason": lc["reason"]}
                for lc in low_contributors
            ],
        },
        "added": added_ids,
        "removed": removed_ids,
        "team_size_before": len(state["agent_configs"]),
        "team_size_after": len(agent_configs),
    }
    evolution_log.append(log_entry)

    return {
        "agent_configs": agent_configs,
        "evolution_cycle": evolution_cycle,
        "evolution_log": evolution_log,
        "token_used": state.get("token_used", 0) + total_tokens,
    }
