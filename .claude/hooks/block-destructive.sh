#!/bin/bash
# Genesis Hive — PreToolUse Hook
# 最后一道防线：用正则拦截所有破坏性命令
# 即使 settings.json 的 deny 规则被绕过（比如通过管道、变量拼接），这里也能兜住

set -e

# 从 stdin 读取 Claude Code 传入的 JSON
INPUT=$(cat)

# 提取 tool 名和命令内容
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 只检查 Bash 类工具
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

# 如果没有命令内容，放行
if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# ============================================
# 危险命令模式列表（正则匹配）
# ============================================
DANGEROUS_PATTERNS=(
  # 文件删除
  '\brm\b'
  '\brmdir\b'
  '\bunlink\b'
  '\bshred\b'
  '\btruncate\b'

  # 磁盘/格式化
  '\bdd\b\s+if='
  '\bmkfs\b'
  '\bformat\b'

  # 破坏性 git
  'git\s+reset\s+--hard'
  'git\s+clean\s+-[a-zA-Z]*f'
  'git\s+push\s+--force'
  'git\s+push\s+-f\b'
  'git\s+checkout\s+--\s'

  # Python 删除操作（防止通过 python -c 绕过）
  'os\.remove'
  'os\.unlink'
  'os\.rmdir'
  'shutil\.rmtree'
  'pathlib.*\.unlink'
  'pathlib.*\.rmdir'

  # 系统操作
  '\bsudo\s+rm\b'
  '\bsudo\s+dd\b'
  '\bsudo\s+reboot\b'
  '\bsudo\s+shutdown\b'
  '\bsudo\s+halt\b'
  '\bsudo\s+poweroff\b'
  '\bpkill\b'
  '\bkillall\b'

  # 卸载
  'pip[3]?\s+uninstall'
  'npm\s+uninstall\s+-g'
  'apt-get\s+(remove|purge|autoremove)'
  'brew\s+(uninstall|remove)'

  # 重定向清空文件
  '>\s*[a-zA-Z_/]'
)

# ============================================
# 逐一匹配
# ============================================
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qP "$pattern"; then
    # exit 2 = 阻止执行并显示原因
    echo "🚫 安全拦截：检测到危险命令模式 [$pattern]" >&2
    echo "被拦截的命令：$COMMAND" >&2
    echo "如果确实需要执行此操作，请手动在终端中运行。" >&2
    exit 2
  fi
done

# 所有检查通过，放行
exit 0
