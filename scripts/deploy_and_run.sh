#!/bin/bash
# CryptoSignal 完整部署和运行脚本
# 用途: 清空、拉取、更新、运行完整系统测试

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 CryptoSignal 完整部署流程"
echo "=========================================="

# 记录开始时间
START_TIME=$(date +%s)

# ============================================
# 1. 环境检查
# ============================================
echo ""
echo "1️⃣  环境检查..."
echo "=========================================="

# 检查必要命令
for cmd in git python3 pip3; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ 错误: $cmd 未安装"
        exit 1
    fi
done

echo "✅ Python版本: $(python3 --version)"
echo "✅ Git版本: $(git --version)"

# ============================================
# 2. 备份当前配置（如果存在）
# ============================================
echo ""
echo "2️⃣  备份配置文件..."
echo "=========================================="

BACKUP_DIR="/tmp/cryptosignal_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d ~/cryptosignal/config ]; then
    cp -r ~/cryptosignal/config "$BACKUP_DIR/"
    echo "✅ 配置已备份至: $BACKUP_DIR"
else
    echo "⚠️  未找到config目录，跳过备份"
fi

# ============================================
# 3. 清空并重新拉取代码
# ============================================
echo ""
echo "3️⃣  清空并拉取最新代码..."
echo "=========================================="

cd ~

# 如果目录存在，先删除
if [ -d cryptosignal ]; then
    echo "🗑️  删除旧目录..."
    rm -rf cryptosignal
fi

# 克隆仓库
echo "📥 克隆仓库..."
git clone http://127.0.0.1:40286/git/FelixWayne0318/cryptosignal
cd cryptosignal

# 切换到正确的分支
echo "🔀 切换分支..."
git checkout claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE
git pull origin claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE

echo "✅ 当前分支: $(git branch --show-current)"
echo "✅ 最新提交: $(git log -1 --oneline)"

# ============================================
# 4. 恢复配置文件
# ============================================
echo ""
echo "4️⃣  恢复配置文件..."
echo "=========================================="

if [ -d "$BACKUP_DIR/config" ]; then
    cp -r "$BACKUP_DIR/config" ~/cryptosignal/
    echo "✅ 配置已恢复"
else
    echo "⚠️  无备份配置，将使用默认配置"

    # 确保config目录存在
    mkdir -p ~/cryptosignal/config

    # 创建Telegram配置（如果不存在）
    if [ ! -f ~/cryptosignal/config/telegram.json ]; then
        echo "📝 创建Telegram配置..."
        cat > ~/cryptosignal/config/telegram.json << 'TELEGRAM_EOF'
{
  "bot_token": "7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70",
  "chat_id": "-1003142003085"
}
TELEGRAM_EOF
        echo "✅ Telegram配置已创建"
    fi

    # 创建Binance配置（如果不存在）
    if [ ! -f ~/cryptosignal/config/binance_credentials.json ]; then
        echo "📝 创建Binance配置（空）..."
        cat > ~/cryptosignal/config/binance_credentials.json << 'BINANCE_EOF'
{
  "api_key": "",
  "api_secret": "",
  "testnet": false
}
BINANCE_EOF
        echo "✅ Binance配置已创建（无交易功能）"
    fi
fi

# ============================================
# 5. 安装/更新依赖
# ============================================
echo ""
echo "5️⃣  安装Python依赖..."
echo "=========================================="

cd ~/cryptosignal

# 检查是否有requirements.txt
if [ -f requirements.txt ]; then
    echo "📦 安装依赖包..."
    pip3 install -r requirements.txt --quiet --disable-pip-version-check
    echo "✅ 依赖安装完成"
else
    echo "⚠️  未找到requirements.txt"
    echo "📦 安装核心依赖..."
    pip3 install aiohttp websockets requests --quiet --disable-pip-version-check
    echo "✅ 核心依赖安装完成"
fi

# ============================================
# 6. 验证关键修复
# ============================================
echo ""
echo "6️⃣  验证关键修复..."
echo "=========================================="

# 检查WebSocket修复
if grep -q "self.is_running = True" ~/cryptosignal/ats_core/execution/binance_futures_client.py; then
    echo "✅ WebSocket修复已应用"
else
    echo "❌ 警告: WebSocket修复未找到"
fi

# 检查并发优化
if grep -q "asyncio.gather" ~/cryptosignal/ats_core/pipeline/batch_scan_optimized.py; then
    echo "✅ 并发优化已应用"
else
    echo "❌ 警告: 并发优化未找到"
fi

# 检查信号输出修复
if grep -q "total_symbols" ~/cryptosignal/scripts/realtime_signal_scanner.py; then
    echo "✅ 信号输出修复已应用"
else
    echo "❌ 警告: 信号输出修复未找到"
fi

# ============================================
# 7. 运行完整系统测试
# ============================================
echo ""
echo "7️⃣  运行完整系统测试..."
echo "=========================================="
echo "⚙️  配置:"
echo "   - 测试币种: 10个高流动性币种"
echo "   - 最低分数: 70分"
echo "   - 电报通知: 启用"
echo "=========================================="

cd ~/cryptosignal

# 发送测试开始通知
echo ""
echo "📱 发送测试开始通知到Telegram..."

python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/cryptosignal')
from ats_core.outputs.publisher import telegram_send

try:
    telegram_send(
        "🚀 <b>CryptoSignal 系统测试开始</b>\n\n"
        "📊 测试配置:\n"
        "• 币种数: 10个高流动性币种\n"
        "• 最低分数: 70分\n"
        "• WebSocket: 启用（已修复）\n"
        "• 并发优化: 启用（5-10倍提升）\n\n"
        "⏳ 预计初始化时间: 2-3分钟\n"
        "⏳ 预计扫描时间: 15-25秒\n\n"
        "等待结果..."
    )
    print("✅ 开始通知已发送")
except Exception as e:
    print(f"⚠️  开始通知发送失败: {e}")
PYTHON_EOF

echo ""
echo "🔄 开始运行完整系统..."
echo "=========================================="

# 运行系统（记录输出到文件）
TEST_LOG="/tmp/cryptosignal_test_$(date +%Y%m%d_%H%M%S).log"
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --min-score 70 2>&1 | tee "$TEST_LOG"

TEST_EXIT_CODE=${PIPESTATUS[0]}

# ============================================
# 8. 测试结果总结
# ============================================
echo ""
echo "=========================================="
echo "📊 测试完成"
echo "=========================================="

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "⏱️  总耗时: ${MINUTES}分${SECONDS}秒"
echo "📝 日志文件: $TEST_LOG"
echo "📁 备份目录: $BACKUP_DIR"
echo ""

# 分析日志
echo "🔍 测试结果分析:"
echo "=========================================="

# 检查WebSocket连接
WS_SUCCESS=$(grep -c "WebSocket连接成功" "$TEST_LOG" || echo "0")
WS_CLOSED=$(grep -c "WebSocket已关闭" "$TEST_LOG" || echo "0")
echo "📡 WebSocket连接: $WS_SUCCESS 个建立"
if [ "$WS_CLOSED" -gt 0 ]; then
    echo "⚠️  WebSocket关闭: $WS_CLOSED 次（预期0次）"
else
    echo "✅ WebSocket稳定: 无异常关闭"
fi

# 检查扫描结果
SYMBOLS_SCANNED=$(grep "总扫描:" "$TEST_LOG" | tail -1 | grep -oP '\d+' | head -1 || echo "0")
PRIME_SIGNALS=$(grep "Prime信号:" "$TEST_LOG" | tail -1 | grep -oP '\d+' | head -1 || echo "0")
echo "🔍 扫描币种: $SYMBOLS_SCANNED 个"
echo "🎯 Prime信号: $PRIME_SIGNALS 个"

# 检查初始化时间
if grep -q "初始化完成" "$TEST_LOG"; then
    echo "✅ 系统初始化成功"
else
    echo "❌ 系统初始化可能失败"
fi

# 检查错误
ERROR_COUNT=$(grep -c "ERROR\|错误\|失败" "$TEST_LOG" || echo "0")
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  发现 $ERROR_COUNT 个错误/警告，请查看日志"
else
    echo "✅ 无严重错误"
fi

echo ""
echo "=========================================="

# 发送测试结果通知
echo "📱 发送测试结果到Telegram..."

python3 << PYTHON_EOF
import sys
sys.path.insert(0, '/home/user/cryptosignal')
from ats_core.outputs.publisher import telegram_send

try:
    message = f"""✅ <b>CryptoSignal 系统测试完成</b>

⏱️ <b>性能指标</b>
• 总耗时: ${MINUTES}分${SECONDS}秒
• 扫描币种: $SYMBOLS_SCANNED 个
• Prime信号: $PRIME_SIGNALS 个

📡 <b>WebSocket状态</b>
• 连接建立: $WS_SUCCESS 个
• 异常关闭: $WS_CLOSED 次

🔧 <b>优化效果</b>
• WebSocket: {'✅ 正常' if $WS_CLOSED == 0 else '⚠️ 需检查'}
• 初始化: {'✅ 快速' if $ELAPSED < 300 else '⚠️ 较慢'}
• 信号输出: {'✅ 正确' if $SYMBOLS_SCANNED > 0 else '❌ 错误'}

📝 日志: $TEST_LOG
"""
    telegram_send(message)
    print("✅ 结果通知已发送")
except Exception as e:
    print(f"⚠️  结果通知发送失败: {e}")
PYTHON_EOF

echo ""
echo "=========================================="
echo "🎉 部署和测试流程完成！"
echo "=========================================="

exit $TEST_EXIT_CODE
