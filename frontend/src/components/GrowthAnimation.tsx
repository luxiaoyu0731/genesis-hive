import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import * as d3 from "d3";
import type { AgentConfig } from "../mockData";
import { MODEL_COLORS } from "../mockData";

interface Props {
  agents: AgentConfig[];
  goal: string;
}

interface Node extends d3.SimulationNodeDatum {
  id: string;
  role: string;
  color: string;
  model: string;
  framework: string;
}

export default function GrowthAnimation({ agents, goal }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [visibleAgents, setVisibleAgents] = useState<AgentConfig[]>([]);
  const [nodes, setNodes] = useState<Node[]>([]);

  // 逐个"诞生" Agent
  useEffect(() => {
    if (visibleAgents.length >= agents.length) return;
    const t = setTimeout(() => {
      setVisibleAgents((prev) => [...prev, agents[prev.length]]);
    }, 600);
    return () => clearTimeout(t);
  }, [visibleAgents, agents]);

  // D3 force layout
  useEffect(() => {
    if (!svgRef.current || visibleAgents.length === 0) return;

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const newNodes: Node[] = visibleAgents.map((a) => ({
      id: a.agent_id,
      role: a.role,
      color: MODEL_COLORS[a.model_env_key] || "#6366f1",
      model: a.model_env_key,
      framework: a.framework,
    }));

    // 全连接的 links
    const links: { source: string; target: string }[] = [];
    for (let i = 0; i < newNodes.length; i++) {
      for (let j = i + 1; j < newNodes.length; j++) {
        links.push({ source: newNodes[i].id, target: newNodes[j].id });
      }
    }

    const sim = d3
      .forceSimulation(newNodes)
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "link",
        d3.forceLink(links).id((d: any) => d.id).distance(120)
      )
      .force("collision", d3.forceCollide(50))
      .on("tick", () => {
        setNodes([...newNodes]);
      });

    return () => { sim.stop(); };
  }, [visibleAgents]);

  return (
    <div className="h-full flex flex-col">
      <div className="text-sm text-[var(--color-text-dim)] mb-3 flex items-center gap-2">
        <motion.div
          className="w-2 h-2 rounded-full bg-[var(--color-accent)]"
          animate={{ scale: [1, 1.5, 1] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        />
        Agent 生成中 — {visibleAgents.length}/{agents.length}
      </div>

      {/* 目标卡片 */}
      <div className="text-center mb-4 p-3 rounded-lg" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
        <div className="text-[10px] text-[var(--color-accent)] mb-1">目标</div>
        <div className="text-sm">{goal}</div>
      </div>

      {/* D3 力导向图 */}
      <div className="relative" style={{ height: 450 }}>
        <svg ref={svgRef} className="w-full" style={{ height: 450 }}>
          {/* 连线 */}
          {nodes.length > 1 &&
            nodes.map((n, i) =>
              nodes.slice(i + 1).map((m, j) => (
                <motion.line
                  key={`${n.id}-${m.id}`}
                  x1={n.x} y1={n.y} x2={m.x} y2={m.y}
                  stroke="var(--color-border)" strokeWidth={0.8} opacity={0.4}
                  initial={{ opacity: 0 }} animate={{ opacity: 0.4 }}
                />
              ))
            )}
        </svg>

        {/* Agent 节点（HTML overlay 方便排版） */}
        <AnimatePresence>
          {nodes.map((n) => (
            <motion.div
              key={n.id}
              className="absolute flex flex-col items-center pointer-events-none"
              style={{ left: (n.x || 0) - 32, top: (n.y || 0) - 32 }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center text-lg font-bold"
                style={{
                  background: `${n.color}15`,
                  border: `2px solid ${n.color}`,
                  boxShadow: `0 0 20px ${n.color}30`,
                }}
              >
                {n.role[0]}
              </div>
              <div className="text-[10px] mt-1 font-medium whitespace-nowrap" style={{ color: n.color }}>
                {n.role}
              </div>
              <div className="text-[9px] text-[var(--color-text-dim)]">{n.framework}</div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
