#!/usr/bin/env bash
# 在服务器上设置Telegram配置

set -euo pipefail

echo "======================================================================"
echo "📱 设置Telegram配置"
echo "======================================================================"
echo ""

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

ENV_FILE=".env.telegram"

# 检查是否已存在配置
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  发现已存在的Telegram配置文件"
    echo ""
    cat "$ENV_FILE"
    echo ""
    read -p "是否覆盖? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 0
    fi
fi

# 创建配置文件
echo "📝 创建Telegram配置文件..."
cat > "$ENV_FILE" << 'EOF'
# Telegram配置
export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
export TELEGRAM_CHAT_ID="-1003142003085"
EOF

# 设置安全权限
chmod 600 "$ENV_FILE"

echo "✅ 配置文件已创建: $ENV_FILE"
echo ""

# 加载配置
source "$ENV_FILE"

# 验证配置
echo "🔍 验证配置..."
echo "  Bot Token: ${TELEGRAM_BOT_TOKEN:0:20}..."
echo "  Chat ID: $TELEGRAM_CHAT_ID"
echo ""

# 测试Telegram连接
echo "🧪 测试Telegram Bot连接..."
TEST_RESULT=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | grep -o '"ok":true' || echo "")

if [ -n "$TEST_RESULT" ]; then
    echo "  ✅ Bot连接正常"
else
    echo "  ⚠️  Bot连接测试失败（可能是网络问题）"
fi

echo ""
echo "======================================================================"
echo "✅ Telegram配置完成！"
echo "======================================================================"
echo ""
echo "使用方法:"
echo "  source .env.telegram"
echo ""
echo "验证:"
echo "  echo \$TELEGRAM_BOT_TOKEN"
echo "  echo \$TELEGRAM_CHAT_ID"
echo ""
