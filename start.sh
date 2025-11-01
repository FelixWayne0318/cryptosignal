#!/bin/bash
# 快速启动脚本（定期扫描模式，每5分钟）

cd /home/user/cryptosignal

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull

# 启动扫描器
echo "🚀 启动实时信号扫描器（每5分钟扫描一次）..."
echo "   按Ctrl+C停止"
echo ""

python3 scripts/realtime_signal_scanner.py --interval 300 --min-score 70
