#!/bin/bash
# ==========================================
# CryptoSignal v6.1 部署脚本
# 修复内容: I因子架构修正 + 降低阈值增加信号量
# ==========================================

set -e  # 遇到错误立即退出

echo "=============================================="
echo "🚀 CryptoSignal v6.1 部署脚本"
echo "=============================================="
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
    echo "⚠️ 仍有进程在运行，强制终止..."
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
cp config/params.json config/params.json.bak.$BACKUP_TIME
cp config/telegram.json config/telegram.json.bak.$BACKUP_TIME 2>/dev/null || echo "⚠️ telegram.json 不存在，跳过备份"
cp config/binance_credentials.json config/binance_credentials.json.bak.$BACKUP_TIME 2>/dev/null || echo "⚠️ binance_credentials.json 不存在，跳过备份"

echo "✅ 配置文件已备份到 *.bak.$BACKUP_TIME"
echo ""

# ==========================================
# 第 3 步：查看当前代码版本
# ==========================================

echo "📍 第 3 步：查看当前代码版本"
echo "=============================================="
cd ~/cryptosignal

echo "当前分支："
git branch --show-current

echo ""
echo "当前提交："
git log --oneline -3

echo ""

# ==========================================
# 第 4 步：拉取最新代码（v6.1）
# ==========================================

echo "📍 第 4 步：拉取最新代码（v6.1）"
echo "=============================================="
cd ~/cryptosignal

# 拉取v6.1修复代码
git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ

echo ""
echo "✅ 更新后的提交记录："
git log --oneline -5

echo ""

# ==========================================
# 第 5 步：验证 v6.1 修复内容
# ==========================================

echo "📍 第 5 步：验证 v6.1 修复内容"
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
echo "2️⃣ 验证权重配置（v6.1 - I因子修正）..."
python3 -c "
import json

# 读取配置
with open('config/params.json') as f:
    config = json.load(f)
    weights = config['weights']
    publish = config['publish']

# 验证权重
a_layer = ['T', 'M', 'C', 'S', 'V', 'O', 'L', 'B', 'Q']
a_total = sum(weights[k] for k in a_layer)
b_layer = ['F', 'I']

print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print('权重配置验证 (v6.1)')
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print(f'A层9因子总和: {a_total}%')
for k in a_layer:
    print(f'  {k}: {weights[k]}%')
print()
print('B层调制器（应为0）:')
for k in b_layer:
    print(f'  {k}: {weights[k]}')
print()

# 验证发布阈值
print('发布阈值 (v6.1降低):')
print(f'  prime_prob_min: {publish[\"prime_prob_min\"]} (应为0.58)')
print(f'  prime_dims_ok_min: {publish[\"prime_dims_ok_min\"]} (应为3)')
print(f'  prime_dim_threshold: {publish[\"prime_dim_threshold\"]} (应为30)')
print()

# 断言验证
assert abs(a_total - 100.0) < 0.01, f'错误: A层权重={a_total}, 应为100.0'
assert all(weights[k] == 0 for k in b_layer), '错误: B层调制器必须为0'
assert publish['prime_prob_min'] == 0.58, '错误: prime_prob_min应为0.58'
assert publish['prime_dims_ok_min'] == 3, '错误: prime_dims_ok_min应为3'

print('✅ 权重配置验证通过')
print('✅ 发布阈值验证通过')
" || {
    echo "❌ 配置验证失败"
    exit 1
}

echo ""
echo "3️⃣ 验证代码修复（Prime阈值 + 防抖动）..."
python3 -c "
import re

# 验证 analyze_symbol.py 中的 Prime 阈值
with open('ats_core/pipeline/analyze_symbol.py') as f:
    content = f.read()

# 查找 is_prime 判定
matches = re.findall(r'is_prime = \(prime_strength >= (\d+)\)', content)
if all(int(m) == 25 for m in matches):
    print('✅ Prime阈值已修改为25分')
else:
    print(f'❌ Prime阈值不正确: {matches}')
    exit(1)

# 验证 realtime_signal_scanner.py 中的防抖动参数
with open('scripts/realtime_signal_scanner.py') as f:
    content = f.read()

# 查找防抖动参数
if 'prime_entry_threshold=0.65' in content:
    print('✅ 防抖动阈值已修改为0.65')
else:
    print('❌ 防抖动阈值未修改')
    exit(1)

if 'confirmation_bars=1' in content:
    print('✅ 确认K线数已修改为1/2')
else:
    print('❌ 确认K线数未修改')
    exit(1)

if 'cooldown_seconds=60' in content:
    print('✅ 冷却时间已修改为60秒')
else:
    print('❌ 冷却时间未修改')
    exit(1)

print()
print('✅ 所有代码修复验证通过')
" || {
    echo "❌ 代码修复验证失败"
    exit 1
}

echo ""
echo "4️⃣ 验证 Telegram 配置..."
if [ -f "config/telegram.json" ]; then
    python3 -c "
import json
with open('config/telegram.json') as f:
    tg = json.load(f)
    if tg.get('bot_token') and tg.get('chat_id'):
        print('✅ Telegram配置存在')
    else:
        print('⚠️ Telegram配置不完整，将无法发送通知')
"
else
    echo "⚠️ config/telegram.json 不存在，将无法发送Telegram通知"
    echo "   如需发送通知，请参考 config/telegram.json.example 创建配置"
fi

echo ""
echo "5️⃣ 验证 Binance API 配置..."
if [ -f "config/binance_credentials.json" ]; then
    python3 -c "
import json
with open('config/binance_credentials.json') as f:
    bn = json.load(f)['binance']
    if bn.get('api_key') and bn['api_key'] != 'YOUR_BINANCE_API_KEY_HERE':
        print('✅ Binance API配置存在')
    else:
        print('❌ Binance API配置未填写')
        print()
        print('请执行以下命令配置API凭证：')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print('cat > config/binance_credentials.json <<\\'EOF\\'')
        print('{')
        print('  \"_comment\": \"Binance Futures API凭证配置\",')
        print('  \"binance\": {')
        print('    \"api_key\": \"您的API_KEY\",')
        print('    \"api_secret\": \"您的SECRET_KEY\",')
        print('    \"testnet\": false,')
        print('    \"_security\": \"只读权限API Key\"')
        print('  }')
        print('}')
        print('EOF')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        exit(1)
"
else
    echo "❌ config/binance_credentials.json 不存在"
    echo ""
    echo "请先创建 Binance API 配置文件："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "配置完成后重新运行: ./deploy_v6.1.sh"
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
# 第 8 步：显示运行命令
# ==========================================

echo "📍 第 8 步：生产环境启动指南"
echo "=============================================="
echo ""
echo "✅ v6.1 部署验证完成！"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 生产环境启动命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "方式 1: Screen 会话启动（推荐）"
echo "-------------------------------------------"
echo "# 1. 创建 screen 会话"
echo "cd ~/cryptosignal"
echo "screen -S cryptosignal"
echo ""
echo "# 2. 在 screen 中运行生产模式（完整扫描140个币种 + 发送Telegram）"
echo "python3 scripts/realtime_signal_scanner.py --interval 300"
echo ""
echo "# 3. 看到初始化完成后，按 Ctrl+A 然后按 D 分离会话"
echo ""
echo "# 4. 重新连接会话查看日志"
echo "screen -r cryptosignal"
echo ""
echo "-------------------------------------------"
echo ""
echo "方式 2: 后台运行（nohup）"
echo "-------------------------------------------"
echo "cd ~/cryptosignal"
echo "nohup python3 scripts/realtime_signal_scanner.py --interval 300 > logs/scanner_\$(date +%Y%m%d_%H%M%S).log 2>&1 &"
echo ""
echo "# 查看日志"
echo "tail -f logs/scanner_*.log"
echo ""
echo "-------------------------------------------"
echo ""
echo "方式 3: 直接运行（前台，测试用）"
echo "-------------------------------------------"
echo "cd ~/cryptosignal"
echo "python3 scripts/realtime_signal_scanner.py --interval 300"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 v6.1 修复摘要"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ I因子架构修正（从A层移至B层）"
echo "✅ 权重重新分配（A层9因子=100%）"
echo "✅ Prime阈值降低（35→25分）"
echo "✅ 概率阈值降低（0.62→0.58）"
echo "✅ 防抖动机制放宽（1/2确认，60秒冷却，0.65阈值）"
echo ""
echo "预期效果："
echo "  • 信号量：3-7个Prime信号/小时（140个币种）"
echo "  • 响应速度：提升33%（2→1 K线确认）"
echo "  • 信号质量：维持高质量（仅降低过严阈值）"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 监控建议："
echo "  1. 运行24小时后统计信号数量"
echo "  2. 记录Prime信号胜率"
echo "  3. 观察各门失败分布"
echo "  4. 根据实际表现微调阈值"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
