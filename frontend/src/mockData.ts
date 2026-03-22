// Mock 数据 — 驱动所有前端组件的静态演示数据

export interface AgentConfig {
  agent_id: string;
  role: string;
  personality: string;
  model_env_key: string;
  capability: string;
  framework: string;
  tools: string[];
  debate_style: string;
}

export interface DebateMessage {
  message_id: string;
  from_agent: string;
  to_agent: string;
  type: "preliminary_result" | "challenge" | "support" | "rebuttal" | "supplement" | "question" | "revision";
  content: string;
  references: string[];
  confidence: number;
  timestamp: string;
}

export interface AgentResult {
  agent_id: string;
  status: "idle" | "thinking" | "searching" | "analyzing" | "done";
  progress: number;
  preliminary_result: string;
  confidence: number;
  tokens_used: number;
  time_ms: number;
  actions: { type: string; content: string }[];
}

export interface EvolutionEntry {
  cycle: number;
  debate_round: number;
  action: string;
  added: string[];
  removed: string[];
  reason: { capability_gaps?: string[]; low_contribution_agents?: { agent_id: string; score: number; reason: string }[] };
  team_size_before: number;
  team_size_after: number;
}

export interface ConsensusReport {
  consensus_reached: boolean;
  consensus_type: "full" | "partial" | "none";
  core_position: string;
  agreement_points: string[];
  disagreement_points: string[];
}

export interface FinalReportData {
  title: string;
  executive_summary: string;
  conclusion: string;
  confidence: number;
  key_findings: { topic: string; content: string; source_agents: string[] }[];
  consensus_points: string[];
  disagreement_points: string[];
  risks: { risk: string; severity: string; mitigation: string }[];
  recommendations: string[];
  debate_rounds: number;
  evolution_cycles: number;
  token_cost: { total: number };
  forced_consensus: boolean;
}

// 模型颜色映射
export const MODEL_COLORS: Record<string, string> = {
  MODEL_RESEARCH: "#22c55e",   // 绿 GPT-4o-mini
  MODEL_ANALYSIS: "#6366f1",   // 靛蓝 Claude Sonnet
  MODEL_ADVERSARY: "#ef4444",  // 红 Gemini
  MODEL_META: "#a855f7",       // 紫 Claude Sonnet
  MODEL_JUDGE: "#f97316",      // 橙 GPT-4o
  MODEL_COMPRESS: "#06b6d4",   // 青 GPT-4o-mini
};

export const MODEL_LABELS: Record<string, string> = {
  MODEL_RESEARCH: "GPT-4o-mini",
  MODEL_ANALYSIS: "Claude Sonnet",
  MODEL_ADVERSARY: "Gemini Flash",
  MODEL_META: "Claude Sonnet",
  MODEL_JUDGE: "GPT-4o",
  MODEL_COMPRESS: "GPT-4o-mini",
};

// 发言类型 → 颜色 + 中文标签
export const MSG_TYPE_META: Record<string, { color: string; label: string }> = {
  preliminary_result: { color: "#8888a0", label: "呈述" },
  challenge: { color: "#ef4444", label: "质疑" },
  support: { color: "#22c55e", label: "支持" },
  rebuttal: { color: "#f97316", label: "反驳" },
  supplement: { color: "#3b82f6", label: "补充" },
  question: { color: "#a855f7", label: "提问" },
  revision: { color: "#06b6d4", label: "修正" },
};

export const MOCK_AGENTS: AgentConfig[] = [
  {
    agent_id: "market_researcher_01",
    role: "市场研究员",
    personality: "数据驱动，注重用户声音",
    model_env_key: "MODEL_RESEARCH",
    capability: "market_research",
    framework: "Jobs-to-be-Done",
    tools: ["web_search", "social_media_scraper"],
    debate_style: "客观严谨，质疑时要求数据支撑",
  },
  {
    agent_id: "tech_architect_01",
    role: "技术架构师",
    personality: "严谨务实，对技术炒作保持冷静",
    model_env_key: "MODEL_ANALYSIS",
    capability: "technical_analysis",
    framework: "Gartner Hype Cycle",
    tools: ["web_search", "code_executor"],
    debate_style: "以技术数据和案例质疑过度乐观",
  },
  {
    agent_id: "competitive_analyst_01",
    role: "竞品分析师",
    personality: "敏锐洞察，善于发现差异",
    model_env_key: "MODEL_RESEARCH",
    capability: "competitive_intelligence",
    framework: "Porter's Five Forces",
    tools: ["web_search", "browser"],
    debate_style: "用对比分析揭示盲区",
  },
  {
    agent_id: "business_analyst_01",
    role: "商业分析师",
    personality: "数字说话，不接受模糊结论",
    model_env_key: "MODEL_ANALYSIS",
    capability: "financial_analysis",
    framework: "Unit Economics",
    tools: ["web_search", "code_executor"],
    debate_style: "用冷酷的数字质疑美好愿景",
  },
  {
    agent_id: "risk_analyst_01",
    role: "风险评估师",
    personality: "警觉细致，强预警意识",
    model_env_key: "MODEL_ANALYSIS",
    capability: "risk_analysis",
    framework: "FMEA",
    tools: ["web_search", "browser"],
    debate_style: "强调风险后果的严重性",
  },
  {
    agent_id: "devil_advocate_01",
    role: "魔鬼代言人",
    personality: "天生怀疑论者，尖锐但有建设性",
    model_env_key: "MODEL_ADVERSARY",
    capability: "adversary",
    framework: "Pre-mortem Analysis",
    tools: ["web_search", "browser"],
    debate_style: "挑战每个乐观假设，揭露隐含前提",
  },
];

export const MOCK_RESULTS: Record<string, AgentResult> = Object.fromEntries(
  MOCK_AGENTS.map((a, i) => [
    a.agent_id,
    {
      agent_id: a.agent_id,
      status: "done" as const,
      progress: 100,
      preliminary_result: `基于 ${a.framework} 框架的深度分析，从${a.role}的视角...`,
      confidence: 0.6 + Math.random() * 0.3,
      tokens_used: 800 + Math.floor(Math.random() * 700),
      time_ms: 5000 + Math.floor(Math.random() * 15000),
      actions: [
        { type: "web_search", content: `搜索 ${a.capability} 相关数据` },
        { type: "analysis", content: `基于 ${a.framework} 框架分析` },
      ],
    },
  ])
);

export const MOCK_DEBATE: DebateMessage[] = [
  {
    message_id: "msg_001",
    from_agent: "tech_architect_01",
    to_agent: "market_researcher_01",
    type: "challenge",
    content: "你提到用户搜索需求很强烈，但数据样本是否足够代表性？小红书核心用户群以种草为主，主动搜索的比例可能被高估了。",
    references: ["market_researcher_01.preliminary_result"],
    confidence: 0.8,
    timestamp: "2025-01-01T10:01:00Z",
  },
  {
    message_id: "msg_002",
    from_agent: "market_researcher_01",
    to_agent: "tech_architect_01",
    type: "rebuttal",
    content: "JTBD分析显示，用户\"找到靠谱的购物参考\"是高频任务。小红书搜索月活已超3亿，占总MAU的60%。这不是被高估，而是尚未被充分满足的需求。",
    references: ["tech_architect_01.msg_001"],
    confidence: 0.85,
    timestamp: "2025-01-01T10:02:00Z",
  },
  {
    message_id: "msg_003",
    from_agent: "devil_advocate_01",
    to_agent: "broadcast",
    type: "rebuttal",
    content: "你们都在假设AI搜索能提升体验，但有没有考虑过：如果AI搜索结果质量不达预期，反而会损害用户信任？小红书的内容是UGC为主，质量参差不齐——AI可能放大低质量内容的传播。这才是最大风险。",
    references: ["market_researcher_01.preliminary_result", "tech_architect_01.preliminary_result"],
    confidence: 0.75,
    timestamp: "2025-01-01T10:03:00Z",
  },
  {
    message_id: "msg_004",
    from_agent: "business_analyst_01",
    to_agent: "devil_advocate_01",
    type: "support",
    content: "同意魔鬼代言人的风险评估。从Unit Economics角度补充：GPU推理成本约0.02元/次查询，如果日均搜索量达2亿次，年化成本高达14.6亿元。ROI回正周期可能超过3年。",
    references: ["devil_advocate_01.msg_003"],
    confidence: 0.7,
    timestamp: "2025-01-01T10:04:00Z",
  },
  {
    message_id: "msg_005",
    from_agent: "competitive_analyst_01",
    to_agent: "broadcast",
    type: "supplement",
    content: "补充竞品数据：抖音已在搜索中接入AI摘要，百度在小红书内容上做了联合搜索。如果小红书不跟进AI搜索，存在被竞品截流的风险。五力分析显示替代威胁评级为\"高\"。",
    references: [],
    confidence: 0.8,
    timestamp: "2025-01-01T10:05:00Z",
  },
  {
    message_id: "msg_006",
    from_agent: "risk_analyst_01",
    to_agent: "tech_architect_01",
    type: "question",
    content: "技术方案中多模态检索的延迟能控制在多少ms以内？根据FMEA分析，如果P99延迟超过500ms，用户流失风险的RPN值将超过200（严重度9×发生概率7×检测度3）。",
    references: ["tech_architect_01.preliminary_result"],
    confidence: 0.82,
    timestamp: "2025-01-01T10:06:00Z",
  },
  {
    message_id: "msg_007",
    from_agent: "tech_architect_01",
    to_agent: "risk_analyst_01",
    type: "rebuttal",
    content: "根据Gartner Hype Cycle，向量检索已进入成熟稳定期，P99延迟可控制在200ms内。但多模态（图文混合）检索仍在复苏爬升期，延迟约300-500ms。建议分阶段：先文本后多模态。",
    references: ["risk_analyst_01.msg_006"],
    confidence: 0.78,
    timestamp: "2025-01-01T10:07:00Z",
  },
  {
    message_id: "msg_008",
    from_agent: "devil_advocate_01",
    to_agent: "business_analyst_01",
    type: "challenge",
    content: "你计算的14.6亿年化成本假设了固定单价，但GPU成本趋势是下降的。更大的问题是：你没有考虑数据隐私合规成本。GDPR和中国个保法合规改造，保守估计需要额外2-3亿投入。",
    references: ["business_analyst_01.msg_004"],
    confidence: 0.72,
    timestamp: "2025-01-01T10:08:00Z",
  },
];

export const MOCK_EVOLUTION: EvolutionEntry[] = [
  {
    cycle: 1,
    debate_round: 1,
    action: "team_restructure",
    added: ["privacy_expert_01"],
    removed: [],
    reason: {
      capability_gaps: ["数据隐私与合规分析"],
    },
    team_size_before: 6,
    team_size_after: 7,
  },
];

export const MOCK_CONSENSUS: ConsensusReport = {
  consensus_reached: true,
  consensus_type: "full",
  core_position: "小红书引入AI搜索在技术和市场层面上是有条件可行的",
  agreement_points: [
    "用户对更智能的搜索体验有真实需求",
    "应采用分阶段实施策略（先文本后多模态）",
    "需要同步进行数据隐私合规建设",
  ],
  disagreement_points: [
    "GPU成本估算和ROI回收周期存在分歧",
    "多模态检索的技术成熟度判断不一致",
  ],
};

export const MOCK_REPORT: FinalReportData = {
  title: "小红书AI搜索可行性分析报告",
  executive_summary:
    "经过6位专家Agent的多轮圆桌辩论和交叉验证，结论为\"有条件可行\"。核心条件：分阶段实施（先文本后多模态）、控制GPU成本在年化10亿以内、同步完成隐私合规建设。团队经历1次进化重组，补充了隐私合规专家视角。",
  conclusion: "有条件可行",
  confidence: 0.76,
  key_findings: [
    { topic: "用户需求", content: "搜索月活3亿+，60%用户有主动搜索行为", source_agents: ["market_researcher_01"] },
    { topic: "技术成熟度", content: "文本向量检索已成熟，多模态仍在爬升期", source_agents: ["tech_architect_01"] },
    { topic: "竞争压力", content: "抖音/百度已布局AI搜索，不跟进将被截流", source_agents: ["competitive_analyst_01"] },
    { topic: "成本风险", content: "年化GPU成本10-15亿，ROI回正需2-3年", source_agents: ["business_analyst_01"] },
    { topic: "合规要求", content: "个保法合规改造需额外2-3亿投入", source_agents: ["devil_advocate_01"] },
  ],
  consensus_points: [
    "用户需求真实存在且强烈",
    "分阶段实施是最佳策略",
    "隐私合规是不可跳过的前置条件",
  ],
  disagreement_points: [
    "GPU成本长期趋势判断不一致（乐观派 vs 保守派）",
    "多模态检索的技术风险评估存在分歧",
  ],
  risks: [
    { risk: "AI搜索结果质量不达预期损害用户信任", severity: "high", mitigation: "小范围灰度测试+用户反馈闭环" },
    { risk: "GPU成本超支导致ROI不达预期", severity: "high", mitigation: "弹性算力+成本监控告警机制" },
    { risk: "隐私合规滞后导致法律风险", severity: "medium", mitigation: "合规建设与技术开发同步推进" },
  ],
  recommendations: [
    "Q1启动文本搜索AI化改造（投入较小、技术成熟）",
    "Q2-Q3推进多模态检索POC验证",
    "同步组建隐私合规专项团队",
    "建立GPU成本月度审计机制",
  ],
  debate_rounds: 2,
  evolution_cycles: 1,
  token_cost: { total: 85000 },
  forced_consensus: false,
};
