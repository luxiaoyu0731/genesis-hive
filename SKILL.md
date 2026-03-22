---
name: genesis-hive
description: |
  自进化多Agent智能体系统开发技能。触发场景：构建能从自然语言目标自动生成Agent团队的系统、
  实现多Agent圆桌辩论与共识机制、轮次间动态重组Agent团队结构、LangGraph Command动态路由、
  多Agent消息总线与协商协议设计、多视角交叉验证可视化。
  不用于：单Agent工具开发、简单的LLM调用链、静态Workflow编排、
  纯前端UI组件开发、非Agent类后端服务。
---

# Genesis Hive · 自进化多Agent智能体 — 全栈开发执行技能

## 核心目标

构建一个能从一句话目标自动生长出专业Agent团队、让团队通过多视角交叉验证产生高质量决策的系统。核心能力：Agent动态生成（不是预定义的）、异构多Agent圆桌辩论（不同模型+不同信息源+不同思维框架）、团队结构轮次间动态重组（辩论轮次间增减成员）。本质上是一个"能自组织、自进化的AI团队"。

### 关键设计原则（解决"同源LLM自说自话"问题）

为避免同一LLM扮演不同角色导致辩论退化为"自说自话"，系统采用三层认知多样性注入：

1. **模型异构**：不同Agent使用不同LLM底座（全部通过 OpenRouter 统一调用）
   - 调研型Agent → `openai/gpt-4o-mini`（速度优先，对应环境变量 MODEL_RESEARCH）
   - 分析型Agent → `anthropic/claude-sonnet-4`（深度推理优先，对应 MODEL_ANALYSIS）
   - 魔鬼代言人 → `google/gemini-2.0-flash-001`（制造认知差异，对应 MODEL_ADVERSARY）
   - 元决策Agent（Decomposer/Spawner/Evolver）→ `anthropic/claude-sonnet-4`（对应 MODEL_META）
   - 裁判LLM → `openai/gpt-4o`（独立第三方，对应 MODEL_JUDGE）
   - 学术依据：混合不同模型的Agent团队在推理准确率上比同模型团队高约10个百分点（GSM-8K benchmark, 2024）

2. **信息源隔离**：不同Agent在调研阶段使用不同搜索策略和信息源
   - 市场研究员 → 社交媒体、用户论坛、消费者调研
   - 技术顾问 → 技术博客、GitHub、学术论文
   - 竞品分析师 → 行业报告、竞品官网、产品评测

3. **思维框架差异**：在Agent的system prompt中嵌入不同的思维框架
   - 市场研究员 → Jobs-to-be-Done 框架
   - 技术顾问 → Gartner Hype Cycle（技术成熟度曲线）
   - 财务分析师 → Unit Economics（单位经济模型）
   - 魔鬼代言人 → Pre-mortem Analysis（预验尸法）

五层进化引擎架构：
- **L1 Decomposer（解构引擎）**：意图解析、任务分解、能力维度识别，输出任务图谱
- **L2 Spawner（孕育引擎）**：动态创建Agent——生成角色、prompt、工具集、模型配置
- **L3 Executor（执行引擎）**：并行执行各Agent的独立任务，收集初步结果
- **L4 Council（圆桌引擎）**：多Agent辩论、质疑、补充、投票、达成共识
- **L5 Evolver（进化引擎）**：动态重组团队结构，增减成员，调整策略

## 分步工作流

### Step 1：项目初始化与基础架构

1. 初始化项目结构：
   ```
   genesis-hive/
   ├── backend/
   │   ├── engines/              # 五层引擎实现
   │   │   ├── decomposer.py     # L1 任务分解
   │   │   ├── spawner.py        # L2 Agent动态生成
   │   │   ├── executor.py       # L3 并行执行
   │   │   ├── council.py        # L4 圆桌辩论
   │   │   └── evolver.py        # L5 动态重组
   │   ├── core/
   │   │   ├── llm_service.py    # 多模型LLM调用服务
   │   │   ├── message_bus.py    # Agent间消息总线
   │   │   ├── consensus.py      # 共识检测算法
   │   │   ├── agent_factory.py  # Agent配置生成与实例化
   │   │   └── tool_pool.py      # 可用工具池管理
   │   ├── tools/                # 工具实现
   │   │   ├── web_search.py
   │   │   ├── browser.py
   │   │   └── code_executor.py
   │   ├── api/
   │   │   ├── routes.py         # FastAPI路由
   │   │   └── websocket.py      # WebSocket实时推送
   │   └── main.py
   ├── frontend/
   │   ├── src/
   │   │   ├── components/
   │   │   │   ├── GrowthAnimation.tsx   # Agent生长动画
   │   │   │   ├── ExecutionBoard.tsx     # 并行执行看板
   │   │   │   ├── CouncilRoom.tsx        # 圆桌辩论室
   │   │   │   ├── EvolutionView.tsx      # 团队进化视图
   │   │   │   ├── FinalReport.tsx        # 最终报告
   │   │   │   └── TeamTopology.tsx       # 团队拓扑图（D3.js）
   │   │   ├── pages/
   │   │   └── App.tsx
   │   └── package.json
   ├── templates/               # Agent配置模板（可选，用于加速生成）
   └── cases/                   # 已完成的案例存档
   ```

2. 安装核心依赖：
   - 后端：`fastapi`, `uvicorn`, `langgraph`, `langchain-core`, `openai`, `python-dotenv`, `playwright`（可选浏览器工具）
   - 前端：`react`, `typescript`, `tailwindcss`, `d3`, `framer-motion`

3. 配置环境变量：
   - 从 `.env.example` 复制为 `.env`，填入 OpenRouter API Key
   - `.env` 已加入 `.gitignore`，不会被提交

4. 配置多模型LLM服务（`llm_service.py`）——统一走 OpenRouter 网关：
   - 所有模型调用统一使用 OpenAI 兼容接口，base_url 指向 `OPENROUTER_BASE_URL`
   - 从 `.env` 读取模型 ID 映射：
     - `MODEL_RESEARCH`（调研型Agent）→ `openai/gpt-4o-mini`，速度优先
     - `MODEL_ANALYSIS`（分析/辩论型Agent）→ `anthropic/claude-sonnet-4`，质量优先
     - `MODEL_ADVERSARY`（魔鬼代言人）→ `google/gemini-2.0-flash-001`，制造认知差异
     - `MODEL_META`（Decomposer/Spawner/Evolver元决策）→ `anthropic/claude-sonnet-4`
     - `MODEL_JUDGE`（裁判LLM）→ `openai/gpt-4o`，独立于辩论的第三方
     - `MODEL_COMPRESS`（辩论摘要压缩）→ `openai/gpt-4o-mini`，轻量够用
   - 核心实现模式：
     ```python
     from openai import AsyncOpenAI
     from dotenv import load_dotenv
     import os

     load_dotenv()

     client = AsyncOpenAI(
         api_key=os.getenv("OPENROUTER_API_KEY"),
         base_url=os.getenv("OPENROUTER_BASE_URL"),
     )

     async def call_llm(model_env_key: str, messages: list, **kwargs) -> str:
         model = os.getenv(model_env_key)
         response = await client.chat.completions.create(
             model=model,
             messages=messages,
             **kwargs
         )
         return response.choices[0].message.content
     ```

### Step 2：L1 Decomposer — 任务分解引擎

1. **接收用户的自然语言目标**（如"分析小红书做AI搜索的可行性"）

2. **意图解析**：用LLM识别目标的类型、领域、复杂度

3. **任务分解**：将目标拆解为子任务图谱
   ```json
   {
     "goal": "分析小红书做AI搜索的可行性",
     "subtasks": [
       {
         "id": "market_research",
         "name": "用户需求调研",
         "capability": "market_research",
         "dependencies": [],
         "priority": "high"
       },
       {
         "id": "tech_assessment",
         "name": "技术可行性评估",
         "capability": "technical_analysis",
         "dependencies": [],
         "priority": "high"
       },
       {
         "id": "competitor_analysis",
         "name": "竞品分析",
         "capability": "competitive_intelligence",
         "dependencies": [],
         "priority": "medium"
       },
       {
         "id": "business_value",
         "name": "商业价值计算",
         "capability": "financial_analysis",
         "dependencies": ["market_research"],
         "priority": "medium"
       },
       {
         "id": "risk_assessment",
         "name": "风险评估",
         "capability": "risk_analysis",
         "dependencies": ["tech_assessment", "competitor_analysis"],
         "priority": "high"
       }
     ],
     "required_adversary": true
   }
   ```

4. **能力维度识别**：分析每个子任务需要的能力类型，用于Spawner生成对应Agent

### Step 3：L2 Spawner — Agent动态生成引擎（Genesis核心）

这是整个系统最核心的技术突破——Agent不是预定义的，而是现场生成的：

1. **接收Decomposer的任务图谱和能力需求**

2. **为每个能力维度动态生成一个Agent配置**（JSON Schema约束输出格式）：
   ```json
   {
     "agent_id": "market_researcher_01",
     "role": "市场研究员",
     "personality": "数据驱动、注重用户声音、善于发现趋势",
     "system_prompt": "你是一位专注于消费者洞察的市场研究员。你的工作方式是：先收集数据，再提炼洞察，最后给出可操作的结论。你不接受没有数据支撑的观点。",
     "tools": ["web_search", "social_media_scraper"],
     "model_env_key": "MODEL_RESEARCH",
     "debate_style": "客观严谨，质疑时会要求数据支撑",
     "max_tokens_per_turn": 2000
   }
   ```

3. **内置对抗机制**：总会生成一个"魔鬼代言人"Agent，专门站在反面找漏洞

4. **配置可序列化**：好的团队配置可保存为"模板"，下次同类任务直接复用

5. **工具分配逻辑**：从tool_pool中根据能力需求自动匹配工具组合
   - market_research → ["web_search", "social_media_scraper"]
   - technical_analysis → ["web_search", "code_executor"]
   - competitive_intelligence → ["web_search", "browser"]
   - financial_analysis → ["web_search", "code_executor"]（计算用）

### Step 4：L3 Executor — 并行执行引擎

1. **实例化所有Agent**：根据Spawner的配置创建Agent实例

2. **并行执行（asyncio协程并发）**：各Agent独立完成自己的子任务
   - 使用`asyncio.gather()`实现IO密集型任务的协程并发（LLM API调用和网络搜索均为IO操作，asyncio是Python最优解）
   - 尊重依赖关系：有依赖的子任务`await`前置任务完成
   - 无依赖的子任务通过`gather`同时并发执行
   - 每个Agent独立调用自己的工具和LLM
   - 支持**增量执行模式**：进化重组后，仅执行新增/变更的Agent，未变更Agent复用上轮结果（通过对比`agent_configs`的hash判断是否变更）

3. **执行日志记录**：
   ```json
   {
     "agent_id": "market_researcher_01",
     "actions": [
       { "type": "web_search", "query": "小红书用户搜索习惯", "result_summary": "..." },
       { "type": "web_search", "query": "小红书搜索功能用户反馈", "result_summary": "..." },
       { "type": "analysis", "content": "基于搜索结果的初步分析..." }
     ],
     "preliminary_result": "用户对小红书搜索有明确需求但当前体验差...",
     "confidence": 0.78,
     "tokens_used": 3500,
     "time_ms": 12000
   }
   ```

4. **实时状态推送**：通过WebSocket向前端推送每个Agent的工作进度

### Step 5：L4 Council — 圆桌辩论引擎（Hive核心）

多个Agent之间如何协作是整个项目的第二个技术突破：

1. **Phase A 独立呈述**：每个Agent展示自己的初步结果，其他Agent只看不说

2. **Phase B 圆桌辩论**：
   - 每个Agent可以对其他Agent的结论发表意见
   - 发言类型标签：`质疑`、`支持`、`反驳`、`补充`、`提问`
   - 消息格式：
     ```json
     {
       "from": "devil_advocate_01",
       "to": "tech_consultant_01",
       "type": "反驳",
       "content": "你说用RAG就能解决，但小红书是图文内容为主，纯文本RAG不够。你考虑过多模态检索的成本和延迟吗？",
       "references": ["tech_consultant_01.preliminary_result.paragraph_2"]
     }
     ```
   - 辩论轮次由Council引擎控制，每轮每个Agent最多发言一次

3. **Phase C 修正更新**：基于辩论反馈，每个Agent修正自己的初步结果

4. **Phase D 共识检测（裁判LLM方案，非语义相似度）**：
   - 先要求每个Agent将结论结构化提取为JSON：
     ```json
     {
       "conclusion": "可行/不可行/有条件可行",
       "confidence": 0.85,
       "key_reasons": ["原因1", "原因2"],
       "conditions": ["前提条件1"],
       "risks": ["风险1"]
     }
     ```
   - 用独立的裁判LLM（不参与辩论的第三方模型）阅读所有结构化结论，判断：
     - 核心立场是否一致
     - 分歧主要在哪些维度
     - 继续辩论的边际价值
   - 裁判输出：`consensus_reached` + `consensus_type`（full/partial/none）+ `recommendation`
   - 完全共识 → 进入整合阶段
   - 部分共识 → 再进行一轮辩论（最多3轮）
   - 3轮后仍有分歧 → 在报告中同时呈现共识部分和分歧部分（比强行统一更诚实）
   - 注意：**不使用语义相似度/cosine similarity**，因为它无法区分"讨论同一话题"和"得出相同结论"

5. **辩论历史摘要压缩（进入下一轮前必做）**：
   - 每轮辩论结束后、进入下一轮之前，用轻量模型（GPT-4o-mini）将本轮完整辩论记录压缩为结构化摘要
   - 摘要格式：每个Agent的核心论点（≤100字）+ 主要分歧点 + 已达成的共识点
   - 下一轮辩论的Agent只接收摘要而非原文，减少60-70% input tokens
   - 完整辩论原文保留在`debate_history_full`中用于最终报告，但不传入后续LLM调用

6. **共识整合**：由一个临时的Synthesizer Agent整合所有观点，生成最终报告

### Step 6：L5 Evolver — 动态重组引擎（融合的核心）

这是Genesis+Hive融合后独有的能力——团队结构不是固定的，而是活的：

1. **能力缺口触发**：
   - 辩论中发现某个角度无人覆盖（如"内容合规""数据隐私"）
   - Evolver检测到关键词/议题未被任何Agent的专业领域覆盖
   - 自动调用Spawner生成新Agent加入团队，重新进入辩论

2. **低贡献检测（量化标准）**：
   - 裁判LLM在共识评估时同时输出每个Agent的`contribution_score`，基于以下三个可量化指标：
     - **被引用次数**：该Agent的观点被其他Agent在发言中引用的次数（从消息总线的`references`字段统计）
     - **结论变更影响**：其他Agent在Phase C修正阶段是否因该Agent的观点而修改了自己的结论
     - **信息增量**：该Agent是否提供了其他Agent未覆盖的独立信息源（对比各Agent的搜索查询和引用来源）
   - 连续2轮`contribution_score < 0.2`（满分1.0）且被引用次数为0的Agent被标记为低贡献
   - 自动退场释放资源（token预算），退场原因记入evolution_log

3. **任务分裂**：
   - 辩论中发现的新子问题太大，超出现有Agent能力范围
   - 生成专项Agent并重新编排任务依赖关系

4. **进化次数上限**：最多进行 **2次进化重组**（`max_evolution_cycles: 2`）。超过后即使仍有能力缺口，也直接进入synthesizer并在报告中标注未覆盖的维度。理由：每次进化都触发重新执行，2次已足够补充关键缺口，再多则成本失控

5. **重组日志**：每次团队变化都记录原因和决策依据，用于最终报告的"决策路径"展示

### Step 7：前端可视化界面（视觉震撼核心）

1. **Agent生长动画（GrowthAnimation.tsx）**：
   - 用户输入目标后，Agent像细胞分裂一样一个个"诞生"
   - 每个节点从Decomposer中弹出，带着角色名和工具图标
   - 使用framer-motion做弹出和连线动画
   - D3.js force-directed layout自动排布节点位置

2. **并行执行看板（ExecutionBoard.tsx）**：
   - 各Agent同时工作，实时滚动显示工作日志
   - 类CI/CD的进度条，看到每个Agent的完成进度
   - 颜色编码：思考中=蓝色、搜索中=绿色、分析中=紫色、完成=灰色

3. **圆桌辩论室（CouncilRoom.tsx）**：
   - 左侧圆形布局的Agent头像，正在发言的Agent高亮
   - 右侧实时对话流，每条发言标注"质疑""支持""反驳""补充"标签
   - 发言类型用不同颜色标识（质疑=红、支持=绿、反驳=橙、补充=蓝）
   - 魔鬼代言人发起强烈反驳时边框闪红——视觉戏剧性

4. **团队进化视图（EvolutionView.tsx）**：
   - 新Agent加入时，节点从边缘"飞入"圆桌，带入场动画
   - Agent退场时节点淡出并显示"任务完成，已退场"
   - 轮次计数器和共识度进度条
   - 团队拓扑图实时变化

5. **最终报告（FinalReport.tsx）**：
   - 核心结论 + 信心度评分
   - 各Agent观点汇总（包含分歧记录）
   - 完整决策路径："为什么得出这个结论"的推理链
   - Token消耗和成本统计

### Step 8：LangGraph编排（轮次间重编译方案）

**重要：LangGraph不支持编译后添加节点。** 图结构在`compile()`时静态确定。因此Evolver的"动态重组"采用"轮次间重编译"方案：每轮辩论结束后，如需重组团队，重新构建并编译新图。重编译耗时毫秒级，用户无感知。

1. **图构建函数（每轮可能重新调用）**：
   ```python
   from langgraph.graph import StateGraph, END
   from langgraph.types import Command
   from typing import Literal

   def build_hive_graph(agent_configs: list[dict]) -> CompiledGraph:
       graph = StateGraph(HiveState)

       # 固定节点
       graph.add_node("decomposer", decomposer_engine)
       graph.add_node("spawner", spawner_engine)
       graph.add_node("executor", build_executor(agent_configs))  # 根据当前配置构建
       graph.add_node("council", council_engine)
       graph.add_node("evolver", evolver_engine)
       graph.add_node("synthesizer", synthesizer_engine)

       graph.add_edge("decomposer", "spawner")
       graph.add_edge("spawner", "executor")
       graph.add_edge("executor", "council")
       # council用Command做动态路由，不需要预定义条件边
       graph.add_edge("evolver", "spawner")  # 重组后重新生成 → 重新执行
       graph.set_entry_point("decomposer")
       graph.set_finish_point("synthesizer")
       return graph.compile()
   ```

2. **Council节点用Command做动态路由**（LangGraph Command API的正确用法）：
   ```python
   def council_engine(state: HiveState) -> Command[Literal["synthesizer", "evolver", "council"]]:
       # 用裁判LLM判断共识（不用语义相似度）
       consensus = judge_llm_check_consensus(
           state["agent_results"],
           state["debate_history"]
       )

       # 压缩本轮辩论历史为摘要（传入下一轮用）
       round_summary = compress_debate_history(state["debate_history_full"][-1])

       if consensus["consensus_reached"]:
           return Command(goto="synthesizer", update={"consensus_report": consensus})
       elif state["debate_round"] >= 3 or state["token_used"] > state["token_budget"] * 0.9:
           return Command(goto="synthesizer", update={"forced_consensus": True})
       elif consensus["capability_gap_detected"] and state["evolution_cycle"] < 2:
           return Command(goto="evolver", update={
               "gaps": consensus["gaps"],
               "evolution_cycle": state["evolution_cycle"] + 1,
               "debate_history": state["debate_history"] + [round_summary]
           })
       elif consensus["capability_gap_detected"] and state["evolution_cycle"] >= 2:
           # 进化次数已达上限，强制整合并标注未覆盖维度
           return Command(goto="synthesizer", update={
               "forced_consensus": True,
               "uncovered_gaps": consensus["gaps"]
           })
       else:
           # 继续辩论：传入压缩后的摘要而非完整历史
           return Command(goto="council", update={
               "debate_round": state["debate_round"] + 1,
               "debate_history": state["debate_history"] + [round_summary]
           })
   ```

3. **Evolver节点：修改配置，触发重编译**：
   ```python
   def evolver_engine(state: HiveState) -> Command[Literal["spawner"]]:
       # 生成新Agent配置补充能力缺口
       new_configs = spawn_for_gaps(state["gaps"])
       # 移除低贡献Agent
       pruned = prune_low_contribution(state["agent_configs"], state["debate_history"])
       updated = pruned + new_configs

       return Command(goto="spawner", update={
           "agent_configs": updated,
           "evolution_log": state["evolution_log"] + [{
               "round": state["debate_round"],
               "added": [c["agent_id"] for c in new_configs],
               "removed": [c["agent_id"] for c in state["agent_configs"] if c not in pruned],
               "reason": state["gaps"]
           }]
       })
   ```
   注意：Evolver输出后回到Spawner，Spawner会基于更新后的`agent_configs`重新实例化Agent，这在逻辑上等价于"团队重组"。

4. **状态对象设计**：
   ```python
   class HiveState(TypedDict):
       goal: str                              # 用户目标
       task_graph: dict                       # Decomposer输出的任务图谱
       agent_configs: list[dict]              # Spawner生成的Agent配置列表
       agent_configs_hash: dict[str, str]     # 各Agent配置的hash（用于增量执行判断）
       agent_results: dict[str, dict]         # 各Agent的执行结果
       debate_history: list[dict]             # 辩论摘要（压缩后，传入LLM用）
       debate_history_full: list[dict]        # 完整辩论原文（仅用于最终报告，不传入LLM）
       debate_round: int                      # 当前辩论轮次
       evolution_cycle: int                   # 当前进化轮次（上限2）
       consensus_report: dict                 # 裁判LLM的共识评估
       evolution_log: list[dict]              # 团队重组日志
       final_report: dict                     # 最终报告
       token_budget: int                      # 总token预算
       token_used: int                        # 已使用token
   ```

5. **关键流程控制**：
   - 共识达成 → `Command(goto="synthesizer")`
   - 未共识且轮次<3 → `Command(goto="council")` 继续辩论
   - 发现能力缺口 → `Command(goto="evolver")` 重组团队
   - Token预算耗尽 → 强制进入synthesizer，输出当前最佳结果

## 执行规则

- Agent配置 ALWAYS 通过 Spawner 动态生成，NEVER 硬编码Agent定义
- 辩论发言 ALWAYS 标注类型标签（质疑/支持/反驳/补充/提问）
- 共识检测 ALWAYS 基于裁判LLM结构化判定，NEVER 使用语义相似度（无法区分同话题和同结论），NEVER 简单多数投票
- 每个Agent ALWAYS 有独立的token预算，防止单Agent消耗过多资源
- 魔鬼代言人 ALWAYS 存在于团队中，确保结论经得起质疑
- LLM调用 ALWAYS 记录 token 消耗和耗时，用于成本监控
- 团队重组 ALWAYS 记录原因和决策依据，确保可追溯
- 前端状态 ALWAYS 通过 WebSocket 实时推送，NEVER 轮询
- Agent退场 ALWAYS 有明确的退场原因记录
- API Key NEVER 写入日志或报告
- 辩论最多进行3轮，超过后 ALWAYS 进入强制共识阶段
- 进化重组最多进行2次（`max_evolution_cycles: 2`），超过后 ALWAYS 直接进入synthesizer
- 辩论历史进入下一轮前 ALWAYS 先压缩为摘要，完整原文仅存入`debate_history_full`
- Executor进化后 ALWAYS 使用增量执行（对比config hash），NEVER 重新执行未变更的Agent
- 低贡献检测 ALWAYS 基于量化指标（被引用次数+结论变更影响+信息增量），NEVER 仅靠主观判断

## 消息总线协议

Agent间通信遵循统一的消息格式：

```json
{
  "message_id": "msg_001",
  "from": "agent_id",
  "to": "agent_id | broadcast",
  "type": "preliminary_result | challenge | support | rebuttal | supplement | question | revision",
  "content": "消息正文",
  "references": ["被引用的消息ID或Agent结果段落"],
  "confidence": 0.85,
  "timestamp": "ISO8601"
}
```

## 技术栈速查

| 模块 | 技术选型 | 选择理由 |
|------|---------|---------|
| Agent编排 | LangGraph + Command API | Command实现动态路由，轮次间重编译实现团队重组（不支持运行时添加节点） |
| Agent生成 | LLM + JSON Schema | LLM生成结构化Agent配置，Schema约束输出格式 |
| LLM服务 | OpenRouter 多模型网关 | 统一 API 入口，通过环境变量配置模型映射，AsyncOpenAI 客户端调用 |
| 工具库 | Web搜索 + 浏览器 + 代码执行 | Spawner从pool中按能力自动分配 |
| 协商引擎 | 消息总线 + 轮次管理器 | 统一消息格式，Agent通过总线交换观点 |
| 共识检测 | 裁判LLM（结构化提取+第三方判定） | 独立裁判模型判断立场一致性，避免语义相似度的"同话题≠同结论"陷阱 |
| 前端界面 | React + TypeScript + D3.js | 实时可视化Agent生长、辩论、进化 |
| 后端 | Python + FastAPI + WebSocket | 复用已有技术栈，WebSocket推送实时状态 |
| 动画 | framer-motion | Agent生长/入场/退场动画 |

## Token成本控制策略

每次完整运行（L1→L5）预估成本约$0.50-0.70（标准模式）。成本主要集中在Council辩论阶段。

**三个控制手段：**
1. **辩论摘要压缩**：每轮辩论结束后，用轻量模型将辩论历史压缩为摘要传入下一轮，减少60-70% input tokens
2. **动态轮次裁剪**：裁判LLM判断"继续辩论的边际价值"，两轮后观点变化极小则提前终止
3. **分级模式**：
   - Demo模式：3 Agent / 1轮辩论 / 轻量模型 → ~$0.10/次（面试演示用）
   - Standard模式：5 Agent / 2轮辩论 / 混合模型 → ~$0.50/次
   - Deep模式：7 Agent / 3轮辩论 / 强模型 → ~$1.50/次

## 已知风险登记簿与迭代改进机制

本项目涉及多Agent动态编排、多模型异构调用、实时辩论共识等复杂交互，潜在风险不可能一次性穷举。以下建立系统化的风险管理流程。

### 已识别并修复的风险（Risk Log）

| ID | 风险描述 | 严重度 | 修复方案 | 状态 |
|----|---------|--------|---------|------|
| R01 | 同源LLM辩论退化为"自说自话" | 高 | 三层认知多样性注入（模型异构+信息源隔离+思维框架差异） | ✅已修复 |
| R02 | 语义相似度无法区分"同话题"和"同结论" | 高 | 替换为裁判LLM结构化判定 | ✅已修复 |
| R03 | LangGraph不支持运行时添加节点 | 高 | 降级为轮次间重编译方案 | ✅已修复 |
| R04 | Token成本失控 | 中 | 辩论摘要压缩+动态轮次裁剪+分级模式 | ✅已修复 |
| R05 | 技术栈表与Step 8描述矛盾 | 低 | 统一为"不支持运行时添加节点" | ✅已修复 |
| R06 | Executor并行机制未明确 | 中 | 明确asyncio.gather协程并发+增量执行 | ✅已修复 |
| R07 | Evolver进化循环无上限 | 高 | 新增max_evolution_cycles: 2 | ✅已修复 |
| R08 | 辩论摘要压缩未落地到工作流 | 中 | Step 5新增压缩步骤，Council代码加入compress调用 | ✅已修复 |
| R09 | 进化后全量重执行浪费 | 中 | 增量执行模式（config hash对比） | ✅已修复 |
| R10 | "低贡献"定义模糊 | 中 | 量化为三指标：被引用次数+结论变更影响+信息增量 | ✅已修复 |

### 待观察的潜在风险（开发中持续关注）

| ID | 风险描述 | 触发条件 | 预防思路 | 优先级 |
|----|---------|---------|---------|--------|
| W01 | Spawner生成的Agent prompt质量不稳定 | 复杂/模糊目标输入时 | 加入prompt质量自检（让另一个LLM评分），低分则重新生成；积累高质量模板库 | 高 |
| W02 | 多模型API调用的延迟差异导致执行瓶颈 | DeepSeek/Gemini响应慢时 | 为每个Agent设置独立超时（如30s），超时后用备选模型重试；Executor层面用asyncio.wait配合FIRST_COMPLETED策略 | 中 |
| W03 | 裁判LLM本身的判断偏差 | 裁判模型对特定领域理解不足时 | 裁判输出confidence字段，低置信度时标注"需人工复核"；可配置裁判模型 | 中 |
| W04 | WebSocket推送在大量Agent并行时造成前端卡顿 | Agent数量>7且同时活跃时 | 前端消息节流（throttle 100ms），非活跃Agent的日志折叠，只推送diff不推全量 | 低 |
| W05 | Agent间辩论出现"回声室效应"——少数强势Agent主导讨论 | 强模型Agent观点被其他Agent无条件接受时 | 裁判LLM额外检测"观点多样性指数"——如果所有Agent修正后都趋同于同一个Agent的原始观点，触发警告 | 中 |
| W06 | Decomposer对任务粒度拆解不当（太粗或太细） | 极简目标（"分析AI"）或极长目标时 | 加入粒度校验：子任务数3-7个，少于3个则提示用户补充细节，多于7个则合并相似项 | 中 |
| W07 | 多模型API Key管理和计费分摊复杂度 | 用户需要配置多个不同提供商的API Key | 提供统一的API配置界面；支持OpenRouter等聚合网关作为单一入口；Demo模式只需一个Key | 低 |
| W08 | 辩论摘要压缩丢失关键信息 | 压缩模型对专业领域术语理解不足时 | 压缩后自动验证：对比压缩前后的关键实体列表（NER），实体丢失率>10%则用原文替代摘要 | 中 |
| W09 | Demo模式Token预算溢出（实测112-118%利用率） | 3个Agent + 1轮辩论的最小配置下，LLM实际输出超预期 | 将Demo预算从30k提升至40k，或在各Phase增加更严格的max_tokens限制；考虑流式输出提前截断 | 中 |
| W10 | ~~`_extract_json` 重复定义在多个引擎文件中~~ | ~~任何一处修复JSON提取逻辑时需同步修改5个文件~~ | 已统一提取到 `backend/core/utils.py`，提供 `extract_json`（抛异常）和 `extract_json_safe`（返回默认值）两个版本，各引擎 import 引用 | ✅已修复 |
| W11 | ~~Spawner并发生成时魔鬼代言人缺少existing_roles上下文~~ | ~~并发改造后adversary_spawn与常规Agent同时启动~~ | 改为 two-phase 并发：Phase 1 所有常规Agent并发生成，Phase 2 魔鬼代言人拿到完整 existing_configs 上下文后生成 | ✅已修复 |
| W12 | ~~Claude Sonnet（MODEL_ANALYSIS）单次调用延迟约20s，是Executor瓶颈~~ | ~~分析型Agent使用Claude Sonnet作为底座时~~ | Executor 增加模型级别超时（MODEL_ANALYSIS=30s）+ FALLBACK_MODEL=MODEL_RESEARCH 自动降级；依赖等待加 60s 死锁防护 | ✅已修复 |

### 开发阶段自检流程（每完成一个Step后执行）

每完成一个引擎（L1-L5）的开发后，必须执行以下自检：

1. **边界条件测试**：用极端输入测试该引擎
   - 空输入/超长输入/非中文输入
   - 单个子任务/超多子任务（>10个）
   - API调用失败/超时的情况

2. **状态一致性检查**：验证该引擎修改的state字段
   - 是否所有新增字段都有初始值？
   - 是否有字段被意外覆盖而非追加？
   - TypedDict中的类型标注是否与实际数据一致？

3. **循环与终止检查**：验证该引擎涉及的所有循环路径
   - 是否每条循环路径都有明确的终止条件？
   - 终止条件是否可达（不存在死锁）？
   - 最坏情况下的循环次数是多少？成本是多少？

4. **上下游接口检查**：验证与前后引擎的数据交接
   - 上游输出的数据格式是否匹配本引擎的输入预期？
   - 本引擎的输出是否满足下游的输入Schema？
   - 缺失字段时是否有合理的默认值或错误处理？

5. **成本审计**：记录该引擎单独运行一次的token消耗和API调用次数
   - 是否在预期范围内？
   - 有没有意外的重复调用？

6. **风险登记簿更新**：
   - 开发过程中发现的新风险 → 追加到上方表格
   - 已修复的风险 → 标记状态为✅
   - 调整优先级：接近开发的风险提升优先级

### 面试答辩准备：高频追问与应对

面试官可能沿以下方向深挖，提前准备应对：

1. **"多Agent辩论和单Agent多轮自我反思有什么区别？"**
   → 关键差异：不同模型+不同信息源+不同思维框架产生真正的认知差异，单Agent无论多少轮都是同一个知识边界内的自我修正。引用GSM-8K论文数据（91% vs 82%）

2. **"LangGraph重编译的性能开销？"**
   → 编译本身是Python对象构建，毫秒级。真正的开销在Agent重新执行，这就是为什么要做增量执行

3. **"如果所有Agent都用同一个API Provider，认知多样性从哪来？"**
   → 模型异构只是三层之一。即使极端情况下只有一个Provider，信息源隔离和思维框架差异仍然有效。但推荐至少2个不同Provider

4. **"这个项目和AutoGen/CrewAI有什么区别？"**
   → AutoGen/CrewAI是预定义角色+固定流程；Genesis Hive的核心区别是：(a) Agent从目标现场生成而非预定义 (b) 团队结构在辩论中动态进化 (c) 异构模型注入真正的认知多样性

5. **"裁判LLM不也是一个LLM吗？它的判断就一定可靠？"**
   → 不一定可靠，所以裁判输出confidence字段。但比语义相似度可靠得多——裁判至少能理解语义，而cosine similarity只是数学距离。这是"更优解"而非"完美解"，报告中保留分歧记录就是对不确定性的诚实处理

6. **"Demo模式3个Agent 1轮辩论，还有辩论的意义吗？"**
   → Demo模式的目标是2分钟内展示完整流程，证明架构可跑通。辩论价值在Standard/Deep模式中体现。面试时可以先跑Demo展示流程，再用预录的Standard案例展示辩论质量

## 质量检查清单

- [ ] Decomposer能将自然语言目标正确分解为3-7个子任务
- [ ] Spawner生成的Agent配置包含完整的角色/prompt/工具/模型信息
- [ ] 生成的Agent团队中始终包含一个"魔鬼代言人"角色
- [ ] 多Agent可正确并行执行各自任务，无资源冲突
- [ ] 圆桌辩论中Agent能针对性回应其他Agent的观点（不是自说自话）
- [ ] 裁判LLM能正确区分"讨论同一话题"和"得出相同结论"（准备10组测试用例验证）
- [ ] 不同模型的Agent确实产生了有意义的认知差异（对比同模型 vs 异构模型的辩论输出质量）
- [ ] Evolver能检测到能力缺口并自动生成新Agent补充
- [ ] 低贡献Agent能被正确识别并退场
- [ ] 前端Agent生长动画流畅，延迟不超过2秒
- [ ] 圆桌辩论室实时显示对话流，发言类型标签正确
- [ ] 完整的L1→L5流程能在5分钟内跑完一个中等复杂度任务
- [ ] Token预算控制有效，不会出现单Agent耗尽全部预算
- [ ] 面试演示版本能在2分钟内展示完整的"生长→执行→辩论→进化→共识"流程
- [ ] 最终报告包含完整的决策路径和分歧记录
- [ ] Executor并行使用asyncio.gather实现，且进化后仅增量执行变更的Agent
- [ ] 辩论摘要压缩后token量确实减少60%以上（对比压缩前后的token数）
- [ ] 进化次数上限（2次）正确触发，不会出现无限进化循环
- [ ] 低贡献检测的三个量化指标（引用次数/结论影响/信息增量）能正确计算
- [ ] debate_history_full保留完整原文，debate_history仅含压缩摘要
