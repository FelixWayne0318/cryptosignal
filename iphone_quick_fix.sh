#!/bin/bash
# iPhone一键修复和重启脚本（单次粘贴）

cd ~/cryptosignal && \
echo "🔧 停止旧进程..." && \
pkill -f "python.*cryptosignal" || true && \
sleep 2 && \
echo "📥 拉取最新代码（包含data_feeds.py修复）..." && \
git fetch origin claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr && \
git reset --hard origin/claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr && \
echo "🧹 清理Python缓存..." && \
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
find . -name "*.pyc" -delete 2>/dev/null || true && \
echo "✅ 修复完成！" && \
echo "" && \
echo "现在运行诊断测试..." && \
python3 scripts/diagnose_server_v72.py
