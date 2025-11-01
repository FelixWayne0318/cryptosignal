#!/bin/bash
# coding: utf-8
# CryptoSignal v6.0 生产环境运行脚本（每5分钟扫描）

set -e  # 遇到错误立即退出

echo "========================================"
echo "🚀 CryptoSignal v6.0 生产环境启动"
echo "========================================"
echo ""

# 1. 切换到项目目录
PROJECT_DIR="/home/user/cryptosignal"
cd "$PROJECT_DIR"

echo "📂 当前目录: $(pwd)"
echo ""

# 2. 拉取最新代码（包含v2.0多空对称性修复）
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 步骤1: 从远程仓库拉取最新代码"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 显示当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "   当前分支: $CURRENT_BRANCH"

# 拉取最新代码（v2.0多空对称性修复版本）
echo "   正在拉取最新代码..."
git fetch origin

# 拉取当前分支的最新代码
git pull origin "$CURRENT_BRANCH"

# 显示最新提交
echo ""
echo "   最新提交:"
git log -1 --oneline
git log -1 --pretty=format:"   提交者: %an <%ae>%n   时间: %ad%n   信息: %s" --date=format:"%Y-%m-%d %H:%M:%S"
echo ""
echo ""

# 验证v2.0修复是否存在
echo "   验证v2.0多空对称性修复..."
if grep -q "symmetry_fixed" ats_core/features/volume.py; then
    echo "   ✅ V因子v2.0修复已应用"
else
    echo "   ⚠️  警告: V因子v2.0修复未找到"
fi

if grep -q "symmetry_fixed" ats_core/features/open_interest.py; then
    echo "   ✅ O因子v2.0修复已应用"
else
    echo "   ⚠️  警告: O因子v2.0修复未找到"
fi

echo ""

# 3. 检查Python环境
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 步骤2: 检查Python环境"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PYTHON_VERSION=$(python3 --version 2>&1)
echo "   Python版本: $PYTHON_VERSION"
echo ""

# 4. 检查Telegram配置
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 步骤3: 检查Telegram配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TELEGRAM_CONFIG="$PROJECT_DIR/config/telegram.json"

if [ -f "$TELEGRAM_CONFIG" ]; then
    echo "   ✅ 配置文件存在: $TELEGRAM_CONFIG"

    # 验证配置内容
    BOT_TOKEN=$(python3 -c "import json; f=open('$TELEGRAM_CONFIG'); c=json.load(f); print(c.get('bot_token', ''))" 2>/dev/null || echo "")
    CHAT_ID=$(python3 -c "import json; f=open('$TELEGRAM_CONFIG'); c=json.load(f); print(c.get('chat_id', ''))" 2>/dev/null || echo "")

    if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
        echo "   ❌ 配置不完整，请编辑 $TELEGRAM_CONFIG"
        exit 1
    else
        echo "   ✅ Telegram配置完整"
        echo "   Bot Token: ${BOT_TOKEN:0:10}..."
        echo "   Chat ID: $CHAT_ID"
    fi
else
    echo "   ❌ 配置文件不存在: $TELEGRAM_CONFIG"
    echo ""
    echo "   请创建配置文件:"
    echo "   mkdir -p config"
    echo "   nano config/telegram.json"
    echo ""
    echo "   内容："
    echo '   {'
    echo '     "bot_token": "YOUR_BOT_TOKEN",'
    echo '     "chat_id": "YOUR_CHAT_ID"'
    echo '   }'
    exit 1
fi

echo ""

# 5. 显示系统信息
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 系统信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   版本: v6.0 (多空对称性修复版)"
echo "   扫描间隔: 5分钟"
echo "   最低分数: 70"
echo "   目标币种: 140个高流动性USDT合约"
echo "   选币标准: 24h成交额 >= 3M USDT"
echo "   多空对称: ✅ V和O因子已修复（v2.0）"
echo "   信号类型: 爆发型（放量+波动）"
echo ""
echo "   预期性能:"
echo "   - 初始化: 3-4分钟（仅首次）"
echo "   - 扫描时间: 12-15秒/次"
echo "   - API调用: 0次/扫描（WebSocket缓存）"
echo "   - 信号数量: 10-30个/天（估计）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 6. 询问是否简化输出
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 输出模式选择"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "默认模式: 显示所有140个币种的详细因子评分和四门调节器值"
echo "简化模式: 只显示前10个币种的详细评分（减少日志输出）"
echo ""
read -p "使用简化输出模式？(y/N): " SIMPLE_CHOICE

VERBOSE_FLAG=""
if [[ "$SIMPLE_CHOICE" == "y" || "$SIMPLE_CHOICE" == "Y" ]]; then
    VERBOSE_FLAG="--no-verbose"
    echo "   ✅ 将使用简化输出模式（只显示前10个币种）"
else
    echo "   ✅ 将使用默认输出模式（显示所有140个币种）"
fi

echo ""

# 7. 最后确认
echo "⚠️  准备启动生产环境扫描器..."
echo ""
echo "按 Ctrl+C 可以随时停止"
echo "按 Enter 继续启动..."
read -p ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 启动实时信号扫描器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 8. 启动扫描器
python3 scripts/realtime_signal_scanner.py \
    --interval 300 \
    --min-score 70 \
    $VERBOSE_FLAG

# 脚本结束
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 扫描器已停止"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
