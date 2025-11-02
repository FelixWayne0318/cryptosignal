#!/bin/bash
# ==========================================
# CryptoSignal v6.1 快速启动脚本
# ==========================================

cd ~/cryptosignal

echo "=============================================="
echo "🚀 CryptoSignal v6.1 生产环境启动"
echo "=============================================="
echo ""

# 1. 停止旧进程
echo "停止旧进程..."
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null || true
sleep 2

# 2. 确认停止
if ps aux | grep realtime_signal_scanner | grep -v grep; then
    echo "⚠️ 仍有进程运行，强制终止..."
    ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# 3. 检查配置
if [ ! -f "config/binance_credentials.json" ]; then
    echo "❌ Binance API配置不存在: config/binance_credentials.json"
    exit 1
fi

if [ ! -f "config/telegram.json" ]; then
    echo "⚠️ Telegram配置不存在，将无法发送通知"
fi

# 4. 创建logs目录
mkdir -p logs

# 5. 启动
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "启动生产模式..."
echo "  • 扫描间隔: 5分钟 (300秒)"
echo "  • 币种数量: 140个（完整扫描）"
echo "  • Telegram: 已启用"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 方式选择
echo "请选择启动方式："
echo "  1) Screen 会话（推荐，可分离）"
echo "  2) 后台运行（nohup）"
echo "  3) 前台运行（直接显示日志）"
echo ""
read -p "请输入选项 [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "启动 Screen 会话..."
        echo "提示：初始化完成后按 Ctrl+A 然后 D 分离会话"
        echo "重连命令: screen -r cryptosignal"
        sleep 2
        screen -S cryptosignal python3 scripts/realtime_signal_scanner.py --interval 300
        ;;
    2)
        LOG_FILE="logs/scanner_$(date +%Y%m%d_%H%M%S).log"
        echo ""
        echo "后台启动..."
        nohup python3 scripts/realtime_signal_scanner.py --interval 300 > "$LOG_FILE" 2>&1 &
        PID=$!
        echo "✅ 已启动，PID: $PID"
        echo "日志文件: $LOG_FILE"
        echo ""
        echo "查看日志: tail -f $LOG_FILE"
        echo "停止进程: kill $PID"
        ;;
    3)
        echo ""
        echo "前台启动（按Ctrl+C停止）..."
        python3 scripts/realtime_signal_scanner.py --interval 300
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
