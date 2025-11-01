#!/bin/bash
# CryptoSignal Screen会话运行脚本（推荐方式）

echo "========================================"
echo "🖥️  CryptoSignal Screen会话模式"
echo "========================================"
echo ""

# 检查screen是否安装
if ! command -v screen &> /dev/null; then
    echo "❌ Screen未安装"
    echo ""
    echo "安装命令："
    echo "  Ubuntu/Debian: sudo apt-get install screen"
    echo "  CentOS/RHEL: sudo yum install screen"
    exit 1
fi

# 检查是否已有会话
SESSION_NAME="cryptosignal"
EXISTING=$(screen -ls | grep "$SESSION_NAME" | wc -l)

if [ "$EXISTING" -gt 0 ]; then
    echo "✅ 找到现有Screen会话"
    echo ""
    screen -ls | grep "$SESSION_NAME"
    echo ""
    echo "选择操作："
    echo "  1) 重新连接到现有会话（推荐）"
    echo "  2) 终止现有会话并创建新会话"
    echo "  3) 退出"
    echo ""
    read -p "请选择 (1/2/3): " CHOICE

    case $CHOICE in
        1)
            echo "正在连接到会话..."
            screen -r "$SESSION_NAME"
            exit 0
            ;;
        2)
            echo "正在终止现有会话..."
            screen -S "$SESSION_NAME" -X quit 2>/dev/null
            sleep 1
            ;;
        *)
            echo "退出"
            exit 0
            ;;
    esac
fi

# 切换到项目目录
cd /home/user/cryptosignal

# 拉取最新代码
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 拉取最新代码"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CURRENT_BRANCH=$(git branch --show-current)
git pull origin "$CURRENT_BRANCH"
echo "✅ 代码已更新"
echo ""

# 创建启动脚本
STARTUP_SCRIPT="/tmp/cryptosignal_startup.sh"
cat > "$STARTUP_SCRIPT" <<'EOF'
#!/bin/bash
cd /home/user/cryptosignal
echo "========================================"
echo "🚀 CryptoSignal v6.0 (Screen会话模式)"
echo "========================================"
echo ""
echo "✅ Screen会话已启动"
echo ""
echo "💡 快捷操作："
echo "   • 分离会话（保持运行）: Ctrl+A, 然后按 D"
echo "   • 重新连接: screen -r cryptosignal"
echo "   • 停止系统: Ctrl+C"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 启动扫描器
python3 scripts/realtime_signal_scanner.py --interval 300 --min-score 70

# 如果程序退出，等待按键
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "程序已退出"
echo "按任意键关闭会话..."
read -n 1
EOF

chmod +x "$STARTUP_SCRIPT"

# 启动screen会话
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 创建Screen会话"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "会话名称: $SESSION_NAME"
echo ""
echo "分离会话快捷键: Ctrl+A, 然后按 D"
echo "重新连接命令: screen -r $SESSION_NAME"
echo ""
echo "按Enter键启动..."
read

# 启动screen会话
screen -S "$SESSION_NAME" "$STARTUP_SCRIPT"
