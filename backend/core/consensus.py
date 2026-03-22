"""共识检测算法 — 基于裁判 LLM 结构化判定

注意：该功能已直接在 backend/engines/council.py 中实现，包括：
- phase_d_judge()：使用 MODEL_JUDGE（独立第三方 LLM）评估共识
- JUDGE_SYSTEM_PROMPT：裁判的结构化输出要求
- 区分"讨论同一话题"和"得出相同结论"的判断逻辑

本文件保留为模块占位符。如果未来需要支持多种共识算法
（如加权投票、Delphi 法等），可在此处实现 ConsensusStrategy 接口。
"""
