"""WebSocket 实时推送 — Agent 状态流"""

import asyncio
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """管理所有 WebSocket 连接"""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, event: str, data: Any):
        """广播事件到所有连接"""
        msg = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                pass


manager = ConnectionManager()


async def websocket_endpoint(ws: WebSocket):
    """WebSocket 入口"""
    await manager.connect(ws)
    try:
        while True:
            # 保持连接，接收客户端心跳
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(ws)
