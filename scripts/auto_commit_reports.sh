#!/bin/bash
#
# 自动提交扫描报告到仓库
#
# 使用场景：扫描完成后自动调用，将reports/目录的变化提交并推送
#
# 安全性：
# - 只提交reports/目录的变化
# - 不提交其他文件
# - 使用--no-gpg-sign避免签名问题

set -e

REPO_DIR="/home/user/cryptosignal"
cd "$REPO_DIR"

# 检查reports目录是否有变化
if ! git diff --quiet reports/ || ! git diff --cached --quiet reports/ || git ls-files --others --exclude-standard reports/ | grep -q .; then
    echo "📝 发现扫描报告变化，准备提交..."

    # 添加reports目录的所有变化
    git add reports/latest/ reports/trends.json 2>/dev/null || true

    # 检查是否有暂存的变化
    if git diff --cached --quiet; then
        echo "⚠️  没有需要提交的变化"
        exit 0
    fi

    # 生成提交消息
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    SIGNALS=$(grep -o '"signals_found": [0-9]*' reports/latest/scan_summary.json 2>/dev/null | grep -o '[0-9]*' || echo "N/A")
    TOTAL=$(grep -o '"total_symbols": [0-9]*' reports/latest/scan_summary.json 2>/dev/null | grep -o '[0-9]*' || echo "N/A")

    COMMIT_MSG="scan: $TIMESTAMP - $TOTAL币种, $SIGNALS信号

自动扫描报告提交
- 扫描时间: $TIMESTAMP
- 扫描币种: $TOTAL
- 发现信号: $SIGNALS

文件: reports/latest/scan_summary.json"

    # 提交（不签名）
    git commit --no-gpg-sign -m "$COMMIT_MSG"

    # 推送到远程
    BRANCH=$(git rev-parse --abbrev-ref HEAD)

    echo "🚀 推送到远程仓库..."
    if git push origin "$BRANCH" 2>&1; then
        echo "✅ 扫描报告已成功推送到仓库"
        echo "📊 查看: reports/latest/scan_summary.json"
    else
        echo "❌ 推送失败（可能网络问题），但本地已提交"
        exit 1
    fi
else
    echo "✅ 没有新的扫描报告需要提交"
fi
