> 网页五个阶段为静态示例，不连接运行引擎；后台运行使用 REST API。

# Genesis Hive 使用指南

安装步骤见 [README](../README.md#本地运行)。本指南只补充配置、操作和排障。

## 配置

在仓库根目录将 `.env.example` 复制为 `.env`，在编辑器中填写：

| 变量 | 用途 |
|---|---|
| `OPENROUTER_API_KEY` | 模型服务凭据 |
| `OPENROUTER_BASE_URL` | OpenRouter 兼容接口地址 |
| `MODEL_RESEARCH` / `MODEL_ANALYSIS` | 调研与分析角色模型 |
| `MODEL_ADVERSARY` | 质疑角色模型 |
| `MODEL_META` / `MODEL_JUDGE` / `MODEL_COMPRESS` | 编排、裁判与摘要模型 |
| `DEFAULT_MODE` | `demo`、`standard` 或 `deep` |
| `TOKEN_BUDGET_*` | 各运行模式的预算配置 |

模型 ID 应在供应商端可用。预算配置不等于已经验证的供应商费用硬顶；先用小任务确认实际调用和费用。

## 使用界面

1. 在两个终端分别启动后端与前端，保持两者运行。
2. 打开 Vite 输出的本地 URL，输入明确目标并选择模式。
3. 观察任务分解、角色执行、讨论和最终报告；一次只发起一个任务。
4. 保存需要的结果。运行状态在内存中，重启进程不会恢复之前的任务。

提交目标会调用外部模型。不要输入无法向相应模型服务披露的资料。

## 接口

后端默认运行于 `http://127.0.0.1:8000`，Swagger 位于 `/docs`。

| 路径 | 功能 |
|---|---|
| `GET /health` | 进程健康 |
| `POST /api/run` | 提交 `goal`、`mode` 启动模型流程 |
| `GET /api/status` | 查看当前进度或错误 |
| `GET /api/report` | 读取已完成的报告 |
| `/ws` | 接收进度事件 |

`started` 只表示接收了任务，最终完成状态以 `/api/status` 和报告为准。服务没有公网认证，应只在可信本地环境使用。

## 常见问题

- 前端无法连接：检查后端是否在 8000 端口运行，Vite 的代理目标是否一致。
- 模型调用失败：核对密钥、模型 ID、供应商额度与服务日志，不要将凭据粘贴进 issue。
- 没有报告：任务可能仍在运行或已失败，先查看状态和后端日志。
- 重启后任务消失：这是当前内存状态设计的行为，不是持久任务队列。

## 开发验证

```sh
python3 -B -m unittest discover -s tests -v
cd frontend
npm run typecheck
npm run build
```

`test_executor_mock.py` 用模拟执行验证任务依赖和结果复用；其他实验脚本可能调用真实模型。工具适配、并发占位和预算的剩余问题见 [代码审查](code-review.md)。
