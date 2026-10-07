# 代码审查 · 2026-10-06

结论：五层引擎的结构有辨识度，是可继续发展的多 Agent 原型；任务生命周期、预算和工具实现尚不足以直接作为公网产品。

范围：43 个受版本管理的源码文件规模与 Python 语法检查；重点阅读服务入口、运行 API、模型服务、执行器、消息总线与 JSON 输出解析。

## 本次修复

`backend/core/utils.py` 对 JSON 顶层类型执行对象约束。原来 `[]`、`null` 或数值解析成功后会进入期待 `.get()` 的引擎，错误发生在更深层；现在解析入口拒绝非对象，安全解析按原约定返回默认值。新增普通对象、代码围栏对象、解释文字、数组与标量测试。

## 剩余问题

| 优先级 | 证据 | 影响 |
|---|---|---|
| P1 | `backend/api/routes.py` create_task 后才在协程里标 running | 两次紧邻请求可能启动两条收费任务；需同步占位与任务锁 |
| P1 | 同文件无认证，错误广播包含 traceback | 不能将当前 API 直接暴露公网 |
| P2 | `backend/core/llm_service.py` 导入时初始化客户端 | 无配置环境难以进行离线测试；宜延迟初始化并可注入客户端 |
| P2 | `backend/engines/executor.py` 按比例分配角色 token | 不是包含失败尝试、重试和裁判的严格总计费账本 |
| P2 | `backend/tools/` 搜索、浏览器与代码执行为骨架 | README 应区分架构预留与已实现能力 |
| P2 | `backend/engines/council.py` 548 行 | 轮次、共识、压缩和路由可进一步拆分 |

## 验证

JSON 契约离线 unittest：2 tests，OK；全部 Python 文件语法检查通过；前端 Vite 构建通过。现有 API 模型测试未运行，避免产生未授权费用；未声明这些测试通过。Git 历史 Gitleaks：0 项。

本批没有部署服务、没有发布运行效果指标；完整运行验收还需网络工具、并发生命周期与总账验证。

## 依赖与发布判定

2026-10-06 使用 npm 官方 registry 执行 `npm audit --json`，当前锁文件报告 5 项高危。统计是依赖图告警，不等同于已证实的运行时可利用漏洞；需逐项分析暴露面。

**运行产品发布：NO-GO。** 本次仅提交源码审查、展示文档及隔离测试覆盖的修复，不发布安装包或公网服务。不能通过修改扫描阈值、强制 audit fix 或隐藏风险制造全绿。

### 依赖修复后的复核

经操作员批准执行兼容范围升级，前端锁文件重新解析，Vite 升级至 8.3.3。npm 官方 registry 审计从 5 项高危降至 0 项；`npm run build` 和 `tsc --noEmit` 均通过。前端包声明 ESM 与 Apache-2.0，并提供 typecheck 脚本。

`test_executor_mock.py` 在使用无效示例接口地址和占位密钥的隔离环境下执行，验证并发、依赖先后和增量复用通过；未调用收费模型，模拟耗时不能写成真实模型效率指标。JSON 输出回归测试通过。

上述依赖告警已解决，公网服务发布仍受未修复的认证与任务生命周期问题阻挡，不宣称整系统安全验收完成。

### Executor recovery regression (2026-10-07)

The previous cache keyed only selected agent fields, allowing reuse across changed goals/strategies and upstream inputs. It also propagated ordinary runner exceptions through the entire gather. Reuse now fingerprints execution inputs and dependencies, invalidates failed results plus downstream tasks, and catches ordinary task errors without leaking exception content. Cycles/unassigned dependencies fail before calling any runner. Offline tests exercise unchanged reuse, changed goal/strategy, failure/retry and invalid graphs; these checks do not assess model accuracy. Existing cached hashes naturally miss once after upgrade. Revert the executor commit to roll back; no persisted state migration.
