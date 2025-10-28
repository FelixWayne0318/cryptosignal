#!/usr/bin/env bash
# 部署WebSocket信号扫描器到服务器

set -euo pipefail

echo "======================================================================"
echo "🚀 部署WebSocket信号扫描器"
echo "======================================================================"
echo ""

# 进入项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

# 1. 备份当前代码（如果有修改）
echo "1️⃣  备份当前代码..."
if [ -n "$(git status --porcelain)" ]; then
    echo "   发现未提交的修改，创建备份..."
    git stash save "backup-$(date +%Y%m%d-%H%M%S)"
    echo "   ✅ 备份完成"
else
    echo "   ✅ 无需备份（工作区干净）"
fi

# 2. 拉取最新代码
echo ""
echo "2️⃣  拉取最新代码..."
BRANCH=$(git branch --show-current)
echo "   当前分支: $BRANCH"

git fetch origin
git pull origin "$BRANCH"

echo "   ✅ 代码已更新"

# 3. 检查新增文件
echo ""
echo "3️⃣  检查新增文件..."
echo ""
echo "   WebSocket信号扫描器相关文件:"
echo "   ✅ scripts/realtime_signal_scanner.py"
ls -lh scripts/realtime_signal_scanner.py 2>/dev/null || echo "   ❌ 文件不存在"

echo "   ✅ scripts/start_signal_scanner.sh"
ls -lh scripts/start_signal_scanner.sh 2>/dev/null || echo "   ❌ 文件不存在"

echo "   ✅ ats_core/pipeline/batch_scan_optimized.py (已更新)"
ls -lh ats_core/pipeline/batch_scan_optimized.py 2>/dev/null || echo "   ❌ 文件不存在"

echo "   ✅ docs/WEBSOCKET_SIGNAL_SCANNER_GUIDE.md"
ls -lh docs/WEBSOCKET_SIGNAL_SCANNER_GUIDE.md 2>/dev/null || echo "   ❌ 文件不存在"

# 4. 确保脚本可执行
echo ""
echo "4️⃣  设置文件权限..."
chmod +x scripts/realtime_signal_scanner.py
chmod +x scripts/start_signal_scanner.sh
echo "   ✅ 权限已设置"

# 5. 检查环境变量
echo ""
echo "5️⃣  检查环境变量..."
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "   ⚠️  TELEGRAM_BOT_TOKEN 未设置"
    echo "   请执行: export TELEGRAM_BOT_TOKEN='your_token'"
else
    echo "   ✅ TELEGRAM_BOT_TOKEN 已设置"
fi

if [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "   ⚠️  TELEGRAM_CHAT_ID 未设置"
    echo "   请执行: export TELEGRAM_CHAT_ID='your_chat_id'"
else
    echo "   ✅ TELEGRAM_CHAT_ID 已设置"
fi

echo ""
echo "======================================================================"
echo "✅ 部署完成！"
echo "======================================================================"
echo ""
echo "测试命令:"
echo "  1. 快速测试（20个币种）:"
echo "     python scripts/realtime_signal_scanner.py --max-symbols 20 --no-telegram"
echo ""
echo "  2. 完整测试（200个币种，不发Telegram）:"
echo "     python scripts/realtime_signal_scanner.py --no-telegram"
echo ""
echo "  3. 生产运行（发送Telegram）:"
echo "     ./scripts/start_signal_scanner.sh"
echo ""
echo "======================================================================"
