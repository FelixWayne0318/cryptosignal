#!/bin/bash
# Telegram配置脚本

echo "======================================"
echo "Telegram Bot 配置向导"
echo "======================================"
echo ""

# 检查现有配置
if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "✅ TELEGRAM_BOT_TOKEN 已设置: ${TELEGRAM_BOT_TOKEN:0:10}..."
else
    echo "❌ TELEGRAM_BOT_TOKEN 未设置"
fi

if [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    echo "✅ TELEGRAM_CHAT_ID 已设置: $TELEGRAM_CHAT_ID"
else
    echo "❌ TELEGRAM_CHAT_ID 未设置"
fi

echo ""
echo "======================================"
echo "配置方法："
echo "======================================"
echo ""
echo "方法1：临时设置（仅当前会话有效）"
echo "  export TELEGRAM_BOT_TOKEN=\"你的Bot Token\""
echo "  export TELEGRAM_CHAT_ID=\"你的群组ID\""
echo ""
echo "方法2：永久设置（推荐）"
echo "  编辑 ~/.bashrc 或 ~/.profile 添加："
echo "  echo 'export TELEGRAM_BOT_TOKEN=\"你的Token\"' >> ~/.bashrc"
echo "  echo 'export TELEGRAM_CHAT_ID=\"你的群组ID\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
echo ""
echo "方法3：使用.env文件（本脚本支持）"
echo "  创建 ~/cryptosignal/.env 文件"
echo ""
echo "======================================"
echo "如何获取Bot Token和Chat ID："
echo "======================================"
echo ""
echo "1. 获取Bot Token："
echo "   - 在Telegram中找 @BotFather"
echo "   - 发送 /newbot 创建机器人"
echo "   - 或发送 /mybots 查看已有机器人"
echo "   - 获取类似：123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
echo ""
echo "2. 获取Chat ID："
echo "   - 将Bot添加到你的群组"
echo "   - 在群组发送任意消息"
echo "   - 访问：https://api.telegram.org/bot<你的Token>/getUpdates"
echo "   - 找到 \"chat\":{\"id\":-1001234567890} 中的ID"
echo ""
echo "======================================"
echo ""

# 交互式配置
read -p "是否现在配置？(y/n): " answer

if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    echo ""
    read -p "请输入 Bot Token: " token
    read -p "请输入 Chat ID: " chatid

    # 写入.env文件
    ENV_FILE="$HOME/cryptosignal/.env"
    echo "# Telegram配置" > "$ENV_FILE"
    echo "export TELEGRAM_BOT_TOKEN=\"$token\"" >> "$ENV_FILE"
    echo "export TELEGRAM_CHAT_ID=\"$chatid\"" >> "$ENV_FILE"

    echo ""
    echo "✅ 配置已保存到: $ENV_FILE"
    echo ""
    echo "使用方法："
    echo "  source $ENV_FILE"
    echo "  python3 tools/manual_run.py --send --top 10"
    echo ""
    echo "或者添加到 ~/.bashrc 使其永久生效："
    echo "  echo 'source $ENV_FILE' >> ~/.bashrc"
    echo "  source ~/.bashrc"
    echo ""
else
    echo "跳过配置"
fi
