#!/bin/bash
#
# 服务器完整配置脚本
# 用途：新服务器或分支切换后，一键配置所有敏感信息
# 使用：bash scripts/setup_server_config.sh
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🔧 CryptoSignal 服务器完整配置"
echo "=========================================="
echo ""
echo "本脚本将配置以下内容："
echo "  1. GitHub访问权限（自动推送报告）"
echo "  2. Binance API凭证（获取行情数据）"
echo "  3. Telegram通知配置（可选，发送信号）"
echo "  4. 定时任务（每2小时自动重启）"
echo ""

# ==========================================
# 配置1：GitHub访问权限
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}配置1/4: GitHub访问权限${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

GITHUB_CONFIG="$HOME/.cryptosignal-github.env"

if [ -f "$GITHUB_CONFIG" ]; then
    echo -e "${GREEN}✅ GitHub配置已存在${NC}"
    cat "$GITHUB_CONFIG"
    echo ""
    read -p "是否重新配置？(y/N): " RECONFIGURE
    if [[ ! $RECONFIGURE =~ ^[Yy]$ ]]; then
        echo "保留现有配置"
    else
        rm "$GITHUB_CONFIG"
    fi
fi

if [ ! -f "$GITHUB_CONFIG" ]; then
    echo "请输入GitHub配置信息："
    echo ""

    read -p "Git用户名 (如: FelixWayne0318): " GIT_USER_NAME
    read -p "Git邮箱 (如: felixwayne0318@gmail.com): " GIT_USER_EMAIL
    read -p "GitHub Token (如: ghp_xxx...): " GITHUB_TOKEN

    cat > "$GITHUB_CONFIG" <<EOF
# CryptoSignal GitHub访问配置
GIT_USER_NAME="$GIT_USER_NAME"
GIT_USER_EMAIL="$GIT_USER_EMAIL"
GITHUB_TOKEN="$GITHUB_TOKEN"
EOF

    chmod 600 "$GITHUB_CONFIG"
    echo ""
    echo -e "${GREEN}✅ GitHub配置已保存${NC}"
fi

# 应用Git配置
source "$GITHUB_CONFIG"
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
git config --global credential.helper store

# 配置凭证文件
if [ -n "$GITHUB_TOKEN" ]; then
    REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ $REPO_URL == https://github.com/* ]]; then
        GITHUB_USER=$(echo "$REPO_URL" | sed -n 's#https://github.com/\([^/]*\)/.*#\1#p')
        echo "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com" > "$HOME/.git-credentials"
        chmod 600 "$HOME/.git-credentials"
    fi
fi

echo ""

# ==========================================
# 配置2：Binance API凭证
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}配置2/4: Binance API凭证${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

BINANCE_CONFIG="$HOME/cryptosignal/config/binance_credentials.json"

if [ -f "$BINANCE_CONFIG" ]; then
    echo -e "${GREEN}✅ Binance配置已存在${NC}"
    # 显示脱敏后的API Key
    API_KEY=$(grep -o '"api_key": "[^"]*"' "$BINANCE_CONFIG" | cut -d'"' -f4)
    echo "API Key: ${API_KEY:0:8}...${API_KEY: -8}"
    echo ""
    read -p "是否重新配置？(y/N): " RECONFIGURE
    if [[ ! $RECONFIGURE =~ ^[Yy]$ ]]; then
        echo "保留现有配置"
    else
        rm "$BINANCE_CONFIG"
    fi
fi

if [ ! -f "$BINANCE_CONFIG" ]; then
    echo "请输入Binance API凭证："
    echo ""
    echo "💡 提示："
    echo "  1. 访问 https://www.binance.com/en/my/settings/api-management"
    echo "  2. 创建API Key，只需勾选'读取'权限"
    echo "  3. 复制API Key和Secret Key"
    echo ""

    read -p "API Key: " BINANCE_API_KEY
    read -p "Secret Key: " BINANCE_API_SECRET

    cat > "$BINANCE_CONFIG" <<EOF
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "$BINANCE_API_KEY",
    "api_secret": "$BINANCE_API_SECRET",
    "testnet": false,
    "_security": "只读权限API Key"
  }
}
EOF

    chmod 600 "$BINANCE_CONFIG"
    echo ""
    echo -e "${GREEN}✅ Binance配置已保存${NC}"
fi

echo ""

# ==========================================
# 配置3：Telegram通知（可选）
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}配置3/4: Telegram通知（可选）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

TELEGRAM_CONFIG="$HOME/cryptosignal/config/telegram.json"

if [ -f "$TELEGRAM_CONFIG" ]; then
    echo -e "${GREEN}✅ Telegram配置已存在${NC}"
    ENABLED=$(grep -o '"enabled": [^,]*' "$TELEGRAM_CONFIG" | cut -d' ' -f2)
    BOT_TOKEN=$(grep -o '"bot_token": "[^"]*"' "$TELEGRAM_CONFIG" | cut -d'"' -f4)
    echo "状态: enabled=$ENABLED"
    echo "Bot Token: ${BOT_TOKEN:0:10}...${BOT_TOKEN: -10}"
    echo ""
    read -p "是否重新配置？(y/N): " RECONFIGURE
    if [[ ! $RECONFIGURE =~ ^[Yy]$ ]]; then
        echo "保留现有配置"
    else
        rm "$TELEGRAM_CONFIG"
    fi
fi

if [ ! -f "$TELEGRAM_CONFIG" ]; then
    read -p "是否启用Telegram通知？(y/N): " ENABLE_TELEGRAM

    if [[ $ENABLE_TELEGRAM =~ ^[Yy]$ ]]; then
        echo ""
        echo "💡 提示："
        echo "  1. 与@BotFather对话创建Bot，获取token"
        echo "  2. 将Bot添加到群组/频道"
        echo "  3. 访问 https://api.telegram.org/bot<TOKEN>/getUpdates 获取chat_id"
        echo ""

        read -p "Bot Token: " TELEGRAM_BOT_TOKEN
        read -p "Chat ID: " TELEGRAM_CHAT_ID

        cat > "$TELEGRAM_CONFIG" <<EOF
{
  "enabled": true,
  "bot_token": "$TELEGRAM_BOT_TOKEN",
  "chat_id": "$TELEGRAM_CHAT_ID",
  "_comment": "Telegram通知配置"
}
EOF
    else
        cat > "$TELEGRAM_CONFIG" <<EOF
{
  "enabled": false,
  "bot_token": "",
  "chat_id": "",
  "_comment": "Telegram通知已禁用"
}
EOF
    fi

    chmod 600 "$TELEGRAM_CONFIG"
    echo ""
    echo -e "${GREEN}✅ Telegram配置已保存${NC}"
fi

echo ""

# ==========================================
# 配置4：定时任务
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}配置4/4: 定时任务（每2小时重启）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if crontab -l 2>/dev/null | grep -q "auto_restart.sh"; then
    echo -e "${GREEN}✅ 定时任务已配置${NC}"
    echo ""
    echo "当前定时任务："
    crontab -l | grep "auto_restart.sh\|cryptosignal"
else
    echo "正在配置定时任务..."
    (crontab -l 2>/dev/null; echo ""; echo "# CryptoSignal自动重启"; echo "0 */2 * * * ~/cryptosignal/auto_restart.sh"; echo "0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete") | crontab -
    echo ""
    echo -e "${GREEN}✅ 定时任务已添加${NC}"
    echo "  • 每2小时自动重启: 0 */2 * * *"
    echo "  • 每天清理7天前日志: 0 1 * * *"
fi

echo ""

# ==========================================
# 配置完成
# ==========================================
echo "=========================================="
echo -e "${GREEN}✅ 服务器配置完成！${NC}"
echo "=========================================="
echo ""
echo "📋 配置摘要："
echo "  1. GitHub配置: $GITHUB_CONFIG"
echo "  2. Binance配置: $BINANCE_CONFIG"
echo "  3. Telegram配置: $TELEGRAM_CONFIG"
echo "  4. 定时任务: 已配置"
echo ""
echo "🚀 下一步："
echo "  cd ~/cryptosignal"
echo "  bash setup.sh"
echo ""
