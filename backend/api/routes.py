"""FastAPI 路由 — REST API + WebSocket

POST /api/run   — 启动完整分析流程（异步后台执行，WebSocket 推送进度）
GET  /api/status — 查询当前运行状态
WS   /ws        — 实时事件推送
"""

import asyncio
import json
import traceback

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from backend.api.websocket import websocket_endpoint, manager
from backend.graph import build_hive_graph, create_initial_state

router = APIRouter()

# 当前运行状态（单实例简化版）
_current_run: dict = {"status": "idle", "result": None}


class RunRequest(BaseModel):
    goal: str
    mode: str = "demo"


async def _execute_pipeline(goal: str, mode: str) -> None:
    """后台执行完整的 L1→L5 流程，各阶段通过 WebSocket 推送事件。"""
    global _current_run
    _current_run = {"status": "running", "goal": goal, "mode": mode, "result": None}

    try:
        await manager.broadcast("run_started", {"goal": goal, "mode": mode})

        state = create_initial_state(goal, mode=mode)
        graph = build_hive_graph()

        # 使用 astream 逐节点执行，推送各阶段事件
        last_state = state
        async for chunk in graph.astream(state):
            # chunk 是 {node_name: state_update} 的字典
            for node_name, node_output in chunk.items():
                last_state = {**last_state, **node_output}

                # 按节点推送不同事件
                if node_name == "decomposer":
                    subtasks = node_output.get("task_graph", {}).get("subtasks", [])
                    await manager.broadcast("decomposed", {
                        "subtask_count": len(subtasks),
                        "subtasks": [
                            {"id": s["id"], "name": s["name"], "capability": s.get("capability")}
                            for s in subtasks
                        ],
                    })

                elif node_name == "spawner":
                    configs = node_output.get("agent_configs", [])
                    for c in configs:
                        await manager.broadcast("agent_spawned", {
                            "agent_id": c.get("agent_id"),
                            "role": c.get("role"),
                            "model": c.get("model_env_key"),
                            "framework": c.get("framework"),
                        })

                elif node_name == "executor":
                    results = node_output.get("agent_results", {})
                    for aid, r in results.items():
                        await manager.broadcast("agent_completed", {
                            "agent_id": aid,
                            "confidence": r.get("confidence", 0),
                            "time_ms": r.get("time_ms", 0),
                            "tokens_used": r.get("tokens_used", 0),
                        })

                elif node_name == "council":
                    consensus = node_output.get("consensus_report", {})
                    await manager.broadcast("debate_round_completed", {
                        "round": node_output.get("debate_round", 0),
                        "consensus_reached": consensus.get("consensus_reached", False),
                        "consensus_type": consensus.get("consensus_type", "none"),
                        "recommendation": consensus.get("recommendation", ""),
                    })

                elif node_name == "evolver":
                    evo_log = node_output.get("evolution_log", [])
                    latest = evo_log[-1] if evo_log else {}
                    await manager.broadcast("evolution_triggered", {
                        "cycle": node_output.get("evolution_cycle", 0),
                        "added": latest.get("added", []),
                        "removed": latest.get("removed", []),
                    })

                elif node_name == "synthesizer":
                    report = node_output.get("final_report", {})
                    await manager.broadcast("report_ready", {
                        "title": report.get("title", ""),
                        "conclusion": report.get("conclusion", ""),
                        "confidence": report.get("confidence", 0),
                    })

        _current_run = {"status": "completed", "result": last_state}
        await manager.broadcast("run_completed", {
            "token_used": last_state.get("token_used", 0),
            "debate_rounds": last_state.get("debate_round", 0),
        })

    except Exception as e:
        _current_run = {"status": "error", "error": str(e)}
        await manager.broadcast("run_error", {"error": str(e), "trace": traceback.format_exc()})


@router.post("/api/run")
async def start_run(req: RunRequest):
    """启动一次完整的 Genesis Hive 分析流程（后台异步执行）"""
    if _current_run.get("status") == "running":
        return {"status": "busy", "message": "已有运行中的任务"}

    # 后台启动，立即返回
    asyncio.create_task(_execute_pipeline(req.goal, req.mode))
    return {"status": "started", "goal": req.goal, "mode": req.mode}


@router.get("/api/status")
async def get_status():
    """查询当前运行状态"""
    info = {"status": _current_run.get("status", "idle")}
    if _current_run.get("status") == "completed" and _current_run.get("result"):
        result = _current_run["result"]
        info["token_used"] = result.get("token_used", 0)
        info["debate_rounds"] = result.get("debate_round", 0)
        report = result.get("final_report", {})
        info["conclusion"] = report.get("conclusion", "")
    elif _current_run.get("status") == "error":
        info["error"] = _current_run.get("error", "")
    return info


@router.get("/api/report")
async def get_report():
    """获取完整的最终报告"""
    if _current_run.get("status") != "completed" or not _current_run.get("result"):
        return {"error": "暂无可用报告", "status": _current_run.get("status", "idle")}
    result = _current_run["result"]
    return {
        "final_report": result.get("final_report", {}),
        "debate_history": result.get("debate_history", []),
        "evolution_log": result.get("evolution_log", []),
        "agent_configs": [
            {
                "agent_id": c.get("agent_id"),
                "role": c.get("role"),
                "model_env_key": c.get("model_env_key"),
                "framework": c.get("framework"),
                "capability": c.get("capability"),
            }
            for c in result.get("agent_configs", [])
        ],
        "token_used": result.get("token_used", 0),
    }


@router.websocket("/ws")
async def ws_route(ws: WebSocket):
    await websocket_endpoint(ws)
