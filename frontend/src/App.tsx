import { useState } from "react";
import GrowthAnimation from "./components/GrowthAnimation";
import ExecutionBoard from "./components/ExecutionBoard";
import CouncilRoom from "./components/CouncilRoom";
import EvolutionView from "./components/EvolutionView";
import FinalReport from "./components/FinalReport";
import TeamTopology from "./components/TeamTopology";
import {
  MOCK_AGENTS, MOCK_RESULTS, MOCK_DEBATE,
  MOCK_EVOLUTION, MOCK_CONSENSUS, MOCK_REPORT,
} from "./mockData";

type Phase = "growth" | "execution" | "council" | "evolution" | "report";

const PHASES: { key: Phase; label: string; icon: string }[] = [
  { key: "growth", label: "Agent 生成", icon: "◉" },
  { key: "execution", label: "并行执行", icon: "▶" },
  { key: "council", label: "圆桌辩论", icon: "⊕" },
  { key: "evolution", label: "团队进化", icon: "↻" },
  { key: "report", label: "最终报告", icon: "■" },
];

export default function App() {
  const [phase, setPhase] = useState<Phase>("council");

  return (
    <div className="min-h-screen">
      {/* 顶部导航 */}
      <header
        className="flex items-center justify-between px-6 py-3"
        style={{ background: "var(--color-surface)", borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-3">
          <div className="text-lg font-bold tracking-tight">
            <span className="text-[var(--color-accent)]">Genesis</span>
            <span className="text-[var(--color-text-dim)]"> Hive</span>
          </div>
          <span className="text-[10px] text-[var(--color-text-dim)] px-2 py-0.5 rounded" style={{ background: "var(--color-surface-2)" }}>
            自进化多Agent智能体
          </span>
        </div>
        <div className="text-[11px] text-[var(--color-text-dim)]">
          目标：分析小红书做AI搜索的可行性
        </div>
      </header>

      {/* 阶段选择器 */}
      <nav className="flex items-center px-6 py-2 gap-1" style={{ background: "var(--color-surface)" }}>
        {PHASES.map((p, i) => (
          <button
            key={p.key}
            onClick={() => setPhase(p.key)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors"
            style={{
              background: phase === p.key ? "var(--color-accent)" : "transparent",
              color: phase === p.key ? "#fff" : "var(--color-text-dim)",
            }}
          >
            <span>{p.icon}</span>
            <span>{p.label}</span>
            {i < PHASES.length - 1 && (
              <span className="ml-2 text-[var(--color-border)]">→</span>
            )}
          </button>
        ))}
      </nav>

      {/* 主内容区 */}
      <main className="p-6">
          <div key={phase}>
            {phase === "growth" && (
              <GrowthAnimation
                agents={MOCK_AGENTS}
                goal="分析小红书做AI搜索的可行性"
              />
            )}
            {phase === "execution" && (
              <ExecutionBoard
                agents={MOCK_AGENTS}
                results={MOCK_RESULTS}
              />
            )}
            {phase === "council" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 500px", gap: "24px" }}>
                <CouncilRoom
                  agents={MOCK_AGENTS}
                  messages={MOCK_DEBATE}
                />
                <TeamTopology
                  agents={MOCK_AGENTS}
                  debateMessages={MOCK_DEBATE}
                />
              </div>
            )}
            {phase === "evolution" && (
              <EvolutionView
                agents={[...MOCK_AGENTS, {
                  agent_id: "privacy_expert_01",
                  role: "隐私合规专家",
                  personality: "严谨，关注法律风险",
                  model_env_key: "MODEL_ANALYSIS",
                  capability: "legal_compliance",
                  framework: "合规矩阵分析",
                  tools: ["web_search"],
                  debate_style: "以法规条文质疑合规风险",
                }]}
                evolution={MOCK_EVOLUTION}
                consensus={MOCK_CONSENSUS}
                debateRound={2}
              />
            )}
            {phase === "report" && (
              <FinalReport report={MOCK_REPORT} />
            )}
          </div>
      </main>
    </div>
  );
}
