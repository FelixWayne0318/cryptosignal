#!/bin/bash
# 配置Telegram凭据（生产环境）
# 此脚本在服务器上执行，创建.env文件

cd ~/cryptosignal

echo "======================================"
echo "配置Telegram凭据"
echo "======================================"

# 创建.env文件
cat > .env << 'EOF'
# Telegram配置
export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
export TELEGRAM_CHAT_ID="-1003142003085"
EOF

echo "✅ .env文件已创建：~/cryptosignal/.env"
echo ""

# 验证.env不在git中
if grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo "✅ .env已在.gitignore中，不会提交到Git"
else
    echo "⚠️  警告：.env未在.gitignore中"
fi

echo ""
echo "======================================"
echo "使用方法："
echo "======================================"
echo ""
echo "1. 加载环境变量："
echo "   source ~/cryptosignal/.env"
echo ""
echo "2. 运行分析并发送："
echo "   cd ~/cryptosignal"
echo "   python3 tools/manual_run.py --send --top 10"
echo ""
echo "3. 永久生效（可选）："
echo "   echo 'source ~/cryptosignal/.env' >> ~/.bashrc"
echo "   source ~/.bashrc"
echo ""
echo "======================================"
echo "测试发送"
echo "======================================"
echo ""

# 加载环境变量
source .env

# 验证配置
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN 未设置"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "❌ TELEGRAM_CHAT_ID 未设置"
    exit 1
fi

echo "✅ TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:20}..."
echo "✅ TELEGRAM_CHAT_ID: $TELEGRAM_CHAT_ID"
echo ""

read -p "是否现在测试发送？(y/n): " answer

if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    echo ""
    echo "测试发送前3个币种..."
    python3 tools/manual_run.py --send --top 3
else
    echo "跳过测试"
fi
