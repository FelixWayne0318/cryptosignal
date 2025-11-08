#!/bin/bash
# ==========================================
# CryptoSignal 一键部署脚本
# 用途：检测环境、安装依赖、启动系统
# 特点：自动检测分支、配置存在则跳过
# ==========================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=============================================="
echo "🚀 CryptoSignal 一键部署"
echo "=============================================="
echo ""

# 检测项目目录
cd ~/cryptosignal 2>/dev/null || {
    echo -e "${RED}❌ ~/cryptosignal 目录不存在${NC}"
    echo "请先克隆仓库："
    echo "  git clone https://github.com/FelixWayne0318/cryptosignal.git"
    exit 1
}

# 自动检测当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}✅ 当前分支: $CURRENT_BRANCH${NC}"
echo ""

# 检测Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装，请先安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3: $(python3 --version 2>&1 | awk '{print $2}')${NC}"

# 检测pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip3 未安装，尝试安装...${NC}"
    sudo apt-get update && sudo apt-get install -y python3-pip || {
        echo -e "${RED}❌ pip3 安装失败${NC}"
        exit 1
    }
fi
echo -e "${GREEN}✅ pip3 已安装${NC}"

# 安装依赖（静默，快速）
echo ""
echo "📦 检查并安装依赖..."
pip3 install -r requirements.txt --quiet 2>&1 | grep -v "Requirement already satisfied" || true
echo -e "${GREEN}✅ 依赖已就绪${NC}"

# 检查配置文件
echo ""
echo "🔧 检查配置文件..."

# 检查Binance配置
if [ ! -f "config/binance_credentials.json" ]; then
    echo -e "${YELLOW}⚠️  Binance配置不存在${NC}"
    echo "请创建: config/binance_credentials.json"
    echo "参考: config/binance_credentials.json.example"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅ Binance配置存在${NC}"

# 检查Telegram配置
if [ ! -f "config/telegram.json" ]; then
    echo -e "${YELLOW}⚠️  Telegram配置不存在，创建默认配置（禁用）${NC}"
    cat > config/telegram.json <<EOF
{
  "enabled": false,
  "bot_token": "",
  "chat_id": "",
  "_comment": "Telegram通知已禁用，如需启用请参考 telegram.json.example"
}
EOF
fi
echo -e "${GREEN}✅ Telegram配置存在${NC}"

# 配置crontab（如果未配置）
echo ""
echo "⏰ 配置定时任务..."
if crontab -l 2>/dev/null | grep -q "auto_restart.sh"; then
    echo -e "${GREEN}✅ 定时任务已配置${NC}"
else
    (crontab -l 2>/dev/null; echo "0 */2 * * * ~/cryptosignal/auto_restart.sh"; echo "0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete") | crontab -
    echo -e "${GREEN}✅ 定时任务已添加（每2小时重启）${NC}"
fi

# 添加执行权限
chmod +x auto_restart.sh deploy_and_run.sh setup.sh scripts/init_databases.py 2>/dev/null || true

# 初始化数据库
echo ""
echo "🗄️  初始化数据库..."
echo "=============================================="
python3 scripts/init_databases.py || {
    echo -e "${RED}❌ 数据库初始化失败${NC}"
    echo "这不会影响系统运行，数据库会在首次使用时自动创建"
}

# 启动系统
echo ""
echo "🚀 启动系统..."
echo "=============================================="
./deploy_and_run.sh

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📊 系统状态:"
echo "  查看日志: tail -f ~/cryptosignal/logs/scanner_*.log"
echo "  重连会话: screen -r cryptosignal"
echo "  手动重启: ~/cryptosignal/auto_restart.sh"
echo ""
