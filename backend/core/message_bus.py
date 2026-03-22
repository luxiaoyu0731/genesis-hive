"""Agent 间消息总线 — 统一消息格式与路由"""

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# 消息类型枚举
MessageType = Literal[
    "preliminary_result",  # 初步结果呈述
    "challenge",           # 质疑
    "support",             # 支持
    "rebuttal",            # 反驳
    "supplement",          # 补充
    "question",            # 提问
    "revision",            # 修正
]


class BusMessage(BaseModel):
    """Agent 间通信的统一消息格式"""
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    from_agent: str                          # 发送者 agent_id
    to_agent: str                            # 接收者 agent_id 或 "broadcast"
    type: MessageType                        # 消息类型
    content: str                             # 消息正文
    references: list[str] = Field(default_factory=list)  # 被引用的消息 ID 或 Agent 结果段落
    confidence: float = 0.0                  # 发送者对此消息的置信度
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MessageBus:
    """
    消息总线：收集和分发 Agent 间的消息。

    职责：
    - 存储所有辩论消息
    - 按 agent_id 或轮次筛选消息
    - 统计引用关系（用于低贡献检测）
    """

    def __init__(self):
        self._messages: list[BusMessage] = []

    def publish(self, message: BusMessage) -> None:
        """发布一条消息到总线"""
        self._messages.append(message)

    def get_all(self) -> list[BusMessage]:
        """获取所有消息"""
        return list(self._messages)

    def get_messages_for(self, agent_id: str) -> list[BusMessage]:
        """获取发送给指定 Agent 的消息（包括 broadcast）"""
        return [
            m for m in self._messages
            if m.to_agent == agent_id or m.to_agent == "broadcast"
        ]

    def get_messages_from(self, agent_id: str) -> list[BusMessage]:
        """获取指定 Agent 发送的所有消息"""
        return [m for m in self._messages if m.from_agent == agent_id]

    def get_messages_by_type(self, msg_type: MessageType) -> list[BusMessage]:
        """按消息类型筛选"""
        return [m for m in self._messages if m.type == msg_type]

    def count_references_to(self, agent_id: str) -> int:
        """统计其他 Agent 引用指定 Agent 的次数（用于低贡献检测）"""
        count = 0
        for m in self._messages:
            if m.from_agent == agent_id:
                continue
            for ref in m.references:
                if agent_id in ref:
                    count += 1
        return count

    def to_dict_list(self) -> list[dict]:
        """序列化为 dict 列表（用于存入 HiveState）"""
        return [m.model_dump() for m in self._messages]

    def clear(self) -> None:
        """清空消息（新一轮辩论前调用）"""
        self._messages.clear()
