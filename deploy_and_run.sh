#!/bin/bash
# coding: utf-8
# CryptoSignal v6.0 部署和运行脚本

set -e  # 遇到错误立即退出

echo "========================================"
echo "🚀 CryptoSignal v6.0 部署和运行"
echo "========================================"

# 1. 切换到项目目录
PROJECT_DIR="/home/user/cryptosignal"
cd "$PROJECT_DIR"

echo ""
echo "📂 当前目录: $(pwd)"
echo ""

# 2. 拉取最新代码
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 步骤1: 从远程仓库拉取最新代码"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 显示当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "   当前分支: $CURRENT_BRANCH"

# 拉取最新代码
echo "   正在拉取最新代码..."
git fetch origin

# 如果在claude分支上，拉取该分支
if [[ "$CURRENT_BRANCH" == claude/* ]]; then
    echo "   检测到Claude分支，拉取分支更新..."
    git pull origin "$CURRENT_BRANCH"
else
    echo "   拉取main分支更新..."
    git pull origin main
fi

# 显示最新提交
echo ""
echo "   最新提交:"
git log -1 --oneline
echo ""

# 3. 检查Python环境
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 步骤2: 检查Python环境"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1)
echo "   Python版本: $PYTHON_VERSION"

# 检查必要依赖
echo "   检查依赖包..."
REQUIRED_PACKAGES=("numpy" "pandas" "websockets" "aiohttp")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo ""
    echo "   ⚠️  缺少以下依赖包: ${MISSING_PACKAGES[*]}"
    echo "   正在安装..."
    pip3 install "${MISSING_PACKAGES[@]}"
else
    echo "   ✅ 所有依赖包已安装"
fi

echo ""

# 4. 检查Telegram配置
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 步骤3: 检查Telegram配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TELEGRAM_CONFIG="$PROJECT_DIR/config/telegram.json"

if [ -f "$TELEGRAM_CONFIG" ]; then
    echo "   ✅ 找到配置文件: $TELEGRAM_CONFIG"

    # 读取并验证配置
    BOT_TOKEN=$(python3 -c "import json; f=open('$TELEGRAM_CONFIG'); c=json.load(f); print(c.get('bot_token', ''))" 2>/dev/null || echo "")
    CHAT_ID=$(python3 -c "import json; f=open('$TELEGRAM_CONFIG'); c=json.load(f); print(c.get('chat_id', ''))" 2>/dev/null || echo "")

    if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
        echo "   ⚠️  配置文件存在但内容不完整"
        echo ""
        echo "   请编辑 $TELEGRAM_CONFIG，填写以下内容:"
        echo '   {'
        echo '     "bot_token": "YOUR_BOT_TOKEN",'
        echo '     "chat_id": "YOUR_CHAT_ID"'
        echo '   }'
        echo ""
        read -p "   配置完成后按Enter继续，或Ctrl+C退出..."
    else
        echo "   ✅ Telegram配置验证通过"
        echo "   Bot Token: ${BOT_TOKEN:0:10}..."
        echo "   Chat ID: $CHAT_ID"
    fi
else
    echo "   ⚠️  未找到配置文件: $TELEGRAM_CONFIG"
    echo ""
    echo "   创建配置模板..."

    mkdir -p "$(dirname "$TELEGRAM_CONFIG")"
    cat > "$TELEGRAM_CONFIG" << 'EOF'
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "chat_id": "YOUR_CHAT_ID_HERE"
}
EOF

    echo "   ✅ 已创建配置模板: $TELEGRAM_CONFIG"
    echo ""
    echo "   请使用以下命令编辑配置:"
    echo "   nano $TELEGRAM_CONFIG"
    echo ""
    echo "   填写你的Telegram Bot Token和Chat ID后继续"
    echo ""
    read -p "   配置完成后按Enter继续，或Ctrl+C退出..."
fi

echo ""

# 5. 显示运行选项
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 步骤4: 选择运行模式"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   1. 单次扫描（测试模式，扫描20个币种）"
echo "   2. 单次扫描（完整模式，扫描200个币种）"
echo "   3. 定期扫描（每5分钟扫描一次）"
echo "   4. 定期扫描（每15分钟扫描一次）"
echo "   5. 自定义参数运行"
echo ""
read -p "   请选择 [1-5]: " MODE

case $MODE in
    1)
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🧪 测试模式: 单次扫描20个币种"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        python3 scripts/realtime_signal_scanner.py --max-symbols 20
        ;;
    2)
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🚀 完整模式: 单次扫描200个币种"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        python3 scripts/realtime_signal_scanner.py
        ;;
    3)
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🔄 定期扫描模式: 每5分钟扫描一次"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "   (按Ctrl+C停止)"
        python3 scripts/realtime_signal_scanner.py --interval 300
        ;;
    4)
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🔄 定期扫描模式: 每15分钟扫描一次"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "   (按Ctrl+C停止)"
        python3 scripts/realtime_signal_scanner.py --interval 900
        ;;
    5)
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⚙️  自定义参数运行"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        read -p "   扫描间隔（秒，0=单次）: " INTERVAL
        read -p "   最低分数（默认70）: " MIN_SCORE
        read -p "   最大币种数（留空=200）: " MAX_SYMBOLS

        CMD="python3 scripts/realtime_signal_scanner.py"

        if [ ! -z "$INTERVAL" ]; then
            CMD="$CMD --interval $INTERVAL"
        fi

        if [ ! -z "$MIN_SCORE" ]; then
            CMD="$CMD --min-score $MIN_SCORE"
        fi

        if [ ! -z "$MAX_SYMBOLS" ]; then
            CMD="$CMD --max-symbols $MAX_SYMBOLS"
        fi

        echo ""
        echo "   执行命令: $CMD"
        echo ""
        $CMD
        ;;
    *)
        echo "   ❌ 无效选择，退出"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 运行完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
