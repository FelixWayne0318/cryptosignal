#!/bin/bash
# ==========================================
# CryptoSignal v7.4.0 精简部署脚本
# 适合手机Termius复制粘贴执行
# ==========================================
# 使用方法：
#   1. 填写下方【您的配置】区域
#   2. 全选复制整个脚本
#   3. 粘贴到Termius执行
# ==========================================

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【您的配置】- 请填写真实信息
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GITHUB_USER="YOUR_GITHUB_USERNAME"                     # 您的GitHub用户名
GITHUB_TOKEN="YOUR_GITHUB_TOKEN"                       # GitHub Token
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"                 # Binance API Key
BINANCE_API_SECRET="YOUR_BINANCE_API_SECRET"           # Binance API Secret

# 可选配置（一般不需要改）
GITHUB_REPO="cryptosignal"
GITHUB_BRANCH="main"
SERVER_TIMEZONE="Asia/Singapore"
TELEGRAM_ENABLED="false"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
print_step() { echo -e "\n${GREEN}━━━ $1 ━━━${NC}\n"; }
print_ok() { echo -e "${GREEN}✅ $1${NC}"; }
print_err() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# 检查配置
[ "$GITHUB_TOKEN" = "YOUR_GITHUB_TOKEN" ] && print_err "请先填写GITHUB_TOKEN"
[ "$BINANCE_API_KEY" = "YOUR_BINANCE_API_KEY" ] && print_err "请先填写BINANCE_API_KEY"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  CryptoSignal v7.4.0 部署开始${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "GitHub用户: $GITHUB_USER"
echo "分支: $GITHUB_BRANCH"
echo "时区: $SERVER_TIMEZONE"
echo ""

print_step "1/8 安装系统依赖"
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip git curl screen ca-certificates >/dev/null 2>&1
print_ok "系统依赖安装完成"

print_step "2/8 配置时区"
sudo timedatectl set-timezone "$SERVER_TIMEZONE" 2>/dev/null || true
print_ok "时区: $(timedatectl | grep 'Time zone' | awk '{print $3}')"

print_step "3/8 配置GitHub认证"
git config --global user.name "$GITHUB_USER"
git config --global user.email "${GITHUB_USER}@users.noreply.github.com"
cat > ~/.git-credentials << EOF
https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com
EOF
chmod 600 ~/.git-credentials
git config --global credential.helper store
print_ok "GitHub认证配置完成"

print_step "4/8 克隆仓库"
[ -d ~/cryptosignal ] && { echo "备份旧版本..."; mv ~/cryptosignal ~/cryptosignal_backup_$(date +%Y%m%d_%H%M%S); }
cd ~
git clone -b "$GITHUB_BRANCH" https://github.com/${GITHUB_USER}/${GITHUB_REPO}.git ~/cryptosignal >/dev/null 2>&1
cd ~/cryptosignal
print_ok "仓库克隆完成: $(git log --oneline -1)"

print_step "5/8 创建配置文件"
mkdir -p ~/cryptosignal/config
cat > ~/cryptosignal/config/binance_credentials.json << EOF
{
  "api_key": "${BINANCE_API_KEY}",
  "api_secret": "${BINANCE_API_SECRET}",
  "testnet": false
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json

cat > ~/cryptosignal/config/telegram.json << EOF
{
  "enabled": ${TELEGRAM_ENABLED},
  "bot_token": "",
  "chat_id": ""
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json
print_ok "配置文件已创建"

print_step "6/8 安装Python依赖"
python3 -m pip install --upgrade pip -q
pip3 install -r requirements.txt -q
print_ok "Python依赖安装完成"

print_step "7/8 初始化数据库"
chmod +x ~/cryptosignal/setup.sh
chmod +x ~/cryptosignal/auto_restart.sh
python3 scripts/init_databases.py >/dev/null 2>&1 || echo "数据库将在首次运行时创建"
print_ok "数据库初始化完成"

print_step "8/8 配置定时任务"
crontab -l 2>/dev/null | grep -v "cryptosignal" > /tmp/cron.tmp || true
cat >> /tmp/cron.tmp << 'CRON'
0 3 * * * ~/cryptosignal/auto_restart.sh >> ~/cryptosignal/auto_restart.log 2>&1
CRON
crontab /tmp/cron.tmp && rm /tmp/cron.tmp
print_ok "定时任务配置完成（每日3am重启）"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}🚀 启动命令：${NC}"
echo "   screen -S cryptosignal -dm bash -c 'cd ~/cryptosignal && ./setup.sh'"
echo ""
echo -e "${YELLOW}📊 查看日志：${NC}"
echo "   screen -r cryptosignal"
echo "   (按 Ctrl+A 然后 D 退出但保持运行)"
echo ""
echo -e "${YELLOW}🔍 检查状态：${NC}"
echo "   ps aux | grep realtime_signal_scanner"
echo ""
