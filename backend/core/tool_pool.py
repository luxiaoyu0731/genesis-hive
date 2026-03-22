"""可用工具池管理

注意：工具分配逻辑已在 backend/engines/spawner.py 的
CAPABILITY_TO_TOOLS 映射表中实现。

当前工具为元数据标注（标记 Agent 应使用哪类信息源），
实际执行由 LLM 基于 system_prompt 中的信息源偏好完成。

工具实现骨架位于 backend/tools/ 目录：
- web_search.py：Web 搜索（待实现）
- browser.py：浏览器自动化（待实现）
- code_executor.py：代码执行沙箱（待实现）

未来如需接入真实工具调用（如 SerpAPI、Playwright），
可在此处实现 ToolPool 注册与分发机制。
"""
