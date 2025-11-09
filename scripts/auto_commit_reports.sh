#!/bin/bash
#
# 智能提交扫描报告到仓库
#
# 提交策略：
# - 有信号：立即提交推送
# - 无信号：每小时提交一次（避免频繁提交）
#
# 使用场景：扫描完成后自动调用
#
# 环境变量控制：
# - AUTO_COMMIT_REPORTS=true  : 启用自动提交（默认，服务器自动运行）
# - AUTO_COMMIT_REPORTS=false : 禁用自动提交（手动测试时使用）
#

set -e

# ==========================================
# 环境变量控制：支持手动测试时禁用自动提交
# ==========================================
AUTO_COMMIT_REPORTS=${AUTO_COMMIT_REPORTS:-true}

if [ "$AUTO_COMMIT_REPORTS" != "true" ]; then
    echo "⚠️  自动提交已禁用（AUTO_COMMIT_REPORTS=$AUTO_COMMIT_REPORTS）"
    echo "💡 如需启用：export AUTO_COMMIT_REPORTS=true"
    exit 0
fi

# 自动检测仓库目录（支持不同的部署路径）
if [ -d "/home/user/cryptosignal" ]; then
    REPO_DIR="/home/user/cryptosignal"
elif [ -d "/home/cryptosignal/cryptosignal" ]; then
    REPO_DIR="/home/cryptosignal/cryptosignal"
elif [ -d "~/cryptosignal" ]; then
    REPO_DIR="~/cryptosignal"
else
    echo "❌ 找不到cryptosignal仓库目录"
    exit 1
fi

cd "$REPO_DIR"

# 时间戳文件，记录上次提交时间
LAST_COMMIT_FILE="$REPO_DIR/.last_report_commit"

# 检查reports目录是否有变化
if ! git diff --quiet reports/ || ! git diff --cached --quiet reports/ || git ls-files --others --exclude-standard reports/ | grep -q .; then

    # 添加reports目录的所有变化
    git add reports/latest/ reports/trends.json 2>/dev/null || true

    # 检查是否有暂存的变化
    if git diff --cached --quiet; then
        echo "⚠️  没有需要提交的变化"
        exit 0
    fi

    # 读取扫描结果
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    SIGNALS=$(grep -o '"signals_found": [0-9]*' reports/latest/scan_summary.json 2>/dev/null | grep -o '[0-9]*' || echo "0")
    TOTAL=$(grep -o '"total_symbols": [0-9]*' reports/latest/scan_summary.json 2>/dev/null | grep -o '[0-9]*' || echo "N/A")

    # 判断是否需要提交
    SHOULD_COMMIT=false
    COMMIT_REASON=""

    # 策略1：有信号立即提交
    if [ "$SIGNALS" != "0" ] && [ "$SIGNALS" != "N/A" ]; then
        SHOULD_COMMIT=true
        COMMIT_REASON="发现信号"
        echo "📝 发现 $SIGNALS 个信号，立即提交..."
    else
        # 策略2：无信号时，检查距离上次提交的时间
        CURRENT_TIME=$(date +%s)

        if [ -f "$LAST_COMMIT_FILE" ]; then
            LAST_COMMIT_TIME=$(cat "$LAST_COMMIT_FILE")
            TIME_DIFF=$((CURRENT_TIME - LAST_COMMIT_TIME))

            # 60分钟 = 3600秒
            if [ $TIME_DIFF -ge 3600 ]; then
                SHOULD_COMMIT=true
                COMMIT_REASON="定期更新"
                HOURS=$((TIME_DIFF / 3600))
                echo "📝 距上次提交已过 ${HOURS}小时，定期提交..."
            else
                MINUTES=$((TIME_DIFF / 60))
                echo "⏳ 无信号，距上次提交 ${MINUTES}分钟，暂不提交（每小时提交一次）"
            fi
        else
            # 首次运行，直接提交
            SHOULD_COMMIT=true
            COMMIT_REASON="首次扫描"
            echo "📝 首次扫描报告，提交..."
        fi
    fi

    # 执行提交
    if [ "$SHOULD_COMMIT" = true ]; then
        # 生成提交消息
        if [ "$SIGNALS" != "0" ] && [ "$SIGNALS" != "N/A" ]; then
            # 有信号：详细信息
            COMMIT_MSG="scan: $TIMESTAMP - $TOTAL币种, $SIGNALS信号 ⚡

自动扫描报告（$COMMIT_REASON）
- 扫描时间: $TIMESTAMP
- 扫描币种: $TOTAL
- 发现信号: $SIGNALS ⚡
- 提交原因: $COMMIT_REASON

文件: reports/latest/scan_summary.json"
        else
            # 无信号：简洁信息
            COMMIT_MSG="scan: $TIMESTAMP - $TOTAL币种, 无信号

定期扫描报告更新（$COMMIT_REASON）"
        fi

        # 提交（不签名，静默模式）
        git commit --no-gpg-sign --quiet -m "$COMMIT_MSG"

        # 推送到远程（静默模式：成功静默，失败显示错误）
        BRANCH=$(git rev-parse --abbrev-ref HEAD)

        # 捕获错误输出
        PUSH_ERROR=$(git push --quiet origin "$BRANCH" 2>&1)
        if [ $? -eq 0 ]; then
            echo "✅ 扫描报告已推送到仓库 (${TOTAL}币种, ${SIGNALS}信号)"

            # 记录提交时间
            date +%s > "$LAST_COMMIT_FILE"
        else
            echo "❌ 推送失败: $PUSH_ERROR"
            echo "💡 本地已提交，可手动运行: git push origin $BRANCH"
            exit 1
        fi
    fi
else
    echo "✅ 没有新的扫描报告需要提交"
fi
