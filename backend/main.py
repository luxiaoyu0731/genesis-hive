"""Genesis Hive — FastAPI 入口

挂载 REST API 路由和 WebSocket 端点，配置 CORS。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

app = FastAPI(
    title="Genesis Hive",
    version="0.1.0",
    description="自进化多Agent智能体系统",
)

# CORS 配置（开发环境允许前端 Vite dev server）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载所有路由（包括 POST /api/run 和 WS /ws）
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
