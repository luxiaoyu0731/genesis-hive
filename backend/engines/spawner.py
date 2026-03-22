"""L2 Spawner — Agent 动态生成引擎（Genesis 核心）

接收 Decomposer 输出的 task_graph，为每个子任务动态生成 Agent 配置。
体现三层认知多样性：模型异构、信息源隔离、思维框架差异。
总是包含一个魔鬼代言人 Agent。
"""

import json

from backend.core.llm_service import call_llm
from backend.core.state import HiveState
from backend.core.utils import extract_json as _extract_json


# ── 三层认知多样性映射 ──────────────────────────────────────

# 第一层：模型异构 — 不同能力类型使用不同 LLM 底座
CAPABILITY_TO_MODEL: dict[str, str] = {
    "market_research": "MODEL_RESEARCH",        # GPT-4o-mini（速度优先）
    "technical_analysis": "MODEL_ANALYSIS",      # Claude Sonnet（深度推理）
    "competitive_intelligence": "MODEL_RESEARCH", # GPT-4o-mini
    "financial_analysis": "MODEL_ANALYSIS",      # Claude Sonnet（精确计算）
    "risk_analysis": "MODEL_ANALYSIS",           # Claude Sonnet（严谨分析）
    "strategic_planning": "MODEL_META",          # Claude Sonnet（全局视角）
    "data_analysis": "MODEL_RESEARCH",           # GPT-4o-mini
    "user_experience": "MODEL_RESEARCH",         # GPT-4o-mini
    "legal_compliance": "MODEL_ANALYSIS",        # Claude Sonnet
}

# 第二层：信息源隔离 — 不同能力类型的搜索策略和信息源
CAPABILITY_TO_SEARCH_STRATEGY: dict[str, dict] = {
    "market_research": {
        "sources": ["社交媒体", "用户论坛", "消费者调研报告"],
        "search_focus": "用户需求、使用场景、痛点反馈",
    },
    "technical_analysis": {
        "sources": ["技术博客", "GitHub", "学术论文", "技术文档"],
        "search_focus": "技术方案、架构设计、性能基准",
    },
    "competitive_intelligence": {
        "sources": ["行业报告", "竞品官网", "产品评测", "应用商店评论"],
        "search_focus": "竞品功能、市场定位、差异化策略",
    },
    "financial_analysis": {
        "sources": ["财报数据", "行业分析报告", "投资研报"],
        "search_focus": "成本结构、收入模型、ROI 估算",
    },
    "risk_analysis": {
        "sources": ["法规政策", "行业事故案例", "安全审计报告"],
        "search_focus": "合规风险、技术风险、运营风险",
    },
    "strategic_planning": {
        "sources": ["战略咨询报告", "行业趋势分析", "高管访谈"],
        "search_focus": "战略方向、优先级排序、里程碑规划",
    },
    "data_analysis": {
        "sources": ["公开数据集", "统计报告", "学术研究"],
        "search_focus": "数据趋势、统计建模、量化分析",
    },
    "user_experience": {
        "sources": ["UX 研究报告", "可用性测试", "设计趋势"],
        "search_focus": "用户旅程、交互模式、体验痛点",
    },
    "legal_compliance": {
        "sources": ["法律法规", "行业标准", "合规指南"],
        "search_focus": "法规要求、合规风险、政策变化",
    },
}

# 第三层：思维框架差异 — 嵌入不同的分析思维框架
CAPABILITY_TO_FRAMEWORK: dict[str, dict] = {
    "market_research": {
        "name": "Jobs-to-be-Done (JTBD)",
        "description": "从用户要完成的'任务'出发，分析需求背后的动机",
        "prompt_injection": (
            "你使用 Jobs-to-be-Done (JTBD) 思维框架进行分析。"
            "核心方法：识别用户在特定场景下要完成的'任务'，"
            "区分功能性任务、情感性任务和社会性任务，"
            "用'当我……的时候，我想要……以便……'的句式提炼洞察。"
        ),
    },
    "technical_analysis": {
        "name": "Gartner Hype Cycle（技术成熟度曲线）",
        "description": "评估技术在生命周期中的位置，判断实际可用性",
        "prompt_injection": (
            "你使用 Gartner Hype Cycle 思维框架进行分析。"
            "核心方法：判断相关技术处于技术触发期、期望膨胀期、"
            "幻灭低谷期、复苏爬升期还是成熟稳定期。"
            "区分技术的炒作热度和实际生产可用性，给出客观的技术成熟度评估。"
        ),
    },
    "competitive_intelligence": {
        "name": "Porter's Five Forces（波特五力）",
        "description": "从行业竞争五个维度分析竞争格局",
        "prompt_injection": (
            "你使用波特五力模型进行分析。"
            "核心方法：从供应商议价能力、买方议价能力、新进入者威胁、"
            "替代品威胁、行业竞争程度五个维度评估竞争格局。"
            "关注护城河和可持续竞争优势。"
        ),
    },
    "financial_analysis": {
        "name": "Unit Economics（单位经济模型）",
        "description": "从单位成本和收益出发，计算商业可行性",
        "prompt_injection": (
            "你使用 Unit Economics 思维框架进行分析。"
            "核心方法：计算 CAC（获客成本）、LTV（用户终身价值）、"
            "LTV/CAC 比率、回本周期。"
            "所有结论必须有具体数字支撑，不接受模糊的'有潜力'描述。"
        ),
    },
    "risk_analysis": {
        "name": "FMEA（失效模式与影响分析）",
        "description": "系统化识别潜在失效模式，量化风险优先级",
        "prompt_injection": (
            "你使用 FMEA 思维框架进行分析。"
            "核心方法：对每个潜在风险评估三个维度——"
            "严重度（Severity）、发生概率（Occurrence）、可检测性（Detection），"
            "计算风险优先数 RPN = S × O × D，按 RPN 排序优先处理。"
        ),
    },
    "strategic_planning": {
        "name": "OKR + Wardley Map",
        "description": "目标-关键结果 + 价值链演进地图",
        "prompt_injection": (
            "你使用 OKR + Wardley Map 思维框架进行分析。"
            "核心方法：先用 Wardley Map 画出价值链中各组件的演进位置"
            "（创世→定制→产品→商品），识别战略杠杆点；"
            "再用 OKR 框架将战略方向转化为可衡量的目标和关键结果。"
        ),
    },
    "data_analysis": {
        "name": "CRISP-DM（数据挖掘跨行业标准流程）",
        "description": "结构化的数据分析方法论",
        "prompt_injection": (
            "你使用 CRISP-DM 思维框架进行分析。"
            "核心方法：业务理解→数据理解→数据准备→建模→评估→部署，"
            "每一步都要明确输入输出和质量标准。"
        ),
    },
    "user_experience": {
        "name": "Design Thinking（设计思维）",
        "description": "以用户为中心的创新方法论",
        "prompt_injection": (
            "你使用 Design Thinking 思维框架进行分析。"
            "核心方法：共情→定义→构思→原型→测试，"
            "始终从用户视角出发，通过快速原型验证假设。"
        ),
    },
    "legal_compliance": {
        "name": "合规矩阵分析",
        "description": "系统化的法规合规评估框架",
        "prompt_injection": (
            "你使用合规矩阵分析框架。"
            "核心方法：列出所有适用法规，逐条评估合规状态"
            "（合规/部分合规/不合规），标注风险等级和整改优先级。"
        ),
    },
}

# 工具分配 — 按能力类型从 tool_pool 自动匹配
CAPABILITY_TO_TOOLS: dict[str, list[str]] = {
    "market_research": ["web_search", "social_media_scraper"],
    "technical_analysis": ["web_search", "code_executor"],
    "competitive_intelligence": ["web_search", "browser"],
    "financial_analysis": ["web_search", "code_executor"],
    "risk_analysis": ["web_search", "browser"],
    "strategic_planning": ["web_search"],
    "data_analysis": ["web_search", "code_executor"],
    "user_experience": ["web_search", "browser"],
    "legal_compliance": ["web_search"],
}

# 魔鬼代言人的思维框架
ADVERSARY_FRAMEWORK = {
    "name": "Pre-mortem Analysis（预验尸法）",
    "description": "假设项目已经失败，倒推失败原因",
    "prompt_injection": (
        "你使用 Pre-mortem Analysis（预验尸法）思维框架。"
        "核心方法：假设这个项目/方案已经彻底失败了，"
        "你的任务是倒推出最可能的失败原因。"
        "对每一个乐观假设都要追问'如果这个假设不成立会怎样？'，"
        "对每一个'优势'都要找到它可能变成'劣势'的场景。"
        "你不是为了否定而否定，而是为了让最终方案更加健壮。"
    ),
}


SPAWNER_SYSTEM_PROMPT = """你是 Genesis Hive 系统的 Agent 生成引擎（Spawner）。
你的职责是为一个子任务生成一个专业 Agent 的完整配置。

## 输出要求

你必须输出严格的 JSON，格式如下：
{
  "agent_id": "唯一标识符（snake_case + 序号，如 market_researcher_01）",
  "role": "角色名称（中文）",
  "personality": "性格特征描述（一句话）",
  "system_prompt": "完整的 system prompt，包含角色定义、工作方法、思维框架",
  "debate_style": "辩论风格描述（一句话，说明质疑和回应时的表现）",
  "max_tokens_per_turn": 2000
}

## 生成规则

1. system_prompt 必须包含：角色定义 + 专业领域 + 工作方法 + 指定的思维框架 + 信息源偏好
2. personality 要有个性，不要千篇一律
3. debate_style 要能体现不同的辩论风格
4. agent_id 使用 snake_case，带 _01 后缀

只输出 JSON，不要输出任何其他内容。"""


async def spawner_engine(state: HiveState) -> dict:
    """
    L2 Spawner 引擎：为 task_graph 中的每个子任务生成 Agent 配置。

    读取 state["task_graph"]，为每个子任务 + 魔鬼代言人生成配置，
    返回 agent_configs 列表。
    """
    task_graph = state["task_graph"]
    subtasks = task_graph.get("subtasks", [])
    required_adversary = task_graph.get("required_adversary", True)

    # Demo 模式限制 Agent 数量（保留 1 个位置给魔鬼代言人）
    max_agents = state.get("max_agents", 7)
    max_regular = max(1, max_agents - 1)  # 至少 1 个常规 Agent
    if len(subtasks) > max_regular:
        # 按优先级排序，取前 max_regular 个
        priority_order = {"high": 0, "medium": 1, "low": 2}
        subtasks = sorted(subtasks, key=lambda s: priority_order.get(s.get("priority", "medium"), 1))
        subtasks = subtasks[:max_regular]

    agent_configs = []
    total_tokens = 0

    # 并发生成所有常规 Agent 配置（+ 魔鬼代言人一起并发）
    import asyncio

    # Two-phase 并发：
    # Phase 1 — 所有常规 Agent 并发生成
    regular_results = await asyncio.gather(
        *[_spawn_agent_for_subtask(st) for st in subtasks]
    )
    for config, tokens in regular_results:
        agent_configs.append(config)
        total_tokens += tokens

    # Phase 2 — 魔鬼代言人拿到完整的 existing_configs 上下文后生成
    adversary_config, adversary_tokens = await _spawn_adversary(
        task_graph, agent_configs
    )
    agent_configs.append(adversary_config)
    total_tokens += adversary_tokens

    # Demo 模式标记（用于 Executor 降低 max_tokens 加速响应）
    mode = state.get("mode", "standard")
    if mode == "demo":
        for c in agent_configs:
            c["_demo_mode"] = True

    return {
        "agent_configs": agent_configs,
        "token_used": state.get("token_used", 0) + total_tokens,
    }


async def _spawn_agent_for_subtask(subtask: dict) -> tuple[dict, int]:
    """为单个子任务生成 Agent 配置"""
    capability = subtask.get("capability", "market_research")

    # 三层认知多样性注入
    model_env_key = CAPABILITY_TO_MODEL.get(capability, "MODEL_RESEARCH")
    search_strategy = CAPABILITY_TO_SEARCH_STRATEGY.get(capability, {})
    framework = CAPABILITY_TO_FRAMEWORK.get(capability, {})
    tools = CAPABILITY_TO_TOOLS.get(capability, ["web_search"])

    messages = [
        {"role": "system", "content": SPAWNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"请为以下子任务生成 Agent 配置：\n\n"
                f"子任务 ID：{subtask['id']}\n"
                f"子任务名称：{subtask['name']}\n"
                f"能力类型：{capability}\n"
                f"任务描述：{subtask.get('description', subtask['name'])}\n"
                f"优先级：{subtask.get('priority', 'medium')}\n\n"
                f"## 必须嵌入的思维框架\n"
                f"框架名称：{framework.get('name', 'N/A')}\n"
                f"框架描述：{framework.get('description', 'N/A')}\n"
                f"嵌入方式：将以下内容整合进 system_prompt 中：\n"
                f"{framework.get('prompt_injection', '')}\n\n"
                f"## 信息源偏好\n"
                f"优先搜索的信息源：{', '.join(search_strategy.get('sources', []))}\n"
                f"搜索重点：{search_strategy.get('search_focus', 'N/A')}\n\n"
                f"请生成完整的 Agent 配置 JSON。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_META",
        messages=messages,
        temperature=0.6,
        max_tokens=1500,
    )

    config = _extract_json(result["content"])

    # 强制注入确定性字段（不依赖 LLM 的输出）
    config["model_env_key"] = model_env_key
    config["tools"] = tools
    config["capability"] = capability
    config["subtask_id"] = subtask["id"]
    config["search_strategy"] = search_strategy
    config["framework"] = framework.get("name", "N/A")

    tokens = result["usage"].get("total_tokens", 0)
    return config, tokens


async def _spawn_adversary(
    task_graph: dict, existing_configs: list[dict]
) -> tuple[dict, int]:
    """生成魔鬼代言人 Agent — 使用不同模型 + Pre-mortem 思维框架"""
    goal = task_graph.get("goal", "")
    existing_roles = [c.get("role", "") for c in existing_configs]

    messages = [
        {"role": "system", "content": SPAWNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"请生成一个**魔鬼代言人（Devil's Advocate）**Agent 配置。\n\n"
                f"项目目标：{goal}\n"
                f"已有的团队成员角色：{', '.join(existing_roles)}\n\n"
                f"## 魔鬼代言人的核心职责\n"
                f"- 专门站在反面，挑战其他 Agent 的每一个乐观假设\n"
                f"- 寻找方案中的漏洞、盲点和未考虑的风险\n"
                f"- 不是为了否定而否定，而是为了让最终结论更加健壮\n\n"
                f"## 必须嵌入的思维框架\n"
                f"框架名称：{ADVERSARY_FRAMEWORK['name']}\n"
                f"嵌入方式：将以下内容整合进 system_prompt 中：\n"
                f"{ADVERSARY_FRAMEWORK['prompt_injection']}\n\n"
                f"## 辩论风格要求\n"
                f"- 尖锐但有建设性\n"
                f"- 对每个结论都要求数据或逻辑支撑\n"
                f"- 善于发现'大家都同意但没有验证'的隐含假设\n\n"
                f"请生成完整的 Agent 配置 JSON。agent_id 必须是 devil_advocate_01。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_META",
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
    )

    config = _extract_json(result["content"])

    # 魔鬼代言人强制使用不同模型（Gemini — 制造认知差异）
    config["agent_id"] = "devil_advocate_01"
    config["model_env_key"] = "MODEL_ADVERSARY"
    config["tools"] = ["web_search", "browser"]
    config["capability"] = "adversary"
    config["subtask_id"] = "__adversary__"
    config["search_strategy"] = {
        "sources": ["反面案例", "失败报告", "批评性评论", "学术质疑"],
        "search_focus": "失败原因、反面论据、未被重视的风险",
    }
    config["framework"] = ADVERSARY_FRAMEWORK["name"]

    tokens = result["usage"].get("total_tokens", 0)
    return config, tokens
