#!/usr/bin/env bash
# 完整的部署和测试流程

set -euo pipefail

echo ""
echo "======================================================================"
echo "🚀 完整部署和测试流程"
echo "======================================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_DIR"

# 步骤1: 停止并清理
echo "======================================================================"
echo "步骤 1/4: 停止进程并清理缓存"
echo "======================================================================"
bash scripts/stop_and_clean.sh

echo ""
read -p "按回车继续部署..." -r

# 步骤2: 部署最新代码
echo ""
echo "======================================================================"
echo "步骤 2/4: 部署最新代码"
echo "======================================================================"
bash scripts/deploy_websocket_scanner.sh

echo ""
read -p "按回车开始测试..." -r

# 步骤3: 快速测试（20个币种）
echo ""
echo "======================================================================"
echo "步骤 3/4: 快速测试（20个币种，不发Telegram）"
echo "======================================================================"
echo ""
echo "这个测试将："
echo "  - 初始化20个币种（约30-60秒）"
echo "  - 扫描20个币种（约2-3秒）"
echo "  - 不发送Telegram消息"
echo ""
read -p "开始测试? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 scripts/realtime_signal_scanner.py --max-symbols 20 --no-telegram
    TEST_STATUS=$?

    if [ $TEST_STATUS -eq 0 ]; then
        echo ""
        echo "✅ 快速测试成功！"
    else
        echo ""
        echo "❌ 快速测试失败，错误码: $TEST_STATUS"
        exit 1
    fi
else
    echo "跳过测试"
fi

# 步骤4: 选择后续操作
echo ""
echo "======================================================================"
echo "步骤 4/4: 后续操作选择"
echo "======================================================================"
echo ""
echo "测试成功！请选择下一步操作："
echo ""
echo "  1) 运行完整测试（200个币种，不发Telegram）"
echo "  2) 启动生产扫描器（发送Telegram）"
echo "  3) 启动后台扫描器（screen）"
echo "  4) 退出"
echo ""
read -p "请选择 (1-4): " -n 1 -r
echo ""

case $REPLY in
    1)
        echo ""
        echo "🔍 运行完整测试（200个币种）..."
        echo "预计耗时: 初始化3-4分钟 + 扫描15秒"
        echo ""
        python3 scripts/realtime_signal_scanner.py --no-telegram
        ;;
    2)
        echo ""
        echo "🚀 启动生产扫描器..."
        echo "将发送Prime信号到Telegram"
        echo ""
        if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
            echo "❌ 错误: Telegram环境变量未设置"
            echo "请先设置:"
            echo "  export TELEGRAM_BOT_TOKEN='your_token'"
            echo "  export TELEGRAM_CHAT_ID='your_chat_id'"
            exit 1
        fi
        ./scripts/start_signal_scanner.sh
        ;;
    3)
        echo ""
        echo "🖥️  启动后台扫描器（screen）..."
        echo ""
        if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
            echo "❌ 错误: Telegram环境变量未设置"
            echo "请先设置:"
            echo "  export TELEGRAM_BOT_TOKEN='your_token'"
            echo "  export TELEGRAM_CHAT_ID='your_chat_id'"
            exit 1
        fi

        # 检查是否已有screen会话
        if screen -list | grep -q "signal_scanner"; then
            echo "⚠️  发现已存在的signal_scanner会话"
            read -p "是否终止旧会话? (y/n) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                screen -S signal_scanner -X quit || true
            else
                echo "退出"
                exit 0
            fi
        fi

        # 启动新的screen会话
        screen -dmS signal_scanner bash -c "cd $REPO_DIR && ./scripts/start_signal_scanner.sh"

        echo ""
        echo "✅ 后台扫描器已启动！"
        echo ""
        echo "查看运行状态:"
        echo "  screen -r signal_scanner"
        echo ""
        echo "退出screen但保持运行:"
        echo "  Ctrl+A, 然后按 D"
        echo ""
        echo "停止扫描器:"
        echo "  screen -S signal_scanner -X quit"
        echo ""
        ;;
    4)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "======================================================================"
echo "✅ 完成！"
echo "======================================================================"
echo ""
