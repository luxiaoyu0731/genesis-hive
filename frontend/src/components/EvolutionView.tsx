import { motion, AnimatePresence } from "framer-motion";
import type { AgentConfig, EvolutionEntry, ConsensusReport } from "../mockData";
import { MODEL_COLORS } from "../mockData";

interface Props {
  agents: AgentConfig[];
  evolution: EvolutionEntry[];
  consensus: ConsensusReport;
  debateRound: number;
}

export default function EvolutionView({ agents, evolution, consensus, debateRound }: Props) {
  // 共识度进度（full=100, partial=60, none=20）
  const consensusPercent = consensus.consensus_type === "full" ? 100
    : consensus.consensus_type === "partial" ? 60 : 20;

  return (
    <div className="space-y-5">
      {/* 顶部状态栏 */}
      <div className="flex gap-4">
        <div className="flex-1 rounded-lg p-3" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <div className="text-[10px] text-[var(--color-text-dim)] mb-1">辩论轮次</div>
          <div className="text-2xl font-bold text-[var(--color-accent)]">{debateRound}</div>
        </div>
        <div className="flex-1 rounded-lg p-3" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <div className="text-[10px] text-[var(--color-text-dim)] mb-1">进化次数</div>
          <div className="text-2xl font-bold text-[var(--color-purple)]">{evolution.length}</div>
        </div>
        <div className="flex-1 rounded-lg p-3" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <div className="text-[10px] text-[var(--color-text-dim)] mb-1">团队规模</div>
          <div className="text-2xl font-bold text-[var(--color-green)]">{agents.length}</div>
        </div>
        <div className="flex-1 rounded-lg p-3" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <div className="text-[10px] text-[var(--color-text-dim)] mb-1">共识度</div>
          <div className="text-2xl font-bold" style={{ color: consensusPercent === 100 ? "#22c55e" : consensusPercent >= 60 ? "#f97316" : "#ef4444" }}>
            {consensusPercent}%
          </div>
        </div>
      </div>

      {/* 共识进度条 */}
      <div>
        <div className="text-[11px] text-[var(--color-text-dim)] mb-1">共识达成度</div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--color-surface-2)" }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: consensusPercent === 100 ? "#22c55e" : consensusPercent >= 60 ? "#f97316" : "#ef4444" }}
            initial={{ width: 0 }}
            animate={{ width: `${consensusPercent}%` }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* 当前团队 */}
      <div>
        <div className="text-[11px] text-[var(--color-text-dim)] mb-2">当前团队拓扑</div>
        <div className="flex flex-wrap gap-2">
          <AnimatePresence>
            {agents.map((a) => {
              const color = MODEL_COLORS[a.model_env_key] || "#6366f1";
              const isNew = evolution.some((e) => e.added.includes(a.agent_id));
              return (
                <motion.div
                  key={a.agent_id}
                  className="flex items-center gap-2 rounded-lg px-3 py-2"
                  style={{
                    background: "var(--color-surface)",
                    border: `1px solid ${isNew ? "#22c55e" : "var(--color-border)"}`,
                  }}
                  initial={isNew ? { scale: 0, x: 100 } : { opacity: 0 }}
                  animate={{ scale: 1, x: 0, opacity: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                  layout
                >
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{ background: `${color}20`, border: `1.5px solid ${color}` }}
                  >
                    {a.role[0]}
                  </div>
                  <div>
                    <div className="text-xs font-medium">{a.role}</div>
                    <div className="text-[9px] text-[var(--color-text-dim)]">{a.framework}</div>
                  </div>
                  {isNew && (
                    <motion.span
                      className="text-[9px] text-[#22c55e] font-bold"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: [0, 1, 0.5, 1] }}
                      transition={{ duration: 1 }}
                    >
                      NEW
                    </motion.span>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>

      {/* 进化日志 */}
      {evolution.length > 0 && (
        <div>
          <div className="text-[11px] text-[var(--color-text-dim)] mb-2">进化日志</div>
          <div className="space-y-2">
            {evolution.map((e, i) => (
              <motion.div
                key={i}
                className="rounded-lg p-3 text-xs"
                style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[var(--color-accent)] font-bold">Cycle {e.cycle}</span>
                  <span className="text-[var(--color-text-dim)]">辩论轮 {e.debate_round}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--color-surface-2)" }}>
                    {e.team_size_before} → {e.team_size_after}
                  </span>
                </div>
                {e.reason.capability_gaps && (
                  <div className="text-[#f97316]">
                    能力缺口：{e.reason.capability_gaps.join(", ")}
                  </div>
                )}
                {e.added.length > 0 && (
                  <div className="text-[#22c55e]">+ 加入：{e.added.join(", ")}</div>
                )}
                {e.removed.length > 0 && (
                  <div className="text-[#ef4444]">- 退场：{e.removed.join(", ")}</div>
                )}
                {e.reason.low_contribution_agents?.map((lc) => (
                  <div key={lc.agent_id} className="text-[var(--color-text-dim)]">
                    退场原因：{lc.reason}
                  </div>
                ))}
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
