#!/bin/bash
# 本地部署脚本 - 推送代码并在服务器上更新
# 使用方法: bash scripts/deploy_to_server.sh

set -e

echo "=========================================="
echo "🚀 CryptoSignal 完整部署流程"
echo "=========================================="

# ============================================
# 1. 检查是否在正确的目录
# ============================================
if [ ! -f "scripts/server_update.sh" ]; then
    echo "❌ 错误: 请在cryptosignal项目根目录下运行此脚本"
    echo "用法: cd ~/cryptosignal && bash scripts/deploy_to_server.sh"
    exit 1
fi

CURRENT_DIR=$(pwd)
echo "📂 当前目录: $CURRENT_DIR"
echo "🌿 当前分支: $(git branch --show-current)"

# ============================================
# 2. 检查是否有未提交的更改
# ============================================
echo ""
echo "1️⃣  检查代码状态..."
echo "=========================================="

if ! git diff-index --quiet HEAD --; then
    echo "⚠️  发现未提交的更改:"
    git status --short
    echo ""
    read -p "是否自动提交这些更改? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📝 提交更改..."
        git add -A
        git commit -m "chore: 自动提交部署前的更改

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
        echo "✅ 更改已提交"
    else
        echo "❌ 取消部署"
        exit 1
    fi
else
    echo "✅ 工作目录干净"
fi

# ============================================
# 3. 推送到远程仓库
# ============================================
echo ""
echo "2️⃣  推送代码到远程..."
echo "=========================================="

BRANCH=$(git branch --show-current)
echo "📤 推送分支: $BRANCH"

# 推送代码
if git push origin "$BRANCH"; then
    echo "✅ 代码已推送到远程"
else
    echo "❌ 代码推送失败"
    exit 1
fi

LATEST_COMMIT=$(git log -1 --oneline)
echo "✅ 最新提交: $LATEST_COMMIT"

# ============================================
# 4. 复制更新脚本到临时目录
# ============================================
echo ""
echo "3️⃣  准备服务器更新脚本..."
echo "=========================================="

# 将更新脚本复制到/tmp，避免在删除目录时丢失
cp scripts/server_update.sh /tmp/cryptosignal_update.sh
chmod +x /tmp/cryptosignal_update.sh
echo "✅ 更新脚本已复制到 /tmp/cryptosignal_update.sh"

# ============================================
# 5. 执行服务器更新
# ============================================
echo ""
echo "4️⃣  执行服务器更新..."
echo "=========================================="
echo "⚠️  注意: 即将删除当前目录并重新克隆代码"
echo "⚠️  脚本将从 /tmp 目录执行，确保安全"
echo ""

# 切换到/tmp并执行更新脚本
cd /tmp
bash /tmp/cryptosignal_update.sh

UPDATE_EXIT_CODE=$?

# ============================================
# 6. 完成
# ============================================
echo ""
echo "=========================================="
if [ $UPDATE_EXIT_CODE -eq 0 ]; then
    echo "✅ 部署成功完成！"
    echo ""
    echo "📍 新的代码位置: ~/cryptosignal"
    echo "📝 您现在可以: cd ~/cryptosignal"
else
    echo "❌ 部署失败，退出码: $UPDATE_EXIT_CODE"
    echo "📝 请检查上面的错误信息"
fi
echo "=========================================="

exit $UPDATE_EXIT_CODE
