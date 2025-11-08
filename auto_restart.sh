#!/bin/bash
# ==========================================
# CryptoSignal 自动重启脚本
# 用途：停止旧进程，拉取最新代码，重新启动
# 使用场景：
#   1. Cron定时重启（每2小时）
#   2. 手动重启
# ==========================================

echo "=========================================="
echo "🔄 CryptoSignal 自动重启"
echo "时间: $(date)"
echo "=========================================="

# 1. 停止旧进程
echo "📍 步骤1: 停止旧进程..."
pkill -f "python.*cryptosignal" || echo "   没有运行中的进程"
pkill -f "deploy_and_run" || true
pkill -f "full_run_v2" || true
pkill -f "auto_scan_prime" || true

# 清理旧的screen会话
echo "   清理旧的screen会话..."
screen -ls 2>/dev/null | grep cryptosignal | cut -d. -f1 | awk '{print $1}' | xargs -I {} screen -S {} -X quit 2>/dev/null || true
sleep 2

# 2. 切换到项目目录
cd ~/cryptosignal || {
    echo "❌ 错误: ~/cryptosignal 目录不存在"
    echo "请先运行: ./setup.sh"
    exit 1
}

# 3. 拉取最新代码
echo ""
echo "📍 步骤2: 拉取最新代码..."

# 获取当前分支
CURRENT_BRANCH=$(git branch --show-current)

# 拉取代码（带重试）
MAX_RETRIES=3
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if git fetch origin "$CURRENT_BRANCH" && git pull origin "$CURRENT_BRANCH"; then
        echo "✅ 代码更新完成"
        break
    else
        RETRY=$((RETRY + 1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            echo "⚠️  拉取失败，2秒后重试 ($RETRY/$MAX_RETRIES)..."
            sleep 2
        else
            echo "⚠️  拉取失败，使用当前代码继续..."
        fi
    fi
done

# 4. 调用 setup.sh（禁用自动提交）
echo ""
echo "📍 步骤3: 重新启动系统..."
echo "=========================================="
echo ""

# 设置环境变量：禁用自动提交
export AUTO_COMMIT_REPORTS=false

# 调用 setup.sh 启动系统
./setup.sh

echo "✅ 重启完成！进程ID: $!"
echo "📋 查看日志: tail -f ~/cryptosignal_*.log"
echo ""
