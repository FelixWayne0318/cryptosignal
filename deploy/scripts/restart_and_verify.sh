#!/bin/bash

# 重启服务并验证v7.4修复

echo "========================================="
echo "🔄 重启服务并验证v7.4修复"
echo "========================================="
echo ""

# 1. 拉取最新代码
echo "1️⃣ 拉取最新代码..."
git pull
echo ""

# 2. 停止旧进程
echo "2️⃣ 停止旧进程..."
pkill -f "realtime_signal_scanner"
sleep 2
echo "✅ 旧进程已停止"
echo ""

# 3. 清理Python缓存
echo "3️⃣ 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "✅ Python缓存已清理"
echo ""

# 4. 重启服务
echo "4️⃣ 重启服务..."
nohup ./setup.sh > /tmp/cryptosignal_restart.log 2>&1 &
sleep 5
echo "✅ 服务已重启"
echo ""

# 5. 等待扫描开始
echo "5️⃣ 等待第一次扫描（5分钟）..."
echo "   扫描间隔: 300秒"
echo "   预计下次扫描: $(date -d '+5 minutes' '+%H:%M:%S')"
echo ""
echo "   实时监控命令（另开终端）:"
echo "   tail -f /tmp/cryptosignal_restart.log | grep -E '(🔍|🚀|Step|Entry|v7.4)'"
echo ""

# 6. 提示下一步
echo "========================================="
echo "✅ 重启完成"
echo "========================================="
echo ""
echo "📊 验证步骤："
echo "1. 等待5-10分钟，让扫描周期开始"
echo "2. 查看日志（应该看到v7.4诊断输出）:"
echo "   tail -f /tmp/cryptosignal_restart.log | grep '🔍'"
echo ""
echo "3. 如果看到这些日志，说明修复成功:"
echo "   🔍 [v7.4诊断] BTCUSDT - four_step_system.enabled=True"
echo "   🚀 v7.4: 启动四步系统 - BTCUSDT (融合模式)"
echo ""
echo "4. 如果还是看不到，请运行:"
echo "   ./diagnose_v74_issue.sh"
echo ""
