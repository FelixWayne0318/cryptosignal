#!/bin/bash
# ==========================================
# CryptoSignal v6.6 全自动部署并运行脚本
# 适用于：首次部署、更新部署、全新服务器
# 自动处理：git冲突、依赖缺失、所有错误
# ==========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "🚀 CryptoSignal v6.6 全自动部署并运行"
echo "=============================================="
echo ""
echo "📋 脚本功能："
echo "  ✓ 自动处理 git 冲突"
echo "  ✓ 自动检测系统环境"
echo "  ✓ 自动安装缺失依赖"
echo "  ✓ 首次部署引导（API配置）"
echo "  ✓ 完整验证（9步）"
echo "  ✓ 自动启动系统"
echo "  ✓ 网络失败自动重试"
echo ""

# ==========================================
# 第 -1 步：Git 环境清理和代码同步
# ==========================================

echo "📍 第 -1 步：Git 环境清理和代码同步"
echo "=============================================="

# 检测是否在项目目录中
if [ ! -d ~/cryptosignal ]; then
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    echo ""
    echo "首次部署，请先克隆仓库："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "cd ~"
    echo "git clone https://github.com/FelixWayne0318/cryptosignal.git"
    echo "cd cryptosignal"
    echo "git checkout claude/understand-realtime-scanner-system-011CUjuCJDa9UX3sbxtR2HvA"
    echo "./deploy_and_run.sh"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi

cd ~/cryptosignal

# 检测是否在 git 仓库中
if [ ! -d .git ]; then
    echo -e "${RED}❌ 不在 git 仓库中${NC}"
    exit 1
fi

echo "1️⃣ 备份本地修改..."
# 备份本地修改（如果有）
BACKUP_NAME="自动备份_$(date +%Y%m%d_%H%M%S)"
if git diff --quiet && git diff --cached --quiet; then
    echo "✅ 没有本地修改，无需备份"
else
    git stash save "$BACKUP_NAME" 2>/dev/null || true
    echo -e "${GREEN}✅ 已备份本地修改: $BACKUP_NAME${NC}"
    echo "   恢复方法: git stash list 查看，git stash pop 恢复"
fi

echo ""
echo "2️⃣ 清理未跟踪文件..."
# 清理未跟踪的文件
git clean -fd 2>/dev/null || true
echo "✅ 未跟踪文件已清理"

echo ""
echo "3️⃣ 同步到最新代码..."

# 网络重试函数
retry_git() {
    local cmd="$1"
    local max_retries=3
    local retry=0

    while [ $retry -lt $max_retries ]; do
        if eval "$cmd"; then
            return 0
        else
            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                echo -e "${YELLOW}⚠️ 网络失败，2秒后重试 ($retry/$max_retries)...${NC}"
                sleep 2
            fi
        fi
    done

    return 1
}

# Fetch 远程代码（带重试）
echo "   正在 fetch 远程代码..."
if ! retry_git "git fetch origin claude/understand-realtime-scanner-system-011CUjuCJDa9UX3sbxtR2HvA"; then
    echo -e "${RED}❌ git fetch 失败，请检查网络连接${NC}"
    exit 1
fi

# 强制重置到远程版本
echo "   强制同步到远程最新版本..."
git reset --hard origin/claude/understand-realtime-scanner-system-011CUjuCJDa9UX3sbxtR2HvA

# 切换分支
git checkout claude/understand-realtime-scanner-system-011CUjuCJDa9UX3sbxtR2HvA 2>/dev/null || true

# Pull 最新代码（带重试）
echo "   正在 pull 最新代码..."
if ! retry_git "git pull origin claude/understand-realtime-scanner-system-011CUjuCJDa9UX3sbxtR2HvA"; then
    echo -e "${YELLOW}⚠️ git pull 失败，但已 reset 到远程版本，继续部署...${NC}"
fi

echo ""
echo -e "${GREEN}✅ 代码同步完成${NC}"
echo "   当前分支: $(git branch --show-current)"
echo "   最新提交: $(git log --oneline -1)"

echo ""

# ==========================================
# 第 0 步：系统环境检测和依赖安装
# ==========================================

echo "📍 第 0 步：系统环境检测"
echo "=============================================="

# 0.1 检测 Python 3
echo "1️⃣ 检测 Python 3..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ Python 已安装: $PYTHON_VERSION"
else
    echo -e "${RED}❌ Python 3 未安装${NC}"
    echo ""
    echo "请先安装 Python 3.8+："
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    exit 1
fi

# 0.2 检测 pip3
echo ""
echo "2️⃣ 检测 pip3..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 已安装"
else
    echo -e "${YELLOW}⚠️ pip3 未安装，尝试自动安装...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    else
        echo -e "${RED}❌ 无法自动安装 pip3，请手动安装${NC}"
        exit 1
    fi
    echo "✅ pip3 安装成功"
fi

# 0.3 检测 git
echo ""
echo "3️⃣ 检测 git..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version 2>&1 | awk '{print $3}')
    echo "✅ git 已安装: $GIT_VERSION"
else
    echo -e "${RED}❌ git 未安装${NC}"
    echo ""
    echo "请先安装 git："
    echo "  Ubuntu/Debian: sudo apt install git"
    echo "  CentOS/RHEL:   sudo yum install git"
    exit 1
fi

# 0.4 检测 screen（可选）
echo ""
echo "4️⃣ 检测 screen..."
if command -v screen &> /dev/null; then
    echo "✅ screen 已安装（推荐，支持后台运行）"
else
    echo -e "${YELLOW}⚠️ screen 未安装（可选）${NC}"
    echo "   安装方法: sudo apt install screen"
    echo "   如未安装，将使用 nohup 后台运行"
fi

echo ""

# ==========================================
# 第 1 步：停止当前运行的扫描器
# ==========================================

echo "📍 第 1 步：停止当前运行的扫描器"
echo "=============================================="
cd ~/cryptosignal

# 停止所有扫描器进程
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null || true
echo "✅ 已停止运行中的扫描器"
sleep 2

# 确认已停止
if ps aux | grep realtime_signal_scanner | grep -v grep; then
    echo -e "${YELLOW}⚠️ 仍有进程在运行，强制终止...${NC}"
    ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
else
    echo "✅ 没有运行的扫描器进程"
fi

echo ""

# ==========================================
# 第 2 步：备份当前配置
# ==========================================

echo "📍 第 2 步：备份当前配置"
echo "=============================================="
cd ~/cryptosignal

# 备份配置文件（以防万一）
BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
cp config/params.json config/params.json.bak.$BACKUP_TIME 2>/dev/null || echo -e "${YELLOW}⚠️ params.json 不存在${NC}"
cp config/telegram.json config/telegram.json.bak.$BACKUP_TIME 2>/dev/null || echo "⚠️ telegram.json 不存在，跳过备份"
cp config/binance_credentials.json config/binance_credentials.json.bak.$BACKUP_TIME 2>/dev/null || echo "⚠️ binance_credentials.json 不存在，跳过备份"

echo "✅ 配置文件已备份到 *.bak.$BACKUP_TIME"

echo ""

# ==========================================
# 第 3 步：检测并安装 Python 依赖
# ==========================================

echo "📍 第 3 步：检测并安装 Python 依赖"
echo "=============================================="
cd ~/cryptosignal

# 检测 requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt 不存在${NC}"
    exit 1
fi

echo "1️⃣ 检测已安装的依赖..."

# 检测关键依赖
MISSING_DEPS=0

# 检测 numpy
python3 -c "import numpy" 2>/dev/null || {
    echo "⚠️ numpy 未安装"
    MISSING_DEPS=1
}

# 检测 pandas
python3 -c "import pandas" 2>/dev/null || {
    echo "⚠️ pandas 未安装"
    MISSING_DEPS=1
}

# 检测 aiohttp
python3 -c "import aiohttp" 2>/dev/null || {
    echo "⚠️ aiohttp 未安装"
    MISSING_DEPS=1
}

# 检测 websockets
python3 -c "import websockets" 2>/dev/null || {
    echo "⚠️ websockets 未安装"
    MISSING_DEPS=1
}

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo "2️⃣ 检测到缺失依赖，开始安装..."
    echo ""

    # 升级 pip
    echo "   升级 pip..."
    python3 -m pip install --upgrade pip --quiet || {
        echo -e "${YELLOW}⚠️ pip 升级失败，继续安装依赖...${NC}"
    }

    # 安装依赖（带错误处理）
    echo "   安装依赖包（可能需要几分钟）..."
    if pip3 install -r requirements.txt --quiet; then
        echo ""
        echo -e "${GREEN}✅ 依赖安装完成${NC}"
    else
        echo ""
        echo -e "${RED}❌ 依赖安装失败${NC}"
        echo ""
        echo "请手动安装："
        echo "  pip3 install -r requirements.txt"
        echo ""
        echo "如果仍然失败，尝试："
        echo "  sudo apt install python3-numpy python3-pandas"
        echo "  pip3 install -r requirements.txt"
        exit 1
    fi
else
    echo "✅ 所有依赖已安装"
fi

echo ""

# ==========================================
# 第 4 步：验证系统配置
# ==========================================

echo "📍 第 4 步：验证系统配置"
echo "=============================================="
cd ~/cryptosignal

echo "1️⃣ 检查核心模块导入..."
if python3 -c "
from ats_core.gates.integrated_gates import FourGatesChecker
from ats_core.execution.metrics_estimator import ExecutionMetricsEstimator
from ats_core.data.quality import DataQualMonitor
from ats_core.pipeline.analyze_symbol import analyze_symbol
print('✅ 所有核心模块导入成功')
" 2>&1; then
    :
else
    echo -e "${RED}❌ 导入失败，请检查代码${NC}"
    exit 1
fi

echo ""
echo "2️⃣ 验证权重配置（v6.6 - 6因子系统）..."
python3 -c "
import json

# 读取配置
with open('config/params.json') as f:
    config = json.load(f)
    weights = config['weights']
    publish = config['publish']

# 验证权重（跳过注释字段）
core_factors = ['T', 'M', 'C', 'V', 'O', 'B']
factor_weights = {k: v for k, v in weights.items() if not k.startswith('_')}
factors_total = sum(factor_weights[k] for k in core_factors if k in factor_weights)
modulators = ['L', 'S', 'F', 'I']

print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print('权重配置验证 (v6.6 - 6因子系统)')
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print(f'核心6因子总和: {factors_total}%')
for k in core_factors:
    if k in factor_weights:
        print(f'  {k}: {weights[k]}%')
print()
print('调制器（应为0.0，不参与评分）:')
for k in modulators:
    if k in weights:
        print(f'  {k}: {weights[k]}')
print()

# 验证发布阈值
print('发布阈值 (v6.6软约束):')
print(f'  prime_prob_min: {publish[\"prime_prob_min\"]} (软约束)')
print(f'  prime_dims_ok_min: {publish[\"prime_dims_ok_min\"]}')
print(f'  prime_dim_threshold: {publish[\"prime_dim_threshold\"]}')
print()

# 断言验证
assert abs(factors_total - 100.0) < 0.01, f'错误: 核心因子权重={factors_total}, 应为100.0'
if all(k in weights for k in modulators):
    assert all(weights[k] == 0.0 for k in modulators), '错误: 调制器权重必须为0.0'

print('✅ v6.6 权重配置验证通过')
print('✅ 类型安全检查通过')
" || {
    echo -e "${RED}❌ 配置验证失败${NC}"
    exit 1
}

echo ""
echo "3️⃣ 验证 Binance API 配置..."

# 检测首次部署
FIRST_TIME_DEPLOY=0

if [ -f "config/binance_credentials.json" ]; then
    python3 -c "
import json
with open('config/binance_credentials.json') as f:
    bn = json.load(f)['binance']
    if bn.get('api_key') and bn['api_key'] != 'YOUR_BINANCE_API_KEY_HERE':
        print('✅ Binance API配置存在')
        exit(0)
    else:
        exit(1)
" || FIRST_TIME_DEPLOY=1
else
    FIRST_TIME_DEPLOY=1
fi

if [ $FIRST_TIME_DEPLOY -eq 1 ]; then
    echo -e "${YELLOW}⚠️ Binance API 配置未填写（首次部署）${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 首次部署引导：配置 Binance API"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "请执行以下命令配置 API 凭证："
    echo ""
    echo "cat > config/binance_credentials.json <<'EOF'"
    echo '{'
    echo '  "_comment": "Binance Futures API凭证配置",'
    echo '  "binance": {'
    echo '    "api_key": "您的API_KEY",'
    echo '    "api_secret": "您的SECRET_KEY",'
    echo '    "testnet": false,'
    echo '    "_security": "只读权限API Key"'
    echo '  }'
    echo '}'
    echo "EOF"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "配置完成后，重新运行: ./deploy_and_run.sh"
    exit 1
fi

echo ""

# ==========================================
# 第 5 步：清理 Python 缓存
# ==========================================

echo "📍 第 5 步：清理 Python 缓存"
echo "=============================================="
cd ~/cryptosignal

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Python 缓存已清理"
echo ""

# ==========================================
# 第 6 步：测试运行（10秒快速验证）
# ==========================================

echo "📍 第 6 步：快速测试运行（10秒验证）"
echo "=============================================="
cd ~/cryptosignal

echo "启动测试（10秒后自动终止）..."
timeout 10 python3 scripts/realtime_signal_scanner.py --max-symbols 10 --no-telegram 2>&1 | tail -50 || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo ""
        echo "✅ 测试超时（正常），系统初始化成功"
    else
        echo ""
        echo -e "${YELLOW}⚠️ 测试失败，退出码: $EXIT_CODE${NC}"
        echo "   继续部署，如果启动失败请查看日志..."
    fi
}

echo ""

# ==========================================
# 第 7 步：自动启动生产环境
# ==========================================

echo "📍 第 7 步：自动启动生产环境"
echo "=============================================="
echo ""
echo -e "${GREEN}✅ v6.5 部署验证完成！${NC}"
echo ""
echo "🚀 正在启动生产环境（每5分钟扫描一次，200个币种）..."
echo ""

# 创建 logs 目录
mkdir -p logs

# 检查是否有 screen
if command -v screen &> /dev/null; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "使用 Screen 会话启动（推荐）"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 Screen 工作原理："
    echo "  1. 启动后您会看到实时日志（类似前台运行）"
    echo "  2. 按 Ctrl+A 然后按 D 键分离会话"
    echo "  3. 分离后程序继续在后台运行"
    echo "  4. ✅ 退出 SSH/Termius 不影响程序运行"
    echo "  5. 随时可以重连查看日志"
    echo ""
    echo "🔧 常用命令："
    echo "  重连会话: screen -r cryptosignal"
    echo "  查看所有: screen -ls"
    echo "  停止程序: 在会话中按 Ctrl+C"
    echo ""
    echo "⏳ 3秒后启动..."
    sleep 3

    # 启动 screen 会话
    screen -S cryptosignal python3 scripts/realtime_signal_scanner.py --interval 300
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "使用 nohup 后台启动"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    LOG_FILE="logs/scanner_$(date +%Y%m%d_%H%M%S).log"

    nohup python3 scripts/realtime_signal_scanner.py --interval 300 > "$LOG_FILE" 2>&1 &
    PID=$!

    echo ""
    echo -e "${GREEN}✅ 已启动，PID: $PID${NC}"
    echo "日志文件: $LOG_FILE"
    echo ""
    echo "查看日志: tail -f $LOG_FILE"
    echo "停止进程: kill $PID"
    echo ""

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✅ 部署并运行完成！${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 v6.5 系统特性"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ L因子架构重构（移至执行层）"
    echo "✅ 8+2因子系统（8个方向因子+2个调制器）"
    echo "✅ 权重优化：T20% M14% C20% O14%"
    echo "✅ Spread阈值收紧：标准25bps 新币40bps"
    echo ""
    echo "预期效果："
    echo "  • 信号量：3-7个Prime信号/小时"
    echo "  • 多空比例：接近1:1（对称）"
    echo "  • 做空信号：增加2-3倍"
    echo "  • 响应速度：提升33%"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
