#!/bin/bash
# CryptoSignal V8.0.2 完整服务器部署脚本
# 支持六层架构 + 四步决策系统 + Freqtrade回测
# 更新日期: 2025-11-22
#
# 使用方法:
#   sudo bash deploy_v8.sh          # 智能模式（推荐）
#   sudo bash deploy_v8.sh fresh    # 强制全新安装
#   sudo bash deploy_v8.sh update   # 只更新代码

# ==================== 敏感配置 ====================
GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
GIT_USER_NAME="YOUR_GITHUB_USERNAME"
GIT_USER_EMAIL="your_email@example.com"
TARGET_BRANCH="main"
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"
BINANCE_API_SECRET="YOUR_BINANCE_API_SECRET"
BINANCE_TESTNET="false"
SERVER_IP_WHITELIST=""
SERVER_TIMEZONE="Asia/Singapore"

# ==================== 模式选择 ====================
DEPLOY_MODE="${1:-auto}"  # auto/fresh/update

# ==================== 非交互模式设置 ====================
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

# ==================== 错误收集 ====================
ERRORS=""
add_error() { ERRORS="$ERRORS\n  - $1"; }

# ==================== 颜色定义 ====================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() { echo ""; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo ""; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
print_skip() { echo -e "${YELLOW}⏭️  $1${NC}"; }

# ==================== 环境检测函数 ====================
check_environment() {
    print_header "环境检测"

    ENV_OK=true

    # 检查虚拟环境
    if [ -d ~/.venv311 ]; then
        # 检查 Python 版本
        VENV_PYTHON_VERSION=$(~/.venv311/bin/python --version 2>/dev/null | grep -o '3\.11' || echo "")
        if [ "$VENV_PYTHON_VERSION" = "3.11" ]; then
            print_success "虚拟环境存在且 Python 版本正确"
            VENV_EXISTS=true
        else
            print_warning "虚拟环境存在但 Python 版本不对"
            VENV_EXISTS=false
            ENV_OK=false
        fi
    else
        print_info "虚拟环境不存在"
        VENV_EXISTS=false
        ENV_OK=false
    fi

    # 检查项目目录
    if [ -d ~/cryptosignal ]; then
        if [ -d ~/cryptosignal/.git ]; then
            print_success "项目目录存在且为 Git 仓库"
            PROJECT_EXISTS=true
        else
            print_warning "项目目录存在但不是 Git 仓库"
            PROJECT_EXISTS=false
            ENV_OK=false
        fi
    else
        print_info "项目目录不存在"
        PROJECT_EXISTS=false
        ENV_OK=false
    fi

    # 检查 Freqtrade
    if [ -d ~/cryptosignal/externals/freqtrade ]; then
        print_success "Freqtrade 已克隆"
        FREQTRADE_EXISTS=true
    else
        print_info "Freqtrade 未克隆"
        FREQTRADE_EXISTS=false
    fi

    # 检查关键依赖（仅当虚拟环境存在时）
    if [ "$VENV_EXISTS" = true ]; then
        DEPS_OK=true
        ~/.venv311/bin/python -c "import freqtrade" 2>/dev/null || DEPS_OK=false
        ~/.venv311/bin/python -c "import ccxt" 2>/dev/null || DEPS_OK=false
        ~/.venv311/bin/python -c "import cryptofeed" 2>/dev/null || DEPS_OK=false

        if [ "$DEPS_OK" = true ]; then
            print_success "关键依赖已安装"
        else
            print_warning "部分关键依赖缺失"
            ENV_OK=false
        fi
    fi

    echo ""

    # 根据检测结果决定实际模式
    if [ "$DEPLOY_MODE" = "auto" ]; then
        if [ "$ENV_OK" = true ]; then
            ACTUAL_MODE="update"
            print_info "检测结果: 环境完整，将执行增量更新"
        else
            ACTUAL_MODE="fresh"
            print_info "检测结果: 环境不完整，将执行全新安装"
        fi
    else
        ACTUAL_MODE="$DEPLOY_MODE"
        print_info "用户指定模式: $ACTUAL_MODE"
    fi

    echo ""
}

# ==================== 开始部署 ====================
clear
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       CryptoSignal V8.0.2 完整服务器部署系统              ║${NC}"
echo -e "${CYAN}║       六层架构 + 四步决策系统 + Freqtrade回测             ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "部署模式: ${YELLOW}$DEPLOY_MODE${NC}"
echo ""

# 执行环境检测
check_environment

# ==================== 步骤 1: 系统环境检测与准备 ====================
print_header "步骤 1/12: 系统环境检测与准备"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    print_info "操作系统: $OS $VER"
else
    print_warning "无法检测操作系统"
fi

print_info "更新系统软件包..."
apt-get update -qq
apt-get upgrade -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

print_info "安装基础工具..."
apt-get install -y git curl wget screen build-essential software-properties-common -qq

print_success "系统环境准备完成"

# ==================== 步骤 2: 安装 Python 3.11 ====================
print_header "步骤 2/12: 安装 Python 3.11"

if python3.11 --version &> /dev/null; then
    print_skip "Python 3.11 已安装: $(python3.11 --version)"
else
    print_info "正在安装 Python 3.11..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
fi

# 确保开发包已安装（编译 cryptofeed 需要 Python.h）
print_info "确保 Python 3.11 开发包已安装..."
apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils -qq
print_success "Python 3.11 开发包已安装"

# 确保 pip 安装
if ! python3.11 -m pip --version &> /dev/null; then
    print_info "安装 pip for Python 3.11..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
    print_success "pip 安装完成"
else
    print_skip "pip 已安装"
fi

# ==================== 步骤 3: 安装 TA-Lib ====================
print_header "步骤 3/12: 安装 TA-Lib"

if [ -f /usr/lib/libta_lib.so ] || [ -f /usr/local/lib/libta_lib.so ]; then
    print_skip "TA-Lib C库已安装"
else
    print_info "安装 TA-Lib C库..."
    apt-get install -y libta-lib-dev -qq 2>/dev/null || {
        print_info "apt 无 TA-Lib，手动编译（约2-3分钟）..."
        cd /tmp
        wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
        if [ ! -f ta-lib-0.4.0-src.tar.gz ]; then
            add_error "TA-Lib 下载失败"
            print_error "TA-Lib 下载失败"
        else
            tar -xzf ta-lib-0.4.0-src.tar.gz
            cd ta-lib/
            print_info "  配置中..."
            ./configure --prefix=/usr >/dev/null 2>&1
            print_info "  编译中（请耐心等待）..."
            if make -j$(nproc) >/dev/null 2>&1; then
                print_info "  安装中..."
                make install >/dev/null 2>&1
                ldconfig
                print_success "TA-Lib C库安装完成"
            else
                add_error "TA-Lib 编译失败，可能内存不足"
                print_error "TA-Lib 编译失败"
            fi
            cd ~
            rm -rf /tmp/ta-lib*
        fi
    }
fi

# ==================== 步骤 4: 停止旧进程 ====================
print_header "步骤 4/12: 停止旧进程"

ps aux | grep -v grep | grep "python.*cryptosignal" > /dev/null && {
    print_info "正在停止旧进程..."
    pkill -f "python.*cryptosignal" 2>/dev/null || true
    sleep 2
    print_success "进程已停止"
} || print_info "无运行中的进程"

screen -ls 2>/dev/null | grep -q cryptosignal && {
    print_info "正在停止 Screen 会话..."
    screen -S cryptosignal -X quit 2>/dev/null || true
    print_success "Screen 会话已停止"
}

# ==================== 步骤 5: 清理/备份旧安装 ====================
print_header "步骤 5/12: 清理/备份旧安装"

if [ "$ACTUAL_MODE" = "fresh" ]; then
    # 全新安装模式：备份并清理
    BACKUP_DIR="$HOME/cryptosignal_backup_$(date +%Y%m%d_%H%M%S)"
    if [ -d ~/cryptosignal ]; then
        print_info "备份旧配置..."
        mkdir -p "$BACKUP_DIR"
        [ -d ~/cryptosignal/config ] && cp -r ~/cryptosignal/config "$BACKUP_DIR/" 2>/dev/null || true
        [ -d ~/cryptosignal/data ] && cp -r ~/cryptosignal/data "$BACKUP_DIR/" 2>/dev/null || true
        [ -d ~/cryptosignal/reports ] && cp -r ~/cryptosignal/reports "$BACKUP_DIR/" 2>/dev/null || true
        print_success "备份完成: $BACKUP_DIR"
        rm -rf ~/cryptosignal
        print_success "旧项目目录已删除"
    else
        print_info "无旧安装需要清理"
    fi

    # 清理旧虚拟环境
    if [ -d ~/.venv311 ]; then
        rm -rf ~/.venv311
        print_success "旧虚拟环境已删除"
    fi

    # 清理旧 Freqtrade 配置
    if [ -d ~/.freqtrade ]; then
        rm -rf ~/.freqtrade
        print_success "旧 Freqtrade 配置已删除"
    fi
else
    # 增量更新模式：保留现有环境
    print_skip "增量更新模式，保留现有环境"
fi

# ==================== 步骤 6: 克隆/更新仓库 ====================
print_header "步骤 6/12: 克隆/更新仓库"

if [ "$ACTUAL_MODE" = "fresh" ] || [ ! -d ~/cryptosignal ]; then
    # 全新克隆
    cd ~
    print_info "正在克隆仓库..."
    git clone https://$GIT_USER_NAME:$GITHUB_TOKEN@github.com/$GIT_USER_NAME/cryptosignal.git
    if [ $? -eq 0 ]; then
        print_success "仓库克隆成功"
    else
        print_error "克隆失败"
        exit 1
    fi
else
    # 增量更新
    cd ~/cryptosignal
    print_info "正在更新仓库..."
    git fetch origin
    git reset --hard origin/$TARGET_BRANCH
    print_success "仓库更新成功"
fi

# 切换分支
cd ~/cryptosignal
git checkout "$TARGET_BRANCH" 2>/dev/null || true
git pull origin "$TARGET_BRANCH" 2>/dev/null || true
print_success "分支: $TARGET_BRANCH"
print_info "当前提交: $(git log --oneline -1)"

# 配置 Git
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
git config --global credential.helper store
echo "https://$GIT_USER_NAME:$GITHUB_TOKEN@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
print_success "Git 配置完成"

# ==================== 步骤 7: 克隆/更新 Freqtrade ====================
print_header "步骤 7/12: 克隆/更新 Freqtrade"

cd ~/cryptosignal
mkdir -p externals
cd externals

if [ ! -d freqtrade ]; then
    print_info "克隆 Freqtrade..."
    git clone https://github.com/freqtrade/freqtrade.git
    print_success "Freqtrade 克隆完成"
else
    print_info "更新 Freqtrade..."
    cd freqtrade && git pull && cd ..
    print_success "Freqtrade 更新完成"
fi

# ==================== 步骤 8: 创建/检查 Python 3.11 虚拟环境 ====================
print_header "步骤 8/12: 创建/检查 Python 3.11 虚拟环境"

cd ~

if [ "$ACTUAL_MODE" = "fresh" ] || [ ! -d ~/.venv311 ]; then
    print_info "创建虚拟环境..."
    python3.11 -m venv ~/.venv311
    print_success "虚拟环境创建完成"
else
    print_skip "虚拟环境已存在，保留使用"
fi

source ~/.venv311/bin/activate

print_info "升级 pip..."
pip install --upgrade pip --quiet

print_info "Python 版本: $(python --version)"

# ==================== 步骤 9: 安装 Python 依赖 ====================
print_header "步骤 9/12: 安装 Python 依赖"

cd ~/cryptosignal

if [ "$ACTUAL_MODE" = "fresh" ]; then
    # 全新安装所有依赖
    print_info "全新安装所有依赖..."

    pip install numpy==1.24.3 pandas==2.0.3 sqlalchemy==2.0.19 --quiet
    pip install "aiohttp>=3.9.0" "websockets>=14.0" --quiet
    pip install nest_asyncio --quiet
    pip install pytest==7.4.0 pytest-cov==4.1.0 pytest-asyncio==0.21.0 --quiet
    pip install python-dotenv==1.0.0 --quiet
    pip install cryptofeed ccxt --quiet
    pip install TA-Lib --quiet
    pip install -e externals/freqtrade --quiet

    print_success "所有 Python 依赖安装完成"
else
    # 增量更新：只安装缺失的依赖
    print_info "检查并安装缺失依赖..."

    # 检查核心依赖
    python -c "import numpy" 2>/dev/null || pip install numpy==1.24.3 --quiet
    python -c "import pandas" 2>/dev/null || pip install pandas==2.0.3 --quiet
    python -c "import sqlalchemy" 2>/dev/null || pip install sqlalchemy==2.0.19 --quiet
    python -c "import aiohttp" 2>/dev/null || pip install "aiohttp>=3.9.0" --quiet
    python -c "import websockets" 2>/dev/null || pip install "websockets>=14.0" --quiet
    python -c "import nest_asyncio" 2>/dev/null || pip install nest_asyncio --quiet
    python -c "import dotenv" 2>/dev/null || pip install python-dotenv==1.0.0 --quiet

    # V8 核心依赖
    python -c "import ccxt" 2>/dev/null || pip install ccxt --quiet
    python -c "import cryptofeed" 2>/dev/null || pip install cryptofeed --quiet
    python -c "import talib" 2>/dev/null || pip install TA-Lib --quiet

    # Freqtrade
    python -c "import freqtrade" 2>/dev/null || pip install -e externals/freqtrade --quiet

    print_success "依赖检查完成"
fi

# ==================== 步骤 10: 配置目录和文件 ====================
print_header "步骤 10/12: 配置目录和文件"

cd ~/cryptosignal

# 创建必要目录
mkdir -p config data reports logs
mkdir -p user_data/strategies
mkdir -p ~/.freqtrade/user_data/strategies

# 复制策略文件
cp cs_ext/backtest/freqtrade_bridge.py user_data/strategies/CryptoSignalStrategy.py
cp cs_ext/backtest/freqtrade_bridge.py ~/.freqtrade/user_data/strategies/CryptoSignalStrategy.py
print_success "策略文件已复制"

# 配置 Binance API
cat > ~/cryptosignal/config/binance_credentials.json <<EOF
{
  "_comment": "Binance Futures API - V8.0.2 - $(date)",
  "binance": {
    "api_key": "$BINANCE_API_KEY",
    "api_secret": "$BINANCE_API_SECRET",
    "testnet": $BINANCE_TESTNET,
    "_server_ip": "$SERVER_IP_WHITELIST"
  }
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json

# 配置 Telegram (禁用)
cat > ~/cryptosignal/config/telegram.json <<EOF
{
  "enabled": false,
  "bot_token": "",
  "chat_id": ""
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json

# 创建 Freqtrade 配置
cat > ~/.freqtrade/config.json <<EOF
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "dry_run_wallet": 10000,
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "cancel_open_orders_on_exit": false,
    "exchange": {
        "name": "binance",
        "key": "$BINANCE_API_KEY",
        "secret": "$BINANCE_API_SECRET",
        "ccxt_config": {},
        "ccxt_async_config": {},
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
    "entry_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1
    },
    "exit_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1
    }
}
EOF
chmod 600 ~/.freqtrade/config.json

print_success "配置完成"

# ==================== 步骤 11: 验证安装 ====================
print_header "步骤 11/12: 验证安装"

cd ~/cryptosignal
echo ""
echo "组件验证结果:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 基础依赖
python -c "import numpy; print('✅ NumPy:', numpy.__version__)" 2>/dev/null || echo "❌ NumPy"
python -c "import pandas; print('✅ Pandas:', pandas.__version__)" 2>/dev/null || echo "❌ Pandas"
python -c "import aiohttp; print('✅ aiohttp:', aiohttp.__version__)" 2>/dev/null || echo "❌ aiohttp"
python -c "import websockets; print('✅ websockets:', websockets.__version__)" 2>/dev/null || echo "❌ websockets"

# V8 核心
python -c "import ccxt; print('✅ CCXT:', ccxt.__version__)" 2>/dev/null || echo "❌ CCXT"
python -c "import cryptofeed; print('✅ Cryptofeed')" 2>/dev/null || echo "❌ Cryptofeed"
python -c "import talib; print('✅ TA-Lib')" 2>/dev/null || echo "❌ TA-Lib"

# Freqtrade
python -c "import freqtrade; print('✅ Freqtrade')" 2>/dev/null || echo "❌ Freqtrade"

# 六层架构组件
python -c "from ats_core.utils.format_converter import normalize_symbol; print('✅ format_converter')" 2>/dev/null || echo "❌ format_converter"
python -c "from ats_core.data.realtime_kline_cache import get_kline_cache; print('✅ kline_cache')" 2>/dev/null || echo "❌ kline_cache"
python -c "from ats_core.decision.four_step_system import run_four_step_decision; print('✅ four_step_system')" 2>/dev/null || echo "❌ four_step_system"
python -c "from ats_core.backtest import BacktestEngine; print('✅ BacktestEngine')" 2>/dev/null || echo "❌ BacktestEngine"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Freqtrade 版本
echo ""
freqtrade --version

# ==================== 步骤 12: 配置自动化 ====================
print_header "步骤 12/12: 配置自动化任务"

# 创建激活脚本
cat > ~/activate_v8.sh <<'EOF'
#!/bin/bash
source ~/.venv311/bin/activate
cd ~/cryptosignal
echo "✅ V8.0.2 环境已激活"
echo "   Python: $(python --version)"
echo "   工作目录: $(pwd)"
EOF
chmod +x ~/activate_v8.sh

# 创建重启脚本
cat > ~/cryptosignal/auto_restart.sh <<'RESTART_EOF'
#!/bin/bash
source ~/.venv311/bin/activate
LOG_FILE="$HOME/cryptosignal/logs/auto_restart.log"
mkdir -p $HOME/cryptosignal/logs
echo "========================================" >> "$LOG_FILE"
echo "重启时间: $(date)" >> "$LOG_FILE"
pkill -f "python.*cryptosignal" 2>/dev/null || true
sleep 2
cd ~/cryptosignal
echo "完成" >> "$LOG_FILE"
RESTART_EOF
chmod +x ~/cryptosignal/auto_restart.sh

# 配置 crontab
crontab -l 2>/dev/null | grep -v "cryptosignal" | grep -v "auto_restart" > /tmp/crontab.tmp || true
cat >> /tmp/crontab.tmp <<EOF

# CryptoSignal V8.0.2
0 3 * * * ~/cryptosignal/auto_restart.sh >> ~/cryptosignal/logs/auto_restart.log 2>&1
0 1 * * * find ~/cryptosignal/logs -name '*.log' -mtime +7 -delete
EOF
crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

print_success "自动化任务配置完成"

# ==================== 部署完成 ====================
print_header "🎉 部署完成"

# 显示错误汇总（如果有）
if [ -n "$ERRORS" ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  部署过程中遇到以下问题：${NC}"
    echo -e "$ERRORS"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
fi

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ V8.0.2 部署成功！                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "📋 部署摘要"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📂 安装目录:     ~/cryptosignal"
echo "  🐍 Python 环境:  ~/.venv311 (Python 3.11)"
echo "  🌿 当前分支:     $TARGET_BRANCH"
echo "  🔧 部署模式:     $ACTUAL_MODE"
echo "  📦 Freqtrade:    $(freqtrade --version 2>&1 | grep freqtrade || echo 'installed')"
echo "  ⏰ 定时任务:     每日 3am 自动重启"
echo ""
echo "🚀 使用方法"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1️⃣  激活环境:"
echo "      source ~/activate_v8.sh"
echo ""
echo "  2️⃣  运行 Freqtrade 回测:"
echo "      freqtrade backtesting \\"
echo "          --strategy CryptoSignalStrategy \\"
echo "          --timerange 20251102-20251122 \\"
echo "          --pairs BNB/USDT:USDT \\"
echo "          --config ~/.freqtrade/config.json \\"
echo "          --userdir ~/cryptosignal/user_data"
echo ""
echo "  3️⃣  部署模式说明:"
echo "      sudo bash deploy_v8.sh          # 智能模式"
echo "      sudo bash deploy_v8.sh fresh    # 全新安装"
echo "      sudo bash deploy_v8.sh update   # 只更新代码"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
print_warning "安全提醒: 部署完成后删除此脚本"
echo "   rm ~/deploy_v8.sh"
echo ""

# 保持虚拟环境激活状态
echo "当前环境已激活，可直接使用。"
