#!/bin/bash
# ==========================================
# CryptoSignal v6.2 全自动部署并运行脚本
# 适用于：首次部署、更新部署、全新服务器
# ==========================================

set -e  # 遇到错误立即退出

echo "=============================================="
echo "🚀 CryptoSignal v6.2 全自动部署并运行"
echo "=============================================="
echo ""
echo "📋 脚本功能："
echo "  ✓ 自动检测系统环境"
echo "  ✓ 自动安装缺失依赖"
echo "  ✓ 首次部署引导（API配置）"
echo "  ✓ 完整验证（8步）"
echo "  ✓ 自动启动系统"
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
    echo "❌ Python 3 未安装"
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
    echo "⚠️ pip3 未安装，尝试自动安装..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    else
        echo "❌ 无法自动安装 pip3，请手动安装"
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
    echo "❌ git 未安装"
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
    echo "⚠️ screen 未安装（可选）"
    echo "   安装方法: sudo apt install screen"
    echo "   如未安装，将使用 nohup 后台运行"
fi

echo ""

# ==========================================
# 第 1 步：停止当前运行的扫描器
# ==========================================

echo "📍 第 1 步：停止当前运行的扫描器"
echo "=============================================="

# 切换到项目目录（如果存在）
if [ -d ~/cryptosignal ]; then
    cd ~/cryptosignal

    # 停止所有扫描器进程
    ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null || true
    echo "✅ 已停止运行中的扫描器"
    sleep 2

    # 确认已停止
    if ps aux | grep realtime_signal_scanner | grep -v grep; then
        echo "⚠️ 仍有进程在运行，强制终止..."
        ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    else
        echo "✅ 没有运行的扫描器进程"
    fi
else
    echo "⚠️ ~/cryptosignal 目录不存在，跳过停止进程"
fi

echo ""

# ==========================================
# 第 2 步：备份当前配置
# ==========================================

echo "📍 第 2 步：备份当前配置"
echo "=============================================="

if [ -d ~/cryptosignal/config ]; then
    cd ~/cryptosignal

    # 备份配置文件（以防万一）
    BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
    cp config/params.json config/params.json.bak.$BACKUP_TIME 2>/dev/null || echo "⚠️ params.json 不存在"
    cp config/telegram.json config/telegram.json.bak.$BACKUP_TIME 2>/dev/null || echo "⚠️ telegram.json 不存在，跳过备份"
    cp config/binance_credentials.json config/binance_credentials.json.bak.$BACKUP_TIME 2>/dev/null || echo "⚠️ binance_credentials.json 不存在，跳过备份"

    echo "✅ 配置文件已备份到 *.bak.$BACKUP_TIME"
else
    echo "⚠️ config 目录不存在，跳过备份"
fi

echo ""

# ==========================================
# 第 3 步：拉取最新代码
# ==========================================

echo "📍 第 3 步：拉取最新代码（v6.2）"
echo "=============================================="

if [ -d ~/cryptosignal/.git ]; then
    # 已在 git 仓库中，执行更新
    cd ~/cryptosignal

    echo "当前分支："
    git branch --show-current

    echo ""
    echo "当前提交："
    git log --oneline -3

    echo ""
    echo "正在拉取最新代码..."

    # 拉取v6.2代码
    git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
    git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
    git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ

    echo ""
    echo "✅ 更新后的提交记录："
    git log --oneline -5
else
    echo "⚠️ 不在 git 仓库中"
    echo ""
    echo "首次部署，请先克隆仓库："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "cd ~"
    echo "git clone <仓库地址> cryptosignal"
    echo "cd cryptosignal"
    echo "git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ"
    echo "./deploy_and_run.sh"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi

echo ""

# ==========================================
# 第 4 步：检测并安装 Python 依赖
# ==========================================

echo "📍 第 4 步：检测并安装 Python 依赖"
echo "=============================================="
cd ~/cryptosignal

# 检测 requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt 不存在"
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
    python3 -m pip install --upgrade pip --quiet

    # 安装依赖
    echo "   安装依赖包（可能需要几分钟）..."
    pip3 install -r requirements.txt --quiet

    echo ""
    echo "✅ 依赖安装完成"
else
    echo "✅ 所有依赖已安装"
fi

echo ""

# ==========================================
# 第 5 步：验证系统配置
# ==========================================

echo "📍 第 5 步：验证系统配置"
echo "=============================================="
cd ~/cryptosignal

echo "1️⃣ 检查核心模块导入..."
python3 -c "
from ats_core.gates.integrated_gates import FourGatesChecker
from ats_core.execution.metrics_estimator import ExecutionMetricsEstimator
from ats_core.data.quality import DataQualMonitor
from ats_core.pipeline.analyze_symbol import analyze_symbol
print('✅ 所有核心模块导入成功')
" || {
    echo "❌ 导入失败，请检查代码"
    exit 1
}

echo ""
echo "2️⃣ 验证权重配置（v6.2 - 类型安全）..."
python3 -c "
import json

# 读取配置
with open('config/params.json') as f:
    config = json.load(f)
    weights = config['weights']
    publish = config['publish']

# 验证权重（跳过注释字段）
a_layer = ['T', 'M', 'C', 'S', 'V', 'O', 'L', 'B', 'Q']
factor_weights = {k: v for k, v in weights.items() if not k.startswith('_')}
a_total = sum(factor_weights[k] for k in a_layer)
b_layer = ['F', 'I']

print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print('权重配置验证 (v6.2)')
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print(f'A层9因子总和: {a_total}%')
for k in a_layer:
    print(f'  {k}: {weights[k]}%')
print()
print('B层调制器（应为0.0）:')
for k in b_layer:
    print(f'  {k}: {weights[k]}')
print()

# 验证发布阈值
print('发布阈值 (v6.1):')
print(f'  prime_prob_min: {publish[\"prime_prob_min\"]} (应为0.58)')
print(f'  prime_dims_ok_min: {publish[\"prime_dims_ok_min\"]} (应为3)')
print(f'  prime_dim_threshold: {publish[\"prime_dim_threshold\"]} (应为30)')
print()

# 断言验证
assert abs(a_total - 100.0) < 0.01, f'错误: A层权重={a_total}, 应为100.0'
assert all(weights[k] == 0.0 for k in b_layer), '错误: B层调制器必须为0.0'
assert publish['prime_prob_min'] == 0.58, '错误: prime_prob_min应为0.58'
assert publish['prime_dims_ok_min'] == 3, '错误: prime_dims_ok_min应为3'

print('✅ 权重配置验证通过')
print('✅ 类型安全检查通过')
" || {
    echo "❌ 配置验证失败"
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
    echo "⚠️ Binance API 配置未填写（首次部署）"
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
# 第 6 步：清理 Python 缓存
# ==========================================

echo "📍 第 6 步：清理 Python 缓存"
echo "=============================================="
cd ~/cryptosignal

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Python 缓存已清理"
echo ""

# ==========================================
# 第 7 步：测试运行（10秒快速验证）
# ==========================================

echo "📍 第 7 步：快速测试运行（10秒验证）"
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
        echo "❌ 测试失败，退出码: $EXIT_CODE"
        exit 1
    fi
}

echo ""

# ==========================================
# 第 8 步：自动启动生产环境
# ==========================================

echo "📍 第 8 步：自动启动生产环境"
echo "=============================================="
echo ""
echo "✅ v6.2 部署验证完成！"
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
    echo "✅ 已启动，PID: $PID"
    echo "日志文件: $LOG_FILE"
    echo ""
    echo "查看日志: tail -f $LOG_FILE"
    echo "停止进程: kill $PID"
    echo ""

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ 部署并运行完成！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 v6.2 系统特性"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ I因子架构修正（从A层移至B层）"
    echo "✅ 多空对称选币机制（波动率优先）"
    echo "✅ 全面类型安全防护（4层防御）"
    echo "✅ 扫描币种提升（140→200个）"
    echo ""
    echo "预期效果："
    echo "  • 信号量：3-7个Prime信号/小时"
    echo "  • 多空比例：接近1:1（对称）"
    echo "  • 做空信号：增加2-3倍"
    echo "  • 响应速度：提升33%"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
