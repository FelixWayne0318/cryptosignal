#!/bin/bash
#
# 清理旧的CryptoSignal部署
# 用途：在重新部署前清理旧数据，避免冲突
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "🧹 清理旧的CryptoSignal部署"
echo "=========================================="
echo ""

# 步骤1：停止所有运行中的进程
echo -e "${YELLOW}步骤 1/5: 停止运行中的进程${NC}"

if ps aux | grep -v grep | grep "python.*cryptosignal" > /dev/null; then
    echo "  发现运行中的Python进程，正在停止..."
    pkill -f "python.*cryptosignal" || true
    sleep 2
    pkill -9 -f "python.*cryptosignal" 2>/dev/null || true
    echo -e "${GREEN}  ✅ Python进程已停止${NC}"
else
    echo "  没有运行中的Python进程"
fi

if screen -ls 2>/dev/null | grep -q cryptosignal; then
    echo "  发现Screen会话，正在停止..."
    screen -S cryptosignal -X quit 2>/dev/null || true
    echo -e "${GREEN}  ✅ Screen会话已停止${NC}"
else
    echo "  没有运行中的Screen会话"
fi

echo ""

# 步骤2：备份旧的配置文件
echo -e "${YELLOW}步骤 2/5: 检查配置文件${NC}"

BACKUP_DIR="$HOME/cryptosignal_backup_$(date +%Y%m%d_%H%M%S)"

if [ -f ~/cryptosignal/config/binance_credentials.json ]; then
    echo "  发现Binance配置"
    mkdir -p "$BACKUP_DIR"
    cp ~/cryptosignal/config/binance_credentials.json "$BACKUP_DIR/" 2>/dev/null || true
fi

if [ -f ~/cryptosignal/config/telegram.json ]; then
    echo "  发现Telegram配置"
    mkdir -p "$BACKUP_DIR"
    cp ~/cryptosignal/config/telegram.json "$BACKUP_DIR/" 2>/dev/null || true
fi

if [ -f ~/.cryptosignal-github.env ]; then
    echo "  发现GitHub配置"
    mkdir -p "$BACKUP_DIR"
    cp ~/.cryptosignal-github.env "$BACKUP_DIR/" 2>/dev/null || true
fi

if [ -d "$BACKUP_DIR" ]; then
    echo -e "${GREEN}  ✅ 配置文件已备份到: $BACKUP_DIR${NC}"
else
    echo "  没有发现旧的配置文件"
fi

echo ""

# 步骤3：清理旧的代码目录
echo -e "${YELLOW}步骤 3/5: 清理旧的代码目录${NC}"

if [ -d ~/cryptosignal ]; then
    read -p "是否删除旧的代码目录 ~/cryptosignal？(y/N): " CONFIRM
    if [[ $CONFIRM =~ ^[Yy]$ ]]; then
        echo "  正在删除 ~/cryptosignal..."
        rm -rf ~/cryptosignal
        echo -e "${GREEN}  ✅ 旧代码已删除${NC}"
    else
        echo -e "${YELLOW}  ⚠️  保留旧代码（可能导致冲突）${NC}"
    fi
else
    echo "  没有发现旧的代码目录"
fi

echo ""

# 步骤4：清理定时任务
echo -e "${YELLOW}步骤 4/5: 检查定时任务${NC}"

if crontab -l 2>/dev/null | grep -q "cryptosignal"; then
    echo "  发现CryptoSignal定时任务"
    read -p "是否删除旧的定时任务？(y/N): " CONFIRM
    if [[ $CONFIRM =~ ^[Yy]$ ]]; then
        crontab -l 2>/dev/null | grep -v "cryptosignal" | grep -v "auto_restart" | crontab -
        echo -e "${GREEN}  ✅ 定时任务已清理${NC}"
    else
        echo -e "${YELLOW}  ⚠️  保留旧定时任务${NC}"
    fi
else
    echo "  没有发现旧的定时任务"
fi

echo ""

# 步骤5：清理日志文件
echo -e "${YELLOW}步骤 5/5: 清理旧日志文件${NC}"

if ls ~/cryptosignal*.log 2>/dev/null | head -1 > /dev/null; then
    read -p "是否删除旧的日志文件？(y/N): " CONFIRM
    if [[ $CONFIRM =~ ^[Yy]$ ]]; then
        rm -f ~/cryptosignal*.log
        echo -e "${GREEN}  ✅ 日志文件已清理${NC}"
    else
        echo -e "${YELLOW}  ⚠️  保留旧日志文件${NC}"
    fi
else
    echo "  没有发现旧的日志文件"
fi

echo ""

echo "=========================================="
echo -e "${GREEN}✅ 清理完成！${NC}"
echo "=========================================="
echo ""

if [ -d "$BACKUP_DIR" ]; then
    echo "📦 配置文件备份位置："
    echo "   $BACKUP_DIR"
    echo ""
fi

echo "🚀 下一步："
echo "   执行完整的部署命令（参考之前提供的配置）"
echo ""
