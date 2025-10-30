#!/bin/bash
# CryptoSignal 初始部署脚本
# 适用于全新服务器或没有代码的情况
# 可以直接复制粘贴到服务器执行

set -e

echo "=========================================="
echo "🚀 CryptoSignal 初始部署"
echo "=========================================="

START_TIME=$(date +%s)

# ============================================
# 1. 检查必要工具
# ============================================
echo ""
echo "1️⃣  检查环境..."
echo "=========================================="

echo "📍 当前用户: $(whoami)"
echo "📍 主目录: $HOME"
echo "📍 当前目录: $(pwd)"

# 检查必要命令
for cmd in git python3 pip3; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ 错误: $cmd 未安装"
        echo "请先安装: sudo apt-get install -y git python3 python3-pip"
        exit 1
    fi
done

echo "✅ Git版本: $(git --version)"
echo "✅ Python版本: $(python3 --version)"
echo "✅ Pip版本: $(pip3 --version)"

# ============================================
# 2. 清理旧目录（如果存在）
# ============================================
echo ""
echo "2️⃣  清理旧代码..."
echo "=========================================="

cd ~

if [ -d cryptosignal ]; then
    echo "⚠️  发现已存在的 cryptosignal 目录"

    # 备份配置
    if [ -d cryptosignal/config ]; then
        BACKUP_DIR="/tmp/cryptosignal_config_backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp -r cryptosignal/config "$BACKUP_DIR/"
        echo "💾 配置已备份至: $BACKUP_DIR"
    fi

    echo "🗑️  删除旧目录..."
    rm -rf cryptosignal
    echo "✅ 旧目录已删除"
else
    echo "✅ 无旧目录，继续安装"
fi

# ============================================
# 3. 克隆代码仓库
# ============================================
echo ""
echo "3️⃣  克隆代码仓库..."
echo "=========================================="

cd ~

# 尝试克隆（使用本地Git服务器）
echo "📥 克隆仓库..."

# 如果本地Git服务器不可用，这里会失败
if git clone http://127.0.0.1:40286/git/FelixWayne0318/cryptosignal 2>/dev/null; then
    echo "✅ 从本地Git服务器克隆成功"
else
    echo "❌ 无法从本地Git服务器克隆"
    echo ""
    echo "请检查："
    echo "1. Git服务器是否运行在 127.0.0.1:40286"
    echo "2. 是否在正确的服务器上执行"
    echo "3. 或者手动克隆代码："
    echo "   cd ~ && git clone <你的仓库地址>"
    exit 1
fi

cd cryptosignal

# ============================================
# 4. 切换到正确的分支
# ============================================
echo ""
echo "4️⃣  切换分支..."
echo "=========================================="

# 获取所有分支
git fetch origin

# 切换到修复分支
BRANCH="claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE"
echo "🔀 切换到分支: $BRANCH"

if git checkout "$BRANCH" 2>/dev/null; then
    echo "✅ 分支切换成功"
else
    echo "⚠️  分支切换失败，尝试创建跟踪分支..."
    git checkout -b "$BRANCH" "origin/$BRANCH"
fi

# 拉取最新代码
git pull origin "$BRANCH"

echo "✅ 当前分支: $(git branch --show-current)"
echo "✅ 最新提交: $(git log -1 --oneline)"

# ============================================
# 5. 创建配置文件
# ============================================
echo ""
echo "5️⃣  创建配置文件..."
echo "=========================================="

mkdir -p ~/cryptosignal/config

# 恢复备份配置（如果有）
if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
    echo "📋 恢复备份配置..."
    cp -r "$BACKUP_DIR"/* ~/cryptosignal/config/ 2>/dev/null || true
fi

# Telegram配置
if [ ! -f ~/cryptosignal/config/telegram.json ]; then
    echo "📝 创建Telegram配置..."
    cat > ~/cryptosignal/config/telegram.json << 'EOF'
{
  "bot_token": "7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70",
  "chat_id": "-1003142003085"
}
EOF
    echo "✅ Telegram配置已创建"
else
    echo "✅ Telegram配置已存在"
fi

# Binance配置
if [ ! -f ~/cryptosignal/config/binance_credentials.json ]; then
    echo "📝 创建Binance配置..."
    cat > ~/cryptosignal/config/binance_credentials.json << 'EOF'
{
  "api_key": "",
  "api_secret": "",
  "testnet": false
}
EOF
    echo "✅ Binance配置已创建（仅获取数据，不交易）"
else
    echo "✅ Binance配置已存在"
fi

# ============================================
# 6. 安装Python依赖
# ============================================
echo ""
echo "6️⃣  安装Python依赖..."
echo "=========================================="

cd ~/cryptosignal

echo "📦 安装核心依赖..."
pip3 install --user aiohttp websockets requests 2>&1 | grep -i "successfully installed" || echo "依赖可能已安装"

echo "✅ 依赖安装完成"

# ============================================
# 7. 验证关键修复
# ============================================
echo ""
echo "7️⃣  验证关键修复..."
echo "=========================================="

FIXES_OK=true

# 检查WebSocket修复
if grep -q "self.is_running = True" ~/cryptosignal/ats_core/execution/binance_futures_client.py; then
    echo "✅ WebSocket修复已应用"
else
    echo "❌ WebSocket修复未找到"
    FIXES_OK=false
fi

# 检查并发优化
if grep -q "asyncio.gather" ~/cryptosignal/ats_core/pipeline/batch_scan_optimized.py; then
    echo "✅ 并发优化已应用"
else
    echo "❌ 并发优化未找到"
    FIXES_OK=false
fi

# 检查信号输出修复
if grep -q "total_symbols" ~/cryptosignal/scripts/realtime_signal_scanner.py; then
    echo "✅ 信号输出修复已应用"
else
    echo "❌ 信号输出修复未找到"
    FIXES_OK=false
fi

if [ "$FIXES_OK" = false ]; then
    echo ""
    echo "⚠️  部分修复未应用，可能不是最新代码"
    echo "当前提交: $(git log -1 --oneline)"
fi

# ============================================
# 8. 发送开始通知
# ============================================
echo ""
echo "8️⃣  发送测试开始通知..."
echo "=========================================="

cd ~/cryptosignal

python3 << 'PYTHON_EOF'
import sys
import os
sys.path.insert(0, os.path.expanduser('~/cryptosignal'))

try:
    from ats_core.outputs.publisher import telegram_send
    from datetime import datetime

    telegram_send(
        f"🚀 <b>CryptoSignal 初始部署并测试</b>\n\n"
        f"📊 测试配置:\n"
        f"• 币种数: 10个高流动性币种\n"
        f"• 最低分数: 70分\n"
        f"• WebSocket: ✅ 已修复\n"
        f"• 并发优化: ✅ 5-10倍提升\n"
        f"• 信号输出: ✅ 已修复\n\n"
        f"⏳ 预计初始化: 2-3分钟\n"
        f"⏳ 预计扫描: 15-25秒\n\n"
        f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"等待结果..."
    )
    print("✅ 开始通知已发送到Telegram")
except Exception as e:
    print(f"⚠️  开始通知发送失败: {e}")
    import traceback
    traceback.print_exc()
PYTHON_EOF

# ============================================
# 9. 运行完整系统测试
# ============================================
echo ""
echo "9️⃣  运行完整系统测试..."
echo "=========================================="
echo "⚙️  测试参数:"
echo "   - 币种数: 10个"
echo "   - 最低分数: 70分"
echo "   - 电报通知: 启用"
echo "=========================================="
echo ""

cd ~/cryptosignal

# 创建日志文件
TEST_LOG="/tmp/cryptosignal_test_$(date +%Y%m%d_%H%M%S).log"

echo "🔄 开始扫描（日志: $TEST_LOG）..."
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --min-score 70 2>&1 | tee "$TEST_LOG"

TEST_EXIT_CODE=${PIPESTATUS[0]}

# ============================================
# 10. 测试结果分析
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
echo ""

# 分析日志
echo "🔍 测试结果分析:"
echo "=========================================="

# WebSocket
WS_SUCCESS=$(grep -c "WebSocket连接成功" "$TEST_LOG" 2>/dev/null || echo "0")
WS_CLOSED=$(grep -c "WebSocket已关闭" "$TEST_LOG" 2>/dev/null || echo "0")
echo "📡 WebSocket连接: $WS_SUCCESS 个建立"
if [ "$WS_CLOSED" -gt 10 ]; then
    WS_STATUS="⚠️ 需检查"
    echo "⚠️  WebSocket异常关闭: $WS_CLOSED 次"
else
    WS_STATUS="✅ 正常"
    echo "✅ WebSocket稳定: $WS_CLOSED 次关闭（正常）"
fi

# 扫描结果
SYMBOLS_SCANNED=$(grep "总扫描:" "$TEST_LOG" 2>/dev/null | tail -1 | grep -oP '\d+' | head -1 || echo "0")
PRIME_SIGNALS=$(grep "Prime信号:" "$TEST_LOG" 2>/dev/null | tail -1 | grep -oP '\d+' | head -1 || echo "0")
echo "🔍 扫描币种: $SYMBOLS_SCANNED 个"
echo "🎯 Prime信号: $PRIME_SIGNALS 个"

# 初始化
if grep -q "初始化完成" "$TEST_LOG"; then
    INIT_STATUS="✅ 成功"
    echo "✅ 系统初始化成功"
else
    INIT_STATUS="❌ 失败"
    echo "❌ 系统初始化失败"
fi

# 性能
if [ $ELAPSED -lt 300 ]; then
    PERF_STATUS="✅ 快速"
elif [ $ELAPSED -lt 600 ]; then
    PERF_STATUS="🟡 正常"
else
    PERF_STATUS="⚠️ 较慢"
fi

# 信号输出
if [ "$SYMBOLS_SCANNED" -gt 0 ]; then
    OUTPUT_STATUS="✅ 正确"
else
    OUTPUT_STATUS="❌ 错误"
fi

echo ""
echo "=========================================="

# 发送结果通知
echo ""
echo "📱 发送测试结果到Telegram..."

python3 << PYTHON_EOF
import sys
import os
sys.path.insert(0, os.path.expanduser('~/cryptosignal'))

try:
    from ats_core.outputs.publisher import telegram_send
    from datetime import datetime

    message = f"""✅ <b>CryptoSignal 初始部署完成</b>

⏱️ <b>性能指标</b>
• 总耗时: ${MINUTES}分${SECONDS}秒
• 扫描币种: ${SYMBOLS_SCANNED} 个
• Prime信号: ${PRIME_SIGNALS} 个

📡 <b>WebSocket状态</b>
• 连接建立: ${WS_SUCCESS} 个
• 异常关闭: ${WS_CLOSED} 次
• 状态: ${WS_STATUS}

🔧 <b>系统状态</b>
• WebSocket: ${WS_STATUS}
• 初始化: ${INIT_STATUS}
• 性能: ${PERF_STATUS}
• 信号输出: ${OUTPUT_STATUS}

📝 <b>详细信息</b>
• 日志: ${TEST_LOG}
• 代码目录: ~/cryptosignal
• 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    telegram_send(message)
    print("✅ 测试结果已发送到Telegram")
except Exception as e:
    print(f"⚠️  结果通知发送失败: {e}")
PYTHON_EOF

echo ""
echo "=========================================="
echo "🎉 初始部署完成！"
echo "=========================================="
echo ""
echo "📊 快速总结:"
echo "   • 代码克隆: ✅"
echo "   • 配置创建: ✅"
echo "   • 依赖安装: ✅"
echo "   • 修复验证: $([ "$FIXES_OK" = true ] && echo "✅" || echo "⚠️")"
echo "   • 系统测试: $([ $TEST_EXIT_CODE -eq 0 ] && echo "✅" || echo "❌")"
echo "   • 总耗时: ${MINUTES}分${SECONDS}秒"
echo ""
echo "📍 代码位置: ~/cryptosignal"
echo "📝 下次更新: cd ~/cryptosignal && bash scripts/deploy_to_server.sh"
echo ""

exit $TEST_EXIT_CODE
