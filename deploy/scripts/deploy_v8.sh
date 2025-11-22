#!/bin/bash
# ==========================================
# CryptoSignal v8.0.2 完整部署脚本
# 支持 Python 3.11 + Freqtrade 回测
# ==========================================
# 使用方法：
#   1. 填写下方【您的配置】区域
#   2. 全选复制整个脚本
#   3. 粘贴到服务器执行
# ==========================================

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【您的配置】- 请填写真实信息
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GITHUB_USER="YOUR_GITHUB_USERNAME"
GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"
BINANCE_API_SECRET="YOUR_BINANCE_API_SECRET"

# 可选配置
GITHUB_REPO="cryptosignal"
GITHUB_BRANCH="main"
SERVER_TIMEZONE="Asia/Singapore"
TELEGRAM_ENABLED="false"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
print_step() { echo -e "\n${GREEN}━━━ $1 ━━━${NC}\n"; }
print_ok() { echo -e "${GREEN}✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_err() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# 检查配置
[ "$GITHUB_TOKEN" = "YOUR_GITHUB_TOKEN" ] && print_err "请先填写GITHUB_TOKEN"
[ "$BINANCE_API_KEY" = "YOUR_BINANCE_API_KEY" ] && print_err "请先填写BINANCE_API_KEY"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  CryptoSignal v8.0.2 部署开始${NC}"
echo -e "${BLUE}  支持 Python 3.11 + Freqtrade 回测${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "GitHub用户: $GITHUB_USER"
echo "分支: $GITHUB_BRANCH"
echo "时区: $SERVER_TIMEZONE"
echo ""

# ==========================================
# 步骤 1/12: 安装系统依赖
# ==========================================
print_step "1/12 安装系统依赖"
sudo apt-get update -qq
sudo apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    build-essential wget curl git screen \
    ca-certificates libssl-dev libffi-dev \
    >/dev/null 2>&1
print_ok "系统依赖安装完成 (Python 3.11)"

# ==========================================
# 步骤 2/12: 配置时区
# ==========================================
print_step "2/12 配置时区"
sudo timedatectl set-timezone "$SERVER_TIMEZONE" 2>/dev/null || true
print_ok "时区: $(timedatectl | grep 'Time zone' | awk '{print $3}')"

# ==========================================
# 步骤 3/12: 配置GitHub认证
# ==========================================
print_step "3/12 配置GitHub认证"
git config --global user.name "$GITHUB_USER"
git config --global user.email "${GITHUB_USER}@users.noreply.github.com"
cat > ~/.git-credentials << EOF
https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com
EOF
chmod 600 ~/.git-credentials
git config --global credential.helper store
print_ok "GitHub认证配置完成"

# ==========================================
# 步骤 4/12: 克隆仓库
# ==========================================
print_step "4/12 克隆仓库"
if [ -d ~/cryptosignal ]; then
    echo "备份旧版本..."
    mv ~/cryptosignal ~/cryptosignal_backup_$(date +%Y%m%d_%H%M%S)
fi
cd ~
git clone -b "$GITHUB_BRANCH" https://github.com/${GITHUB_USER}/${GITHUB_REPO}.git ~/cryptosignal >/dev/null 2>&1
cd ~/cryptosignal
print_ok "仓库克隆完成: $(git log --oneline -1)"

# ==========================================
# 步骤 5/12: 创建Python 3.11虚拟环境
# ==========================================
print_step "5/12 创建Python 3.11虚拟环境"
python3.11 -m venv ~/.venv311
source ~/.venv311/bin/activate
pip install --upgrade pip -q
print_ok "Python 3.11 虚拟环境创建完成"

# ==========================================
# 步骤 6/12: 安装TA-Lib C库
# ==========================================
print_step "6/12 安装TA-Lib C库 (Freqtrade依赖)"
cd /tmp
if [ ! -f /usr/local/lib/libta_lib.so ]; then
    wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr/local >/dev/null 2>&1
    make -j$(nproc) >/dev/null 2>&1
    sudo make install >/dev/null 2>&1
    sudo ldconfig
    cd /tmp && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
    print_ok "TA-Lib C库编译安装完成"
else
    print_ok "TA-Lib C库已存在，跳过"
fi
cd ~/cryptosignal

# ==========================================
# 步骤 7/12: 安装Python依赖
# ==========================================
print_step "7/12 安装Python依赖"
pip install -r requirements.txt -q
print_ok "基础Python依赖安装完成"

# ==========================================
# 步骤 8/12: 安装Freqtrade
# ==========================================
print_step "8/12 安装Freqtrade回测框架"
if [ ! -d ~/cryptosignal/externals/freqtrade ]; then
    mkdir -p ~/cryptosignal/externals
    git clone https://github.com/freqtrade/freqtrade.git ~/cryptosignal/externals/freqtrade >/dev/null 2>&1
fi
cd ~/cryptosignal/externals/freqtrade
pip install -e . -q
cd ~/cryptosignal
print_ok "Freqtrade安装完成: $(freqtrade --version 2>/dev/null | head -1)"

# ==========================================
# 步骤 9/12: 创建配置文件
# ==========================================
print_step "9/12 创建配置文件"

# Binance凭证
mkdir -p ~/cryptosignal/config
cat > ~/cryptosignal/config/binance_credentials.json << EOF
{
  "binance": {
    "api_key": "${BINANCE_API_KEY}",
    "api_secret": "${BINANCE_API_SECRET}",
    "testnet": false
  }
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json

# Telegram配置
cat > ~/cryptosignal/config/telegram.json << EOF
{
  "enabled": ${TELEGRAM_ENABLED},
  "bot_token": "",
  "chat_id": ""
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json

# Freqtrade配置
mkdir -p ~/.freqtrade
cat > ~/.freqtrade/config.json << EOF
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "cancel_open_orders_on_exit": false,
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "unfilledtimeout": {
        "entry": 10,
        "exit": 10,
        "exit_timeout_count": 0,
        "unit": "minutes"
    },
    "entry_pricing": {
        "price_side": "other",
        "use_order_book": true,
        "order_book_top": 1
    },
    "exit_pricing": {
        "price_side": "other",
        "use_order_book": true,
        "order_book_top": 1
    },
    "exchange": {
        "name": "binance",
        "key": "${BINANCE_API_KEY}",
        "secret": "${BINANCE_API_SECRET}",
        "ccxt_config": {},
        "ccxt_sync_config": {},
        "pair_whitelist": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "BNB/USDT:USDT",
            "SOL/USDT:USDT",
            "XRP/USDT:USDT"
        ],
        "pair_blacklist": []
    },
    "pairlists": [
        {"method": "StaticPairList"}
    ],
    "telegram": {
        "enabled": false,
        "token": "",
        "chat_id": ""
    },
    "api_server": {
        "enabled": false,
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8080,
        "verbosity": "error"
    },
    "bot_name": "cryptosignal_v8",
    "initial_state": "running",
    "force_entry_enable": false,
    "internals": {
        "process_throttle_secs": 5
    }
}
EOF
chmod 600 ~/.freqtrade/config.json
print_ok "配置文件已创建"

# ==========================================
# 步骤 10/12: 设置Freqtrade目录结构
# ==========================================
print_step "10/12 设置Freqtrade目录结构"
mkdir -p ~/cryptosignal/user_data/strategies
mkdir -p ~/cryptosignal/user_data/data

# 复制策略文件
if [ -f ~/cryptosignal/cs_ext/backtest/freqtrade_bridge.py ]; then
    cp ~/cryptosignal/cs_ext/backtest/freqtrade_bridge.py ~/cryptosignal/user_data/strategies/CryptoSignalStrategy.py
    print_ok "策略文件已复制"
else
    print_warn "策略文件不存在，请手动创建"
fi

# ==========================================
# 步骤 11/12: 创建激活脚本
# ==========================================
print_step "11/12 创建激活脚本"
cat > ~/activate_v8.sh << 'EOF'
#!/bin/bash
source ~/.venv311/bin/activate
cd ~/cryptosignal
echo "✅ CryptoSignal v8.0.2 环境已激活"
echo "   Python: $(python --version)"
echo "   Freqtrade: $(freqtrade --version 2>/dev/null | head -1)"
echo ""
echo "📊 回测命令示例:"
echo "   freqtrade backtesting --strategy CryptoSignalStrategy --timerange 20251102-20251122 --pairs BNB/USDT:USDT --config ~/.freqtrade/config.json --userdir ~/cryptosignal/user_data"
EOF
chmod +x ~/activate_v8.sh
print_ok "激活脚本已创建: ~/activate_v8.sh"

# ==========================================
# 步骤 12/12: 初始化数据库和配置定时任务
# ==========================================
print_step "12/12 初始化数据库和定时任务"
chmod +x ~/cryptosignal/setup.sh 2>/dev/null || true
chmod +x ~/cryptosignal/auto_restart.sh 2>/dev/null || true
python3 scripts/init_databases.py >/dev/null 2>&1 || echo "数据库将在首次运行时创建"

# 配置定时任务
crontab -l 2>/dev/null | grep -v "cryptosignal" > /tmp/cron.tmp || true
cat >> /tmp/cron.tmp << 'CRON'
0 3 * * * source ~/.venv311/bin/activate && ~/cryptosignal/auto_restart.sh >> ~/cryptosignal/auto_restart.log 2>&1
CRON
crontab /tmp/cron.tmp && rm /tmp/cron.tmp
print_ok "数据库初始化和定时任务配置完成"

# ==========================================
# 部署完成
# ==========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ CryptoSignal v8.0.2 部署完成！${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}🔧 激活环境：${NC}"
echo "   source ~/activate_v8.sh"
echo ""
echo -e "${YELLOW}📊 运行回测：${NC}"
echo "   freqtrade backtesting \\"
echo "       --strategy CryptoSignalStrategy \\"
echo "       --timerange 20251102-20251122 \\"
echo "       --pairs BNB/USDT:USDT \\"
echo "       --config ~/.freqtrade/config.json \\"
echo "       --userdir ~/cryptosignal/user_data"
echo ""
echo -e "${YELLOW}🚀 启动实时信号：${NC}"
echo "   screen -S cryptosignal -dm bash -c 'source ~/.venv311/bin/activate && cd ~/cryptosignal && ./setup.sh'"
echo ""
echo -e "${YELLOW}📋 查看日志：${NC}"
echo "   screen -r cryptosignal"
echo "   (按 Ctrl+A 然后 D 退出但保持运行)"
echo ""
