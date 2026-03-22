import { motion } from "framer-motion";
import type { FinalReportData } from "../mockData";

interface Props {
  report: FinalReportData;
}

const SEVERITY_COLORS: Record<string, string> = {
  high: "#ef4444",
  medium: "#f97316",
  low: "#22c55e",
};

export default function FinalReport({ report }: Props) {
  const confidenceColor = report.confidence >= 0.75 ? "#22c55e"
    : report.confidence >= 0.5 ? "#f97316" : "#ef4444";

  return (
    <div className="space-y-5 max-w-4xl mx-auto">
      {/* 标题 + 核心结论 */}
      <motion.div
        className="text-center py-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-xl font-bold mb-4">{report.title}</h1>
        <div className="flex items-center justify-center gap-6">
          <div className="text-center">
            <div className="text-[10px] text-[var(--color-text-dim)] mb-1">核心结论</div>
            <div
              className="text-2xl font-bold px-4 py-1 rounded-lg"
              style={{
                color: report.conclusion === "可行" ? "#22c55e" : report.conclusion === "不可行" ? "#ef4444" : "#f97316",
                background: report.conclusion === "可行" ? "#22c55e15" : report.conclusion === "不可行" ? "#ef444415" : "#f9731615",
              }}
            >
              {report.conclusion}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] text-[var(--color-text-dim)] mb-1">置信度</div>
            <div className="relative w-16 h-16">
              <svg className="w-16 h-16 -rotate-90">
                <circle cx={32} cy={32} r={26} fill="none" stroke="var(--color-surface-2)" strokeWidth={4} />
                <motion.circle
                  cx={32} cy={32} r={26} fill="none" stroke={confidenceColor}
                  strokeWidth={4} strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 26}`}
                  initial={{ strokeDashoffset: 2 * Math.PI * 26 }}
                  animate={{ strokeDashoffset: 2 * Math.PI * 26 * (1 - report.confidence) }}
                  transition={{ duration: 1.5 }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center text-sm font-bold" style={{ color: confidenceColor }}>
                {Math.round(report.confidence * 100)}%
              </div>
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] text-[var(--color-text-dim)] mb-1">Token 消耗</div>
            <div className="text-lg font-bold text-[var(--color-accent)]">{(report.token_cost.total / 1000).toFixed(1)}K</div>
          </div>
        </div>
      </motion.div>

      {/* 执行摘要 */}
      <Section title="执行摘要">
        <p className="text-[13px] leading-relaxed">{report.executive_summary}</p>
        <div className="flex gap-3 mt-3 text-[10px]">
          <span className="px-2 py-0.5 rounded" style={{ background: "var(--color-surface-2)" }}>
            辩论 {report.debate_rounds} 轮
          </span>
          <span className="px-2 py-0.5 rounded" style={{ background: "var(--color-surface-2)" }}>
            进化 {report.evolution_cycles} 次
          </span>
          {report.forced_consensus && (
            <span className="px-2 py-0.5 rounded" style={{ background: "#ef444420", color: "#ef4444" }}>
              强制共识
            </span>
          )}
        </div>
      </Section>

      {/* 关键发现 */}
      <Section title="关键发现">
        <div className="space-y-2">
          {report.key_findings.map((f, i) => (
            <motion.div
              key={i}
              className="flex gap-3 p-2 rounded"
              style={{ background: "var(--color-surface-2)" }}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <div className="text-[var(--color-accent)] font-bold text-xs whitespace-nowrap pt-0.5">{f.topic}</div>
              <div className="text-xs text-[var(--color-text)]">{f.content}</div>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* 共识 vs 分歧 */}
      <div className="grid grid-cols-2 gap-4">
        <Section title="共识要点">
          {report.consensus_points.map((p, i) => (
            <div key={i} className="flex items-start gap-2 text-xs mb-1.5">
              <span className="text-[#22c55e] mt-0.5">&#10003;</span>
              <span>{p}</span>
            </div>
          ))}
        </Section>
        <Section title="分歧要点">
          {report.disagreement_points.map((p, i) => (
            <div key={i} className="flex items-start gap-2 text-xs mb-1.5">
              <span className="text-[#ef4444] mt-0.5">&#10007;</span>
              <span>{p}</span>
            </div>
          ))}
        </Section>
      </div>

      {/* 风险 */}
      <Section title="风险评估">
        <div className="space-y-2">
          {report.risks.map((r, i) => (
            <div key={i} className="flex items-start gap-3 text-xs p-2 rounded" style={{ background: "var(--color-surface-2)" }}>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded font-bold whitespace-nowrap"
                style={{ background: `${SEVERITY_COLORS[r.severity]}20`, color: SEVERITY_COLORS[r.severity] }}
              >
                {r.severity.toUpperCase()}
              </span>
              <div>
                <div className="font-medium">{r.risk}</div>
                <div className="text-[var(--color-text-dim)] mt-0.5">缓解：{r.mitigation}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* 建议 */}
      <Section title="实施建议">
        {report.recommendations.map((r, i) => (
          <div key={i} className="flex items-start gap-2 text-xs mb-1.5">
            <span className="text-[var(--color-accent)] font-bold">{i + 1}.</span>
            <span>{r}</span>
          </div>
        ))}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg p-4" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
      <div className="text-xs font-bold text-[var(--color-accent)] mb-3 uppercase tracking-wider">{title}</div>
      {children}
    </div>
  );
}
