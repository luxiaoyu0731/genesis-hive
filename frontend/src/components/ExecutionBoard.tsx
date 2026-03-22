import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import type { AgentConfig, AgentResult } from "../mockData";
import { MODEL_COLORS, MODEL_LABELS } from "../mockData";

interface Props {
  agents: AgentConfig[];
  results: Record<string, AgentResult>;
}

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  idle: { color: "#8888a0", label: "等待中" },
  thinking: { color: "#3b82f6", label: "思考中" },
  searching: { color: "#22c55e", label: "搜索中" },
  analyzing: { color: "#a855f7", label: "分析中" },
  done: { color: "#8888a0", label: "完成" },
};

export default function ExecutionBoard({ agents, results }: Props) {
  // 模拟进度动画
  const [progresses, setProgresses] = useState<Record<string, number>>({});
  const [statuses, setStatuses] = useState<Record<string, string>>({});

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    agents.forEach((a, i) => {
      const phases = ["thinking", "searching", "analyzing", "done"];
      let phaseIdx = 0;
      const step = () => {
        if (phaseIdx < phases.length) {
          setStatuses((s) => ({ ...s, [a.agent_id]: phases[phaseIdx] }));
          setProgresses((p) => ({ ...p, [a.agent_id]: ((phaseIdx + 1) / phases.length) * 100 }));
          phaseIdx++;
          timers.push(setTimeout(step, 500 + Math.random() * 800));
        }
      };
      timers.push(setTimeout(step, i * 200));
    });
    return () => timers.forEach(clearTimeout);
  }, [agents]);

  return (
    <div className="space-y-3">
      <div className="text-sm text-[var(--color-text-dim)] flex items-center gap-2 mb-2">
        <motion.div
          className="w-2 h-2 rounded-full bg-[#22c55e]"
          animate={{ scale: [1, 1.4, 1] }}
          transition={{ repeat: Infinity, duration: 1 }}
        />
        并行执行中
      </div>

      {agents.map((agent) => {
        const status = statuses[agent.agent_id] || "idle";
        const progress = progresses[agent.agent_id] || 0;
        const result = results[agent.agent_id];
        const statusCfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle;
        const color = MODEL_COLORS[agent.model_env_key] || "#6366f1";

        return (
          <motion.div
            key={agent.agent_id}
            className="rounded-lg p-3"
            style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* 头部 */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: `${color}20`, border: `1.5px solid ${color}` }}
                >
                  {agent.role[0]}
                </div>
                <div>
                  <div className="text-sm font-medium">{agent.role}</div>
                  <div className="text-[10px] text-[var(--color-text-dim)]">
                    {MODEL_LABELS[agent.model_env_key]} · {agent.framework}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <motion.span
                  className="text-[10px] px-2 py-0.5 rounded-full"
                  style={{ background: `${statusCfg.color}20`, color: statusCfg.color }}
                  animate={status !== "done" ? { opacity: [1, 0.5, 1] } : {}}
                  transition={{ repeat: Infinity, duration: 1 }}
                >
                  {statusCfg.label}
                </motion.span>
                {result && (
                  <span className="text-[10px] text-[var(--color-text-dim)]">
                    {result.tokens_used} tok · {(result.time_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            </div>

            {/* 进度条 */}
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--color-surface-2)" }}>
              <motion.div
                className="h-full rounded-full"
                style={{ background: color }}
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>

            {/* 工具标签 */}
            <div className="flex gap-1 mt-2">
              {agent.tools.map((t) => (
                <span
                  key={t}
                  className="text-[9px] px-1.5 py-0.5 rounded"
                  style={{ background: "var(--color-surface-2)", color: "var(--color-text-dim)" }}
                >
                  {t}
                </span>
              ))}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
