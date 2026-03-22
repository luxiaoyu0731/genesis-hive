"""L1 Decomposer — 任务分解引擎

接收自然语言目标，通过元决策模型（MODEL_META）进行意图解析和任务分解，
输出结构化的任务图谱（task_graph）。
"""

import json

from backend.core.llm_service import call_llm
from backend.core.state import HiveState
from backend.core.utils import extract_json as _extract_json

# 任务分解的 system prompt
DECOMPOSER_SYSTEM_PROMPT = """你是 Genesis Hive 系统的任务分解引擎（Decomposer）。
你的职责是将用户的自然语言目标分解为一组可执行的子任务。

## 输出要求

你必须输出严格的 JSON，格式如下：
{
  "goal": "用户原始目标",
  "complexity": "low | medium | high",
  "domain": "目标所属领域（如：商业分析、技术评估、市场调研等）",
  "subtasks": [
    {
      "id": "唯一标识符（snake_case）",
      "name": "子任务名称（中文）",
      "capability": "所需能力类型",
      "dependencies": ["依赖的其他子任务 id"],
      "priority": "high | medium | low",
      "description": "子任务的具体描述，说明需要调研/分析什么"
    }
  ],
  "required_adversary": true/false
}

## 能力类型（capability）可选值

- market_research：市场调研、用户需求分析、消费者洞察
- technical_analysis：技术可行性评估、架构分析、技术选型
- competitive_intelligence：竞品分析、行业格局、差异化定位
- financial_analysis：商业价值计算、成本收益分析、ROI 评估
- risk_analysis：风险评估、合规性分析、潜在障碍识别
- strategic_planning：战略规划、路线图制定、优先级排序
- data_analysis：数据分析、统计建模、趋势预测
- user_experience：用户体验研究、交互设计评估
- legal_compliance：法律合规、政策法规分析

## 分解规则

1. 子任务数量必须在 3-7 个之间
2. 每个子任务必须有明确的能力类型
3. 依赖关系必须合理——无依赖的任务可以并行执行
4. 优先级分配要合理——核心任务为 high，辅助任务为 medium/low
5. required_adversary 判断标准：
   - 涉及重大决策、投资判断、战略方向 → true
   - 涉及风险评估、可行性分析 → true
   - 纯信息收集、简单查询 → false
6. 确保子任务之间有足够的视角差异，避免重叠

只输出 JSON，不要输出任何其他内容。"""


async def decomposer_engine(state: HiveState) -> dict:
    """
    L1 Decomposer 引擎：解析用户目标，输出任务图谱。

    读取 state["goal"]，调用 MODEL_META 进行任务分解，
    返回更新后的 state 字段（task_graph + token_used）。
    """
    goal = state["goal"]

    messages = [
        {"role": "system", "content": DECOMPOSER_SYSTEM_PROMPT},
        {"role": "user", "content": f"请分解以下目标：\n\n{goal}"},
    ]

    result = await call_llm(
        model_env_key="MODEL_META",
        messages=messages,
        temperature=0.4,
        max_tokens=2000,
    )

    # 解析 LLM 返回的 JSON（兼容 markdown 包裹等情况）
    content = result["content"]
    task_graph = _extract_json(content)

    # 子任务数量校验：不足 3 个或超过 7 个时进行修正
    subtasks = task_graph.get("subtasks", [])
    if len(subtasks) < 3:
        task_graph = await _expand_subtasks(goal, task_graph)
    elif len(subtasks) > 7:
        task_graph = await _merge_subtasks(goal, task_graph)

    # 累计 token 消耗
    tokens_used = result["usage"].get("total_tokens", 0)

    return {
        "task_graph": task_graph,
        "token_used": state.get("token_used", 0) + tokens_used,
    }


async def _expand_subtasks(goal: str, task_graph: dict) -> dict:
    """子任务不足 3 个时，要求 LLM 补充更多维度"""
    messages = [
        {"role": "system", "content": DECOMPOSER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"目标：{goal}\n\n"
                f"当前分解结果只有 {len(task_graph.get('subtasks', []))} 个子任务，"
                "太少了。请重新分解，确保有 3-7 个子任务，"
                "覆盖更多分析维度。\n\n"
                f"当前结果：{json.dumps(task_graph, ensure_ascii=False)}\n\n"
                "请输出完整的新 JSON。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_META",
        messages=messages,
        temperature=0.5,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return _extract_json(result["content"])


async def _merge_subtasks(goal: str, task_graph: dict) -> dict:
    """子任务超过 7 个时，要求 LLM 合并相似项"""
    messages = [
        {"role": "system", "content": DECOMPOSER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"目标：{goal}\n\n"
                f"当前分解结果有 {len(task_graph.get('subtasks', []))} 个子任务，"
                "太多了。请合并相似的子任务，确保最终有 3-7 个。\n\n"
                f"当前结果：{json.dumps(task_graph, ensure_ascii=False)}\n\n"
                "请输出完整的新 JSON。"
            ),
        },
    ]

    result = await call_llm(
        model_env_key="MODEL_META",
        messages=messages,
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return _extract_json(result["content"])
