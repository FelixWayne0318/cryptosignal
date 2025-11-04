#!/bin/bash
# ==========================================
# CryptoSignal 自动重启脚本
# 用途：定时停止旧进程，拉取最新代码，重新启动
# ==========================================

echo "=========================================="
echo "🔄 CryptoSignal 自动重启"
echo "时间: $(date)"
echo "=========================================="

# 1. 停止旧进程
echo "📍 步骤1: 停止旧进程..."
pkill -f "python.*cryptosignal" || echo "   没有运行中的进程"
pkill -f "deploy_and_run" || true
sleep 2

# 2. 切换到项目目录
cd ~/cryptosignal || exit 1

# 3. 拉取最新代码
echo ""
echo "📍 步骤2: 拉取最新代码..."
git fetch origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git checkout claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git pull origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

# 4. 重新启动（后台运行）
echo ""
echo "📍 步骤3: 重新启动系统..."
echo "=========================================="
echo ""

# 以nohup方式在后台运行，输出重定向到日志文件
nohup ./deploy_and_run.sh > ~/cryptosignal_$(date +%Y%m%d_%H%M%S).log 2>&1 &

echo "✅ 重启完成！进程ID: $!"
echo "📋 查看日志: tail -f ~/cryptosignal_*.log"
echo ""
