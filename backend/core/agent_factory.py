"""Agent 配置生成与实例化

注意：该功能已直接在 backend/engines/spawner.py 中实现，包括：
- _spawn_agent_for_subtask()：为子任务生成 Agent 配置
- _spawn_adversary()：生成魔鬼代言人 Agent
- CAPABILITY_TO_MODEL / CAPABILITY_TO_FRAMEWORK 等映射表

本文件保留为模块占位符。如果未来需要将 Agent 工厂逻辑从 Spawner 中解耦，
可在此处实现独立的 AgentFactory 类。
"""
