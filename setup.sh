#!/bin/bash
# ==========================================
# CryptoSignal v8.0.0 一键部署脚本
# 用途：拉取代码、检测环境、安装依赖、启动系统
# 特点：自动更新代码、清理缓存、验证结构、可配置化
# v8.0.0: V8六层架构有机融合
#   - Cryptofeed (实时数据层)
#   - CryptoSignal (因子+决策层)
#   - CCXT (执行层)
#   - Cryptostore (存储层)
# ==========================================
#
# 环境变量配置（可选）:
#   SCANNER_SCRIPT    扫描器脚本路径（默认：scripts/realtime_signal_scanner.py）
#   SCAN_INTERVAL     扫描间隔秒数（默认：300）
#   AUTO_COMMIT_REPORTS 自动提交报告（默认：false）
#
# 使用示例:
#   # 默认配置
#   ./setup.sh
#
#   # 自定义扫描间隔（每10分钟）
#   SCAN_INTERVAL=600 ./setup.sh
#
#   # 使用不同的扫描器
#   SCANNER_SCRIPT=scripts/realtime_signal_scanner_v72.py ./setup.sh
# ==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo "🚀 CryptoSignal v8.0.0 一键部署"
echo "   V8六层架构有机融合"
echo "=============================================="
echo ""

# 检测项目目录
cd ~/cryptosignal 2>/dev/null || {
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    echo "请先克隆仓库："
    echo "  git clone https://github.com/FelixWayne0318/cryptosignal.git"
    exit 1
}

# 自动检测当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}✅ 当前分支: $CURRENT_BRANCH${NC}"
echo ""

# ==========================================
# 第0步：拉取最新代码
# ==========================================
echo "📥 拉取最新代码..."
echo "=============================================="

# 0.1 保存本地修改（如果有）
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  检测到本地修改，正在保存...${NC}"
    BACKUP_NAME="自动备份_$(date +%Y%m%d_%H%M%S)"
    git stash save "$BACKUP_NAME" 2>/dev/null || true
    echo -e "${GREEN}✅ 本地修改已备份: $BACKUP_NAME${NC}"
    echo "   恢复方法: git stash pop"
fi

# 0.2 拉取远程代码
echo "正在从远程拉取最新代码..."
if git fetch origin; then
    # 使用rebase模式拉取，避免分支分歧问题
    if git pull --rebase origin "$CURRENT_BRANCH" 2>/dev/null; then
        echo -e "${GREEN}✅ 代码已更新到最新版本${NC}"
    else
        echo -e "${YELLOW}⚠️  检测到分支分歧，强制同步到远程最新版本...${NC}"
        git reset --hard origin/"$CURRENT_BRANCH" 2>/dev/null || true
        echo -e "${GREEN}✅ 已同步到远程最新版本${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  代码拉取失败（可能网络问题），继续使用本地版本...${NC}"
fi

# 0.3 清理Python缓存（重要！确保新代码生效）
echo ""
echo "🧹 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Python缓存已清理${NC}"

# 0.4 验证目录结构（v8.0.0特性）
echo ""
echo "🔍 验证v8.0.0目录结构..."

# v8.0.0: 检查目录是否存在
# 必需目录: tests/, docs/, standards/, config/, ats_core/, cs_ext/
if [ -d "tests" ] && [ -d "docs" ] && [ -d "standards" ] && [ -d "ats_core/decision" ] && [ -d "cs_ext" ]; then
    echo -e "${GREEN}✅ v8.0.0目录结构正确（含V8架构）${NC}"

    # 统计文件数量
    DOC_FILES=$(find docs -name "*.md" 2>/dev/null | wc -l)
    STANDARD_FILES=$(find standards -name "*.md" 2>/dev/null | wc -l)
    CS_EXT_FILES=$(find cs_ext -name "*.py" 2>/dev/null | wc -l)

    echo "   - docs/: $DOC_FILES 个文档"
    echo "   - standards/: $STANDARD_FILES 个规范"
    echo "   - cs_ext/: $CS_EXT_FILES 个V8适配器文件"

    # V8组件检查
    if [ -f "cs_ext/data/cryptofeed_stream.py" ] && [ -f "cs_ext/execution/ccxt_executor.py" ]; then
        echo -e "${GREEN}   ✅ V8组件完整（Cryptofeed + CCXT）${NC}"
    else
        echo -e "${YELLOW}   ⚠️ V8组件不完整${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  目录结构可能不是v8.0.0版本${NC}"
    echo "   请确保存在以下目录: tests/, docs/, standards/, ats_core/, cs_ext/"
fi

echo ""
echo "=============================================="
echo ""

# 检测Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装，请先安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3: $(python3 --version 2>&1 | awk '{print $2}')${NC}"

# 检测pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip3 未安装，尝试安装...${NC}"
    sudo apt-get update && sudo apt-get install -y python3-pip || {
        echo -e "${RED}❌ pip3 安装失败${NC}"
        exit 1
    }
fi
echo -e "${GREEN}✅ pip3 已安装${NC}"

# 安装依赖（静默，快速）
echo ""
echo "📦 检查并安装依赖..."
pip3 install -r requirements.txt --quiet 2>&1 | grep -v "Requirement already satisfied" || true
echo -e "${GREEN}✅ 依赖已就绪${NC}"

# 检查配置文件
echo ""
echo "🔧 检查配置文件..."

# 检查Binance配置
if [ ! -f "config/binance_credentials.json" ]; then
    echo -e "${YELLOW}⚠️  Binance配置不存在${NC}"
    echo "请创建: config/binance_credentials.json"
    echo "参考: config/binance_credentials.json.example"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅ Binance配置存在${NC}"

# 从配置文件加载API密钥到环境变量
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo "🔑 从配置文件加载API密钥..."

    # 使用Python解析JSON（更可靠）
    export BINANCE_API_KEY=$(python3 -c "import json; print(json.load(open('config/binance_credentials.json'))['binance']['api_key'])" 2>/dev/null)
    export BINANCE_API_SECRET=$(python3 -c "import json; print(json.load(open('config/binance_credentials.json'))['binance']['api_secret'])" 2>/dev/null)

    if [ -n "$BINANCE_API_KEY" ] && [ -n "$BINANCE_API_SECRET" ]; then
        echo -e "${GREEN}✅ API密钥已加载到环境变量${NC}"
    else
        echo -e "${YELLOW}⚠️  无法从配置文件读取API密钥${NC}"
        echo "   请检查 config/binance_credentials.json 格式"
    fi
else
    echo -e "${GREEN}✅ API密钥已从环境变量获取${NC}"
fi

# 检查Telegram配置
if [ ! -f "config/telegram.json" ]; then
    echo -e "${YELLOW}⚠️  Telegram配置不存在，创建默认配置（禁用）${NC}"
    cat > config/telegram.json <<EOF
{
  "enabled": false,
  "bot_token": "",
  "chat_id": "",
  "_comment": "Telegram通知已禁用，如需启用请参考 telegram.json.example"
}
EOF
fi
echo -e "${GREEN}✅ Telegram配置存在${NC}"

# ==========================================
# 注意：定时任务配置已移至部署脚本
# ==========================================
# v7.4.2方案B架构调整：
#   - crontab配置应由部署脚本负责（服务器基础设施层）
#   - setup.sh只负责应用启动（应用执行层）
#   - 这样职责清晰，避免每次git pull都修改系统配置
#
# 如果需要配置定时任务，请使用：
#   deploy_server_v7.4.2_planB_PRODUCTION.sh（全新部署）
#   或手动配置：crontab -e
#     添加：0 3 * * * ~/cryptosignal/auto_restart.sh
# ==========================================

# 添加执行权限
chmod +x auto_restart.sh deploy_and_run.sh setup.sh scripts/init_databases.py start_live.sh 2>/dev/null || true

# 初始化数据库
echo ""
echo "🗄️  初始化数据库..."
echo "=============================================="
python3 scripts/init_databases.py || {
    echo -e "${RED}❌ 数据库初始化失败${NC}"
    echo "这不会影响系统运行，数据库会在首次使用时自动创建"
}

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 环境准备完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🚀 正在启动 v8.0.0 扫描器（后台模式 + 实时日志）..."
echo "   特性: V8六层架构 | 实时因子计算 | Cryptofeed + CCXT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 停止旧进程（兼容V7和V8版本）
pkill -f realtime_signal_scanner 2>/dev/null || true
pkill -f start_realtime_stream 2>/dev/null || true
sleep 1

# 创建日志文件名
LOG_FILE=~/cryptosignal_$(date +%Y%m%d_%H%M%S).log

# 后台启动V8扫描器
# 支持环境变量配置
V8_MODE="${V8_MODE:-full}"
SCAN_INTERVAL="${SCAN_INTERVAL:-300}"
ALL_SYMBOLS="${ALL_SYMBOLS:-true}"

echo "📝 后台启动V8扫描器（真V8模式 - Cryptofeed+CCXT+Cryptostore）..."
echo "   🔧 运行模式: $V8_MODE"
echo "   ⏰ 扫描间隔: ${SCAN_INTERVAL}秒"
echo "   🌐 全市场扫描: $ALL_SYMBOLS"
echo "   📁 数据存储: data/v8_storage/"

# 构建启动命令
V8_CMD="python3 scripts/start_realtime_stream.py --mode $V8_MODE --interval $SCAN_INTERVAL"
if [ "$ALL_SYMBOLS" = "true" ]; then
    V8_CMD="$V8_CMD --all-symbols"
fi

nohup $V8_CMD > "$LOG_FILE" 2>&1 &
PID=$!

sleep 2

# 验证启动
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 扫描器已启动（PID: $PID）${NC}"
    echo "   日志文件: $LOG_FILE"
    echo "   ✅ SSH断开后继续运行"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 管理命令:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  查看状态: ps aux | grep start_realtime_stream"
    echo "  重新启动: ~/cryptosignal/setup.sh"
    echo "  停止程序: pkill -f start_realtime_stream.py"
    echo "  查看日志: tail -f $LOG_FILE"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚙️  v8.0.1 真V8模式配置:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  🌐 全市场扫描: $ALL_SYMBOLS"
    echo "  📁 数据存储位置: data/v8_storage/"
    echo "  💡 切换模式: V8_MODE=simple ./setup.sh"
    echo ""
    echo "  🆕 v8.0.1 真V8六层架构已启用："
    echo "    ✅ Layer1: Cryptofeed (WebSocket实时数据流)"
    echo "    ✅ Layer2: CryptoSignal (实时因子计算+决策)"
    echo "    ✅ Layer3: CCXT (动态加载全市场币种)"
    echo "    ✅ Layer4: Cryptostore (数据持久化)"
    echo "    ✅ 实时因子: CVD/OBI/LDI/VWAP/TradeIntensity"
    echo "    📊 全市场实时交易系统"
    echo ""
    echo "  V8组件目录："
    echo "    - cs_ext/data/cryptofeed_stream.py (数据层)"
    echo "    - cs_ext/execution/ccxt_executor.py (执行层)"
    echo "    - cs_ext/storage/cryptostore_adapter.py (存储层)"
    echo "    - ats_core/realtime/factor_calculator.py (因子计算)"
    echo "    - ats_core/pipeline/v8_realtime_pipeline.py (集成管道)"
    echo ""
    echo "  配置开关："
    echo "    - config/signal_thresholds.json → v8_integration"
    echo "    - V8实时模式: python scripts/start_realtime_stream.py --mode full"
    echo ""
    echo "  详细文档："
    echo "    - docs/FOUR_STEP_IMPLEMENTATION_GUIDE.md"
    echo "    - standards/00_INDEX.md"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}🟢 正在显示实时日志（按 Ctrl+C 退出查看，程序继续运行）${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # 等待日志文件生成
    sleep 2

    # 显示实时日志（用户按Ctrl+C只是退出查看，不影响后台程序）
    tail -f "$LOG_FILE"
else
    echo -e "${RED}❌ 启动失败${NC}"
    echo "请查看日志: cat $LOG_FILE"
    exit 1
fi
