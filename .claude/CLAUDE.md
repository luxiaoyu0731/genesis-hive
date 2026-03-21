# Genesis Hive — Claude Code 行为准则

## 项目概述

Genesis Hive 是一个自进化多Agent智能体系统。技术栈：Python + FastAPI + LangGraph（后端），React + TypeScript + D3.js（前端）。详细架构和开发步骤见 `SKILL.md`。

## 绝对禁止的操作

以下操作在任何情况下都不允许执行，即使看起来合理也不行：

- 删除任何文件或目录（rm、rmdir、shred、unlink、os.remove、shutil.rmtree）
- 清空文件内容（truncate、> file）
- 破坏性 git 操作（reset --hard、push --force、clean -f、checkout -- .）
- 修改系统级文件（/etc/、/usr/、/var/ 下的任何东西）
- 终止系统进程（pkill、killall、systemctl stop）
- 卸载软件包（pip uninstall、npm uninstall -g、apt-get remove）

如果开发过程中确实需要删除文件（比如重构后移除旧文件），请停下来告诉我，由我手动执行。

## 需要替代方案的场景

遇到以下情况时，用安全的替代方式处理：

- 需要"删除并重建"某个文件 → 直接覆盖写入（Write tool），不要先删后建
- 需要清理 node_modules 或 __pycache__ → 告诉我手动清理，不要自己 rm -rf
- 需要回滚 git 变更 → 用 `git revert` 创建新提交，不要用 `git reset --hard`
- 需要替换整个文件内容 → 用 Write tool 覆盖，不要 truncate + 重写
- 需要重命名文件 → 用 `mv`（已在白名单中），不要 cp + rm

## 可以自主执行的操作

以下操作不需要问我，直接做：

- 创建新文件和新目录
- 编辑现有文件内容
- 安装新依赖（npm install、pip install）
- 运行测试和构建（pytest、npm test、npm run build）
- 读取和搜索代码
- git add、commit、push（非 force）
- 启动开发服务器

## 开发规范

- 每完成一个 Step（L1-L5 引擎），跑一遍 SKILL.md 中"开发阶段自检流程"的 6 项检查
- 遇到 SKILL.md 中"已知风险登记簿"记载的问题时，按已有修复方案处理
- 发现新的潜在风险时，记录到"待观察的潜在风险"表格中，并告知我
- LangGraph 相关：使用 Command API 做动态路由，轮次间重编译实现团队重组，不要尝试运行时添加节点
- 共识检测：使用裁判 LLM 方案，不要使用 cosine similarity
- 辩论历史每轮结束后必须压缩为摘要再传入下一轮

## 代码风格

- Python：遵循 PEP 8，类型标注（TypedDict、Literal），async/await 用于 IO 操作
- TypeScript/React：函数组件 + Hooks，Tailwind CSS，严格模式
- 变量命名：英文，snake_case（Python）/ camelCase（TypeScript）
- 注释语言：中文注释，英文代码
- commit message：英文，conventional commits 格式
