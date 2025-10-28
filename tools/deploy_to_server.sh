#!/bin/bash
# 服务器快速部署脚本 - 链上望远镜Telegram信号推送

echo "============================================================"
echo "🔭 链上望远镜 - 服务器部署脚本"
echo "============================================================"
echo ""

# Step 1: 克隆或更新代码
echo "📥 Step 1: 获取最新代码..."
if [ -d "cryptosignal" ]; then
    echo "项目已存在，更新代码..."
    cd cryptosignal
    git fetch origin
    git checkout claude/review-candidate-pool-removal-011CUXvj6SL2naxNqykCbYKS
    git pull origin claude/review-candidate-pool-removal-011CUXvj6SL2naxNqykCbYKS
else
    echo "首次部署，克隆代码..."
    git clone https://github.com/FelixWayne0318/cryptosignal.git
    cd cryptosignal
    git checkout claude/review-candidate-pool-removal-011CUXvj6SL2naxNqykCbYKS
fi

echo "✅ 代码获取完成"
echo ""

# Step 2: 安装依赖
echo "📦 Step 2: 安装Python依赖..."
pip3 install numpy scipy 2>&1 | grep -E "(Successfully|already satisfied|Requirement)"
echo "✅ 依赖安装完成"
echo ""

# Step 3: 配置Telegram
echo "⚙️  Step 3: 配置Telegram..."
echo ""
echo "请提供以下信息:"
read -p "Bot Token (例: 123456789:ABCdef...): " BOT_TOKEN
read -p "Chat ID (默认: -1003142003085): " CHAT_ID

# 默认Chat ID
if [ -z "$CHAT_ID" ]; then
    CHAT_ID="-1003142003085"
fi

# 写入配置文件
cat > .env.telegram << EOF
# 链上望远镜 Telegram配置
export TELEGRAM_BOT_TOKEN="${BOT_TOKEN}"
export TELEGRAM_CHAT_ID="${CHAT_ID}"
EOF

echo "✅ 配置已保存到 .env.telegram"
echo ""

# Step 4: 测试发送
echo "🧪 Step 4: 测试Telegram发送..."
echo ""

source .env.telegram

# 测试Token有效性
echo "验证Bot Token..."
python3 << PYEOF
import urllib.request
import json

TOKEN = "${BOT_TOKEN}"
try:
    url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())
        if result.get('ok'):
            bot = result.get('result', {})
            print(f"✅ Bot验证成功: @{bot.get('username')}")
        else:
            print(f"❌ Bot验证失败: {result}")
except Exception as e:
    print(f"❌ 验证失败: {e}")
    print("请检查Token是否正确")
PYEOF

echo ""
read -p "是否发送测试信号？(y/n): " SEND_TEST

if [ "$SEND_TEST" = "y" ] || [ "$SEND_TEST" = "Y" ]; then
    echo "发送测试信号到 BTCUSDT..."
    python3 tools/send_signal_to_telescope.py BTCUSDT
    echo ""
fi

# Step 5: 设置定时任务（可选）
echo ""
echo "============================================================"
echo "✅ 部署完成！"
echo "============================================================"
echo ""
echo "📚 使用方法:"
echo ""
echo "1. 单币种分析:"
echo "   source .env.telegram"
echo "   python3 tools/send_signal_to_telescope.py BTCUSDT"
echo ""
echo "2. 批量扫描:"
echo "   source .env.telegram"
echo "   python3 tools/send_signal_to_telescope.py --batch --max 20"
echo ""
echo "3. 使用v3系统:"
echo "   python3 tools/send_signal_to_telescope.py BTCUSDT --v3"
echo ""
echo "4. 设置定时任务:"
echo "   crontab -e"
echo "   添加: 0 * * * * cd $(pwd) && source .env.telegram && python3 tools/send_signal_to_telescope.py --batch --max 20"
echo ""
echo "📖 详细文档:"
echo "   - 快速部署: docs/VULTR_DEPLOYMENT_QUICKSTART.md"
echo "   - 配置指南: docs/TELESCOPE_SETUP.md"
echo "   - v3实施总结: docs/V3_IMPLEMENTATION_SUMMARY.md"
echo ""
echo "🔭 链上望远镜群组: ${CHAT_ID}"
echo "============================================================"
