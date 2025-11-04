#!/bin/bash
# ==========================================
# CryptoSignal v6.6 一键部署脚本
# 用途：首次部署 - 环境检测、依赖安装、配置引导
# 使用场景：
#   1. 新服务器首次部署
#   2. 切换到新分支
#   3. 重置所有配置
# ==========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=============================================="
echo "🚀 CryptoSignal v6.6 一键部署"
echo "=============================================="
echo ""

# ==========================================
# 步骤1: 检测项目目录
# ==========================================
echo -e "${BLUE}📍 步骤1: 检测项目目录${NC}"
echo "=============================================="

if [ ! -d ~/cryptosignal ]; then
    echo -e "${YELLOW}⚠️  项目目录不存在，开始克隆仓库...${NC}"
    echo ""
    echo "请输入仓库URL（直接回车使用默认）:"
    read -p "仓库URL [https://github.com/FelixWayne0318/cryptosignal.git]: " REPO_URL
    REPO_URL=${REPO_URL:-https://github.com/FelixWayne0318/cryptosignal.git}

    echo ""
    echo "请输入要检出的分支（直接回车使用默认）:"
    read -p "分支名称 [claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8]: " BRANCH_NAME
    BRANCH_NAME=${BRANCH_NAME:-claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8}

    echo ""
    echo "正在克隆仓库..."
    cd ~
    git clone "$REPO_URL" cryptosignal
    cd cryptosignal
    git checkout "$BRANCH_NAME"
    echo -e "${GREEN}✅ 仓库克隆完成${NC}"
else
    echo -e "${GREEN}✅ 项目目录已存在${NC}"
    cd ~/cryptosignal

    # 检测当前分支
    CURRENT_BRANCH=$(git branch --show-current)
    echo "   当前分支: $CURRENT_BRANCH"

    # 拉取最新代码
    echo ""
    echo "是否拉取最新代码？(y/n)"
    read -p "拉取 [y]: " PULL_CODE
    PULL_CODE=${PULL_CODE:-y}

    if [ "$PULL_CODE" = "y" ] || [ "$PULL_CODE" = "Y" ]; then
        echo "正在拉取最新代码..."
        git fetch origin "$CURRENT_BRANCH"
        git pull origin "$CURRENT_BRANCH"
        echo -e "${GREEN}✅ 代码已更新${NC}"
    fi
fi

echo ""

# ==========================================
# 步骤2: 检测系统环境
# ==========================================
echo -e "${BLUE}📍 步骤2: 检测系统环境${NC}"
echo "=============================================="

# 检测Python3
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✅ Python3: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python3 未安装${NC}"
    echo "请先安装 Python 3.8+："
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    exit 1
fi

# 检测pip3
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✅ pip3 已安装${NC}"
else
    echo -e "${YELLOW}⚠️  pip3 未安装，尝试自动安装...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    else
        echo -e "${RED}❌ 无法自动安装 pip3，请手动安装${NC}"
        exit 1
    fi
fi

# 检测git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version 2>&1 | awk '{print $3}')
    echo -e "${GREEN}✅ git: $GIT_VERSION${NC}"
else
    echo -e "${RED}❌ git 未安装${NC}"
    echo "请先安装 git"
    exit 1
fi

# 检测screen
if command -v screen &> /dev/null; then
    echo -e "${GREEN}✅ screen 已安装（推荐）${NC}"
else
    echo -e "${YELLOW}⚠️  screen 未安装${NC}"
    echo "是否安装 screen？(推荐用于后台运行) (y/n)"
    read -p "安装 [y]: " INSTALL_SCREEN
    INSTALL_SCREEN=${INSTALL_SCREEN:-y}

    if [ "$INSTALL_SCREEN" = "y" ] || [ "$INSTALL_SCREEN" = "Y" ]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y screen
            echo -e "${GREEN}✅ screen 安装完成${NC}"
        fi
    fi
fi

echo ""

# ==========================================
# 步骤3: 安装Python依赖
# ==========================================
echo -e "${BLUE}📍 步骤3: 安装Python依赖${NC}"
echo "=============================================="

cd ~/cryptosignal

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt 不存在${NC}"
    exit 1
fi

echo "正在安装依赖包（可能需要几分钟）..."
pip3 install -r requirements.txt --quiet

# 验证关键依赖
python3 -c "import numpy, pandas, aiohttp, websockets" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 所有依赖安装成功${NC}"
else
    echo -e "${RED}❌ 依赖安装失败，请检查错误信息${NC}"
    exit 1
fi

echo ""

# ==========================================
# 步骤4: 配置 Binance API
# ==========================================
echo -e "${BLUE}📍 步骤4: 配置 Binance API${NC}"
echo "=============================================="

BINANCE_CONFIG="config/binance_credentials.json"

if [ -f "$BINANCE_CONFIG" ]; then
    # 检查是否已配置
    CONFIGURED=$(python3 -c "
import json
try:
    with open('$BINANCE_CONFIG') as f:
        bn = json.load(f).get('binance', {})
        if bn.get('api_key') and bn['api_key'] != 'YOUR_BINANCE_API_KEY_HERE':
            print('yes')
        else:
            print('no')
except:
    print('no')
" 2>/dev/null)

    if [ "$CONFIGURED" = "yes" ]; then
        echo -e "${GREEN}✅ Binance API 已配置${NC}"
        echo ""
        echo "是否重新配置？(y/n)"
        read -p "重新配置 [n]: " RECONFIG
        RECONFIG=${RECONFIG:-n}

        if [ "$RECONFIG" != "y" ] && [ "$RECONFIG" != "Y" ]; then
            echo "跳过配置"
            SKIP_BINANCE=1
        fi
    fi
fi

if [ -z "$SKIP_BINANCE" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 配置 Binance API 凭证"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "请前往 Binance Futures 获取 API Key："
    echo "https://www.binance.com/en/my/settings/api-management"
    echo ""
    echo "⚠️  权限要求：只读权限即可（不需要交易权限）"
    echo ""

    read -p "请输入 API Key: " API_KEY
    read -p "请输入 API Secret: " API_SECRET

    # 创建配置文件
    cat > "$BINANCE_CONFIG" <<EOF
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "$API_KEY",
    "api_secret": "$API_SECRET",
    "testnet": false,
    "_security": "只读权限API Key"
  }
}
EOF

    echo -e "${GREEN}✅ Binance API 配置完成${NC}"
fi

echo ""

# ==========================================
# 步骤5: 配置 Telegram
# ==========================================
echo -e "${BLUE}📍 步骤5: 配置 Telegram 通知${NC}"
echo "=============================================="

TELEGRAM_CONFIG="config/telegram.json"

if [ -f "$TELEGRAM_CONFIG" ]; then
    # 检查是否已配置
    CONFIGURED=$(python3 -c "
import json
try:
    with open('$TELEGRAM_CONFIG') as f:
        tg = json.load(f)
        if tg.get('bot_token') and tg.get('chat_id'):
            print('yes')
        else:
            print('no')
except:
    print('no')
" 2>/dev/null)

    if [ "$CONFIGURED" = "yes" ]; then
        echo -e "${GREEN}✅ Telegram 已配置${NC}"
        echo ""
        echo "是否重新配置？(y/n)"
        read -p "重新配置 [n]: " RECONFIG_TG
        RECONFIG_TG=${RECONFIG_TG:-n}

        if [ "$RECONFIG_TG" != "y" ] && [ "$RECONFIG_TG" != "Y" ]; then
            echo "跳过配置"
            SKIP_TELEGRAM=1
        fi
    fi
fi

if [ -z "$SKIP_TELEGRAM" ]; then
    echo ""
    echo "是否启用 Telegram 通知？(y/n)"
    read -p "启用 [y]: " ENABLE_TG
    ENABLE_TG=${ENABLE_TG:-y}

    if [ "$ENABLE_TG" = "y" ] || [ "$ENABLE_TG" = "Y" ]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📝 配置 Telegram Bot"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "步骤1: 创建 Bot"
        echo "  1. 在 Telegram 搜索 @BotFather"
        echo "  2. 发送 /newbot 创建新机器人"
        echo "  3. 获取 Bot Token"
        echo ""
        echo "步骤2: 获取 Chat ID"
        echo "  1. 创建一个频道或群组"
        echo "  2. 将 Bot 添加为管理员"
        echo "  3. 发送一条消息后访问："
        echo "     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
        echo "  4. 找到 \"chat\":{\"id\":-1001234567890}"
        echo ""

        read -p "请输入 Bot Token: " BOT_TOKEN
        read -p "请输入 Chat ID: " CHAT_ID

        # 创建配置文件
        cat > "$TELEGRAM_CONFIG" <<EOF
{
  "enabled": true,
  "bot_token": "$BOT_TOKEN",
  "chat_id": "$CHAT_ID",
  "_comment": "Telegram Bot 配置"
}
EOF

        echo -e "${GREEN}✅ Telegram 配置完成${NC}"
    else
        # 创建禁用的配置
        cat > "$TELEGRAM_CONFIG" <<EOF
{
  "enabled": false,
  "bot_token": "",
  "chat_id": "",
  "_comment": "Telegram 通知已禁用"
}
EOF
        echo -e "${YELLOW}⚠️  Telegram 通知已禁用${NC}"
    fi
fi

echo ""

# ==========================================
# 步骤6: 配置 Crontab（自动重启）
# ==========================================
echo -e "${BLUE}📍 步骤6: 配置定时任务（自动重启）${NC}"
echo "=============================================="

echo "是否配置自动重启？(推荐每2小时重启) (y/n)"
read -p "配置 [y]: " SETUP_CRON
SETUP_CRON=${SETUP_CRON:-y}

if [ "$SETUP_CRON" = "y" ] || [ "$SETUP_CRON" = "Y" ]; then
    # 备份现有crontab
    crontab -l > ~/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true

    # 检查是否已经配置
    CRON_EXISTS=$(crontab -l 2>/dev/null | grep -c "auto_restart.sh" || echo "0")

    if [ "$CRON_EXISTS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  定时任务已存在${NC}"
        echo ""
        echo "是否覆盖？(y/n)"
        read -p "覆盖 [n]: " OVERWRITE_CRON
        OVERWRITE_CRON=${OVERWRITE_CRON:-n}

        if [ "$OVERWRITE_CRON" != "y" ] && [ "$OVERWRITE_CRON" != "Y" ]; then
            echo "保留现有配置"
            SKIP_CRON=1
        fi
    fi

    if [ -z "$SKIP_CRON" ]; then
        # 创建新的crontab
        (crontab -l 2>/dev/null | grep -v "auto_restart.sh" | grep -v "cryptosignal_.*\.log"; echo "# CryptoSignal v6.6 自动重启"; echo "0 */2 * * * ~/cryptosignal/auto_restart.sh"; echo "# 每天凌晨1点清理7天前的日志"; echo "0 1 * * * find ~ -name \"cryptosignal_*.log\" -mtime +7 -delete") | crontab -

        echo -e "${GREEN}✅ 定时任务配置完成${NC}"
        echo "   - 每2小时自动重启"
        echo "   - 每天清理旧日志"
    fi
else
    echo "跳过定时任务配置"
fi

echo ""

# ==========================================
# 步骤7: 添加执行权限
# ==========================================
echo -e "${BLUE}📍 步骤7: 添加脚本执行权限${NC}"
echo "=============================================="

cd ~/cryptosignal
chmod +x auto_restart.sh 2>/dev/null || true
chmod +x deploy_and_run.sh 2>/dev/null || true
chmod +x setup.sh 2>/dev/null || true

echo -e "${GREEN}✅ 执行权限已添加${NC}"
echo ""

# ==========================================
# 步骤8: 启动系统
# ==========================================
echo -e "${BLUE}📍 步骤8: 启动系统${NC}"
echo "=============================================="

echo ""
echo "是否现在启动系统？(y/n)"
read -p "启动 [y]: " START_NOW
START_NOW=${START_NOW:-y}

if [ "$START_NOW" = "y" ] || [ "$START_NOW" = "Y" ]; then
    echo ""
    echo "正在启动系统..."
    ./deploy_and_run.sh

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ CryptoSignal v6.6 部署完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "📊 系统状态："
    echo "   - 后台运行: Screen Detached"
    echo "   - 扫描间隔: 每5分钟"
    echo "   - 自动重启: 每2小时"
    echo ""
    echo "🔧 管理命令："
    echo "   查看日志: tail -f ~/cryptosignal/logs/scanner_*.log"
    echo "   重连会话: screen -r cryptosignal"
    echo "   手动重启: ~/cryptosignal/auto_restart.sh"
    echo "   查看状态: screen -ls"
    echo ""
else
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ CryptoSignal v6.6 配置完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "📝 下一步："
    echo "   启动系统: ~/cryptosignal/deploy_and_run.sh"
    echo "   或者: ~/cryptosignal/auto_restart.sh"
    echo ""
fi
