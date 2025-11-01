#!/bin/bash
################################################################################
# CryptoSignal v6.1 一键部署脚本
# 复制本脚本内容到服务器执行，或直接运行：
# bash <(curl -s https://raw.githubusercontent.com/.../ONE_COMMAND_DEPLOY.sh)
################################################################################

set -e

echo "========================================================================"
echo "🚀 CryptoSignal v6.1 一键部署"
echo "========================================================================"
echo ""

# 进入项目目录
cd ~/cryptosignal || {
    echo "❌ 目录不存在: ~/cryptosignal"
    exit 1
}

# 停止旧进程
echo "停止旧进程..."
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null || true
sleep 2

# 备份配置
echo "备份配置..."
BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
cp config/params.json config/params.json.bak.$BACKUP_TIME 2>/dev/null || true
cp config/telegram.json config/telegram.json.bak.$BACKUP_TIME 2>/dev/null || true
cp config/binance_credentials.json config/binance_credentials.json.bak.$BACKUP_TIME 2>/dev/null || true

# 拉取最新代码
echo "拉取v6.1代码..."
git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ

# 清理缓存
echo "清理缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 验证配置
echo "验证配置..."
python3 -c "
import json
with open('config/params.json') as f:
    w = json.load(f)['weights']
    assert sum(w[k] for k in ['T','M','C','S','V','O','L','B','Q']) == 100.0
    print('✅ 权重配置正确')
" || exit 1

# 启动
echo ""
echo "========================================================================"
echo "✅ 部署完成！"
echo "========================================================================"
echo ""
echo "现在启动生产环境..."
echo ""

# 创建logs目录
mkdir -p logs

# 使用Screen启动
if command -v screen &> /dev/null; then
    echo "使用Screen会话启动..."
    echo "提示：初始化完成后按 Ctrl+A 然后 D 分离会话"
    sleep 2
    screen -S cryptosignal python3 scripts/realtime_signal_scanner.py --interval 300
else
    echo "Screen未安装，使用nohup后台启动..."
    LOG_FILE="logs/scanner_$(date +%Y%m%d_%H%M%S).log"
    nohup python3 scripts/realtime_signal_scanner.py --interval 300 > "$LOG_FILE" 2>&1 &
    PID=$!
    echo "✅ 已启动，PID: $PID"
    echo "日志文件: $LOG_FILE"
    echo "查看日志: tail -f $LOG_FILE"
fi
