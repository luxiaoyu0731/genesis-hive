import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { motion } from "framer-motion";
import { AgentConfig, MODEL_COLORS, MODEL_LABELS, DebateMessage } from "../mockData";

interface Props {
  agents: AgentConfig[];
  debateMessages: DebateMessage[];
}

interface Node extends d3.SimulationNodeDatum {
  id: string;
  role: string;
  model: string;
  capability: string;
  framework: string;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  type: string;
  count: number;
}

/**
 * TeamTopology — D3 force-directed 团队拓扑图
 *
 * 节点 = Agent（颜色按模型区分，大小按交互频次）
 * 连线 = 辩论中的引用/回应关系（粗细按交互次数，颜色按消息类型）
 */
export default function TeamTopology({ agents, debateMessages }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const WIDTH = 500;
  const HEIGHT = 400;

  useEffect(() => {
    if (!svgRef.current || agents.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // 构建节点
    const nodes: Node[] = agents.map((a) => ({
      id: a.agent_id,
      role: a.role,
      model: a.model_env_key,
      capability: a.capability,
      framework: a.framework,
    }));

    // 从辩论消息中提取交互关系
    const linkMap = new Map<string, { type: string; count: number }>();
    debateMessages.forEach((msg) => {
      if (msg.to_agent === "broadcast") {
        // broadcast 消息：与所有其他 Agent 建立连线
        agents.forEach((a) => {
          if (a.agent_id !== msg.from_agent) {
            const key = [msg.from_agent, a.agent_id].sort().join("--");
            const existing = linkMap.get(key);
            if (existing) {
              existing.count += 1;
            } else {
              linkMap.set(key, { type: msg.type, count: 1 });
            }
          }
        });
      } else {
        const key = [msg.from_agent, msg.to_agent].sort().join("--");
        const existing = linkMap.get(key);
        if (existing) {
          existing.count += 1;
        } else {
          linkMap.set(key, { type: msg.type, count: 1 });
        }
      }
    });

    const links: Link[] = Array.from(linkMap.entries()).map(([key, val]) => {
      const [source, target] = key.split("--");
      return { source, target, type: val.type, count: val.count };
    });

    // 交互频次统计（用于节点大小）
    const interactionCount = new Map<string, number>();
    debateMessages.forEach((msg) => {
      interactionCount.set(msg.from_agent, (interactionCount.get(msg.from_agent) || 0) + 1);
    });

    // D3 force simulation
    const simulation = d3
      .forceSimulation<Node>(nodes)
      .force(
        "link",
        d3.forceLink<Node, Link>(links).id((d) => d.id).distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(WIDTH / 2, HEIGHT / 2))
      .force("collision", d3.forceCollide().radius(35));

    // 容器
    const g = svg.append("g");

    // 连线
    const link = g
      .selectAll<SVGLineElement, Link>("line")
      .data(links)
      .enter()
      .append("line")
      .attr("stroke", "#4b5563")
      .attr("stroke-opacity", 0.5)
      .attr("stroke-width", (d) => Math.min(1 + d.count, 5));

    // 节点组
    const node = g
      .selectAll<SVGGElement, Node>("g.node")
      .data(nodes)
      .enter()
      .append("g")
      .attr("class", "node")
      .style("cursor", "pointer");

    // 节点光晕
    node
      .append("circle")
      .attr("r", (d) => {
        const count = interactionCount.get(d.id) || 1;
        return 16 + Math.min(count * 2, 12);
      })
      .attr("fill", (d) => MODEL_COLORS[d.model] || "#6b7280")
      .attr("fill-opacity", 0.15)
      .attr("stroke", (d) => MODEL_COLORS[d.model] || "#6b7280")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.4);

    // 节点实心圆
    node
      .append("circle")
      .attr("r", 12)
      .attr("fill", (d) => MODEL_COLORS[d.model] || "#6b7280")
      .attr("stroke", "#1f2937")
      .attr("stroke-width", 2);

    // Agent 首字标签
    node
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("fill", "#fff")
      .attr("font-size", "10px")
      .attr("font-weight", "bold")
      .text((d) => d.role.charAt(0));

    // Agent 名称（节点下方）
    node
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "30px")
      .attr("fill", "#9ca3af")
      .attr("font-size", "9px")
      .text((d) => d.role);

    // Tick 更新位置
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as Node).x || 0)
        .attr("y1", (d) => (d.source as Node).y || 0)
        .attr("x2", (d) => (d.target as Node).x || 0)
        .attr("y2", (d) => (d.target as Node).y || 0);

      node.attr("transform", (d) => `translate(${d.x || 0},${d.y || 0})`);
    });

    // 拖拽
    const drag = d3
      .drag<SVGGElement, Node>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    node.call(drag);

    return () => {
      simulation.stop();
    };
  }, [agents, debateMessages]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      style={{
        background: "linear-gradient(135deg, #111827 0%, #0f172a 100%)",
        borderRadius: "12px",
        padding: "16px",
        border: "1px solid #1f2937",
      }}
    >
      <h3
        style={{
          color: "#e5e7eb",
          fontSize: "14px",
          fontWeight: 600,
          marginBottom: "8px",
        }}
      >
        Team Topology
      </h3>

      {/* 图例 */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "8px", flexWrap: "wrap" }}>
        {Object.entries(MODEL_LABELS).map(([key, label]) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: MODEL_COLORS[key] || "#6b7280",
              }}
            />
            <span style={{ color: "#9ca3af", fontSize: "10px" }}>{label}</span>
          </div>
        ))}
      </div>

      <svg ref={svgRef} width={WIDTH} height={HEIGHT} />
    </motion.div>
  );
}
