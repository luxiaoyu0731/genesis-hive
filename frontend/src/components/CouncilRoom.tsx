import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AgentConfig, DebateMessage } from "../mockData";
import { MSG_TYPE_META, MODEL_COLORS } from "../mockData";

interface Props {
  agents: AgentConfig[];
  messages: DebateMessage[];
}

// Agent 头像在圆形上的位置
function circlePos(i: number, total: number, r: number) {
  const angle = (2 * Math.PI * i) / total - Math.PI / 2;
  return { x: r + r * Math.cos(angle), y: r + r * Math.sin(angle) };
}

export default function CouncilRoom({ agents, messages }: Props) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 逐条播放消息
  useEffect(() => {
    if (visibleCount >= messages.length) return;
    const t = setTimeout(() => {
      const msg = messages[visibleCount];
      setSpeakingId(msg.from_agent);
      setVisibleCount((c) => c + 1);
      // 1.5s 后取消高亮
      setTimeout(() => setSpeakingId(null), 1500);
    }, 800);
    return () => clearTimeout(t);
  }, [visibleCount, messages]);

  // 自动滚到底
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [visibleCount]);

  const visible = messages.slice(0, visibleCount);
  const r = 120; // 圆半径

  const agentMap = Object.fromEntries(agents.map((a) => [a.agent_id, a]));

  return (
    <div className="flex gap-6 h-full">
      {/* 左侧：圆形布局 Agent 头像 */}
      <div className="flex-shrink-0 flex items-center justify-center" style={{ width: r * 2 + 80 }}>
        <div className="relative" style={{ width: r * 2, height: r * 2 }}>
          {/* 中心标签 */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-[11px] text-[var(--color-text-dim)] text-center leading-tight">
              圆桌<br />辩论
            </div>
          </div>
          {/* 连线 */}
          <svg className="absolute inset-0" width={r * 2} height={r * 2}>
            {agents.map((_, i) => {
              const p1 = circlePos(i, agents.length, r);
              return agents.slice(i + 1).map((_, j) => {
                const p2 = circlePos(i + j + 1, agents.length, r);
                return (
                  <line
                    key={`${i}-${j}`}
                    x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                    stroke="var(--color-border)" strokeWidth={0.5} opacity={0.3}
                  />
                );
              });
            })}
          </svg>
          {/* Agent 节点 */}
          {agents.map((agent, i) => {
            const pos = circlePos(i, agents.length, r);
            const isSpeaking = speakingId === agent.agent_id;
            const isDevil = agent.agent_id === "devil_advocate_01";
            const color = MODEL_COLORS[agent.model_env_key] || "#6366f1";

            return (
              <motion.div
                key={agent.agent_id}
                className="absolute flex flex-col items-center"
                style={{ left: pos.x - 24, top: pos.y - 24 }}
                animate={{
                  scale: isSpeaking ? 1.25 : 1,
                }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
              >
                <motion.div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-[13px] font-bold"
                  style={{
                    background: `${color}20`,
                    border: `2px solid ${color}`,
                    boxShadow: isSpeaking
                      ? `0 0 20px ${isDevil && visible.some(m => m.from_agent === agent.agent_id && m.type === "rebuttal") ? "#ef4444" : color}80`
                      : "none",
                  }}
                  animate={{
                    borderColor: isSpeaking && isDevil ? ["#ef4444", "#ff6666", "#ef4444"] : color,
                  }}
                  transition={{ repeat: isSpeaking && isDevil ? Infinity : 0, duration: 0.5 }}
                >
                  {agent.role[0]}
                </motion.div>
                <div className="text-[10px] mt-1 text-center whitespace-nowrap" style={{ color }}>
                  {agent.role}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* 右侧：实时对话流 */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="text-sm text-[var(--color-text-dim)] mb-2 flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-[#22c55e] animate-pulse" />
          圆桌辩论进行中 — {visible.length}/{messages.length} 条发言
        </div>
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-3 pr-2"
          style={{ maxHeight: "calc(100vh - 200px)" }}
        >
          <AnimatePresence>
            {visible.map((msg) => {
              const meta = MSG_TYPE_META[msg.type] || { color: "#888", label: msg.type };
              const agent = agentMap[msg.from_agent];
              const isDevil = msg.from_agent === "devil_advocate_01";
              const isHotRebuttal = isDevil && (msg.type === "rebuttal" || msg.type === "challenge");

              return (
                <motion.div
                  key={msg.message_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="rounded-lg p-3"
                  style={{
                    background: isHotRebuttal ? "#ef444415" : "var(--color-surface)",
                    border: `1px solid ${isHotRebuttal ? "#ef4444" : "var(--color-border)"}`,
                  }}
                >
                  {/* 头部：发言者 + 类型标签 + 目标 */}
                  <div className="flex items-center gap-2 mb-1.5">
                    <span
                      className="text-xs font-bold"
                      style={{ color: MODEL_COLORS[agent?.model_env_key || ""] || "#888" }}
                    >
                      {agent?.role || msg.from_agent}
                    </span>
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                      style={{ background: `${meta.color}25`, color: meta.color }}
                    >
                      {meta.label}
                    </span>
                    {msg.to_agent !== "broadcast" && (
                      <span className="text-[10px] text-[var(--color-text-dim)]">
                        → {agentMap[msg.to_agent]?.role || msg.to_agent}
                      </span>
                    )}
                    {isHotRebuttal && (
                      <motion.span
                        className="text-[10px] text-[#ef4444] font-bold"
                        animate={{ opacity: [1, 0.4, 1] }}
                        transition={{ repeat: 2, duration: 0.4 }}
                      >
                        ⚡ 强烈反驳
                      </motion.span>
                    )}
                  </div>
                  {/* 内容 */}
                  <div className="text-[13px] leading-relaxed text-[var(--color-text)]">
                    {msg.content}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
