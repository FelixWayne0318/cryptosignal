#!/usr/bin/env bash
# 停止所有运行的进程并清空缓存

set -euo pipefail

echo "======================================================================"
echo "🛑 停止运行的进程并清空缓存"
echo "======================================================================"
echo ""

# 1. 停止所有相关进程
echo "1️⃣  停止运行的进程..."

# 查找并停止所有Python扫描进程
PIDS=$(pgrep -f "realtime_scanner|full_run|scan_with_websocket|run_auto_trader" || true)

if [ -n "$PIDS" ]; then
    echo "   发现运行中的进程:"
    ps -p $PIDS -o pid,cmd || true
    echo ""
    echo "   正在停止进程..."
    kill $PIDS || true
    sleep 2

    # 强制停止仍在运行的进程
    REMAINING=$(pgrep -f "realtime_scanner|full_run|scan_with_websocket|run_auto_trader" || true)
    if [ -n "$REMAINING" ]; then
        echo "   强制停止残留进程..."
        kill -9 $REMAINING || true
    fi

    echo "   ✅ 进程已停止"
else
    echo "   ✅ 无运行中的进程"
fi

# 2. 清空Python缓存
echo ""
echo "2️⃣  清空Python缓存..."

# 进入项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

# 删除__pycache__目录
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 删除.pyc文件
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 删除.pyo文件
find . -type f -name "*.pyo" -delete 2>/dev/null || true

echo "   ✅ Python缓存已清空"

# 3. 清空日志文件（可选）
echo ""
echo "3️⃣  清理日志文件..."
if [ -d "logs" ]; then
    # 备份最近的日志
    if [ -f "logs/scanner.log" ]; then
        cp logs/scanner.log logs/scanner.log.backup.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
    fi

    # 清空日志
    > logs/scanner.log 2>/dev/null || true
    echo "   ✅ 日志已清空（已备份）"
else
    mkdir -p logs
    echo "   ✅ 创建日志目录"
fi

# 4. 显示系统资源状态
echo ""
echo "4️⃣  系统资源状态..."
echo "   内存使用:"
free -h | grep Mem | awk '{print "     总计: "$2", 已用: "$3", 可用: "$7}'

echo "   磁盘使用:"
df -h /home | tail -1 | awk '{print "     总计: "$2", 已用: "$3", 可用: "$4", 使用率: "$5}'

echo ""
echo "======================================================================"
echo "✅ 清理完成！"
echo "======================================================================"
echo ""
echo "下一步: 运行部署脚本"
echo "  bash scripts/deploy_websocket_scanner.sh"
echo ""
