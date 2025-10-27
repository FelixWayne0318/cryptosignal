#!/bin/bash
# CryptoSignal 服务器一键部署脚本
#
# 使用方法:
#   chmod +x deploy_to_server.sh
#   ./deploy_to_server.sh

set -e  # 遇到错误立即退出

echo "======================================================================"
echo "🚀 CryptoSignal 自动交易系统 - 服务器部署"
echo "======================================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}⚠️  建议使用root用户运行此脚本${NC}"
    echo "如需继续，请输入: sudo ./deploy_to_server.sh"
    exit 1
fi

echo "======================================================================"
echo "📋 第1步: 检查系统环境"
echo "======================================================================"

# 检查操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "${GREEN}✅ 操作系统: $NAME $VERSION${NC}"
else
    echo -e "${RED}❌ 无法检测操作系统${NC}"
    exit 1
fi

# 检查Python版本
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✅ Python版本: $PYTHON_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  Python3未安装，正在安装...${NC}"
    apt update && apt install -y python3 python3-pip python3-venv
fi

# 检查git
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}⚠️  Git未安装，正在安装...${NC}"
    apt install -y git
fi

echo ""
echo "======================================================================"
echo "📥 第2步: 克隆代码仓库"
echo "======================================================================"

# 设置项目目录
PROJECT_DIR="/root/cryptosignal"

if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️  项目目录已存在，正在更新...${NC}"
    cd $PROJECT_DIR
    git fetch origin
    git checkout claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya
    git pull origin claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya
else
    echo "正在克隆仓库..."
    cd /root
    git clone https://github.com/FelixWayne0318/cryptosignal.git
    cd cryptosignal
    git checkout claude/system-repo-analysis-011CUXnjHZshGm6qPffCn8Ya
fi

echo -e "${GREEN}✅ 代码已同步到最新版本${NC}"

echo ""
echo "======================================================================"
echo "🔧 第3步: 安装Python依赖"
echo "======================================================================"

# 创建虚拟环境
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv $PROJECT_DIR/venv
fi

# 激活虚拟环境并安装依赖
source $PROJECT_DIR/venv/bin/activate
pip install --upgrade pip

# 安装核心依赖（如果没有requirements.txt）
echo "安装核心依赖..."
pip install aiohttp asyncio websockets

echo -e "${GREEN}✅ Python依赖安装完成${NC}"

echo ""
echo "======================================================================"
echo "⚙️  第4步: 配置环境变量"
echo "======================================================================"

# 创建 .env 文件
cat > $PROJECT_DIR/.env <<'EOF'
# ========== 币安API配置 ==========
BINANCE_API_KEY=fWLZHY9uzscJDEoAxUH33LU7FHiVYsjT6Yf1piSloyfSFHIM5sJBc2jVR6DKVTZi
BINANCE_API_SECRET=g6Qy00I2PLo3iBlU9oXT3vZXwCWqb5vkEWlcqByfrfgXcChe9kNEYR8lrkdutW7x

# ========== 电报Bot配置 ==========
TELEGRAM_BOT_TOKEN=7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70
TELEGRAM_CHAT_ID=-1003142003085

# ========== 交易模式 ==========
# 是否启用真实交易（false=模拟模式）
ENABLE_REAL_TRADING=false

# ========== WebSocket优化 ==========
# 是否启用WebSocket批量扫描优化（true=17倍提速）
USE_OPTIMIZED_SCAN=true

# ========== 交易配置 ==========
# 最大并发仓位数
MAX_CONCURRENT_POSITIONS=5

# 单个仓位最大USDT（默认10000）
MAX_POSITION_SIZE_USDT=10000

# 每日最大亏损USDT（默认2000）
MAX_DAILY_LOSS_USDT=2000

# 杠杆倍数（默认10x）
MAX_LEVERAGE=10

# 最小订单金额USDT（默认10）
MIN_ORDER_SIZE_USDT=10

# ========== 扫描配置 ==========
# 扫描间隔（秒）
SCAN_INTERVAL_SECONDS=300

# 最小信号分数（0-100）
MIN_SIGNAL_SCORE=75

# ========== 日志配置 ==========
LOG_LEVEL=INFO
LOG_FILE=/var/log/cryptosignal/trading.log
EOF

chmod 600 $PROJECT_DIR/.env
echo -e "${GREEN}✅ 环境变量配置完成${NC}"
echo -e "${YELLOW}⚠️  当前为模拟模式（ENABLE_REAL_TRADING=false）${NC}"

echo ""
echo "======================================================================"
echo "📁 第5步: 创建必要的目录"
echo "======================================================================"

# 创建日志目录
mkdir -p /var/log/cryptosignal
chmod 755 /var/log/cryptosignal

# 创建配置目录
mkdir -p $PROJECT_DIR/config
chmod 700 $PROJECT_DIR/config

echo -e "${GREEN}✅ 目录创建完成${NC}"

echo ""
echo "======================================================================"
echo "🔧 第6步: 设置systemd服务"
echo "======================================================================"

# 创建systemd服务文件
cat > /etc/systemd/system/cryptosignal.service <<'EOF'
[Unit]
Description=CryptoSignal Auto Trading System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/cryptosignal
Environment="PATH=/root/cryptosignal/venv/bin"
EnvironmentFile=/root/cryptosignal/.env
ExecStart=/root/cryptosignal/venv/bin/python /root/cryptosignal/scripts/run_auto_trader.py
Restart=always
RestartSec=10

# 日志
StandardOutput=append:/var/log/cryptosignal/trading.log
StandardError=append:/var/log/cryptosignal/error.log

[Install]
WantedBy=multi-user.target
EOF

# 重载systemd
systemctl daemon-reload
echo -e "${GREEN}✅ systemd服务配置完成${NC}"

echo ""
echo "======================================================================"
echo "🔒 第7步: 配置防火墙（可选）"
echo "======================================================================"

if command -v ufw &> /dev/null; then
    echo "UFW防火墙已安装，跳过配置..."
else
    echo -e "${YELLOW}是否安装并配置UFW防火墙？(y/n)${NC}"
    read -r SETUP_FIREWALL
    if [ "$SETUP_FIREWALL" = "y" ]; then
        apt install -y ufw
        ufw allow 22/tcp  # SSH
        ufw --force enable
        echo -e "${GREEN}✅ 防火墙配置完成${NC}"
    fi
fi

echo ""
echo "======================================================================"
echo "📝 第8步: 创建管理脚本"
echo "======================================================================"

# 创建备份脚本
cat > /root/backup_cryptosignal.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR

tar -czf $BACKUP_DIR/cryptosignal_$DATE.tar.gz \
    ~/cryptosignal/.env \
    ~/cryptosignal/config/ \
    /var/log/cryptosignal/

find $BACKUP_DIR -name "cryptosignal_*.tar.gz" -mtime +7 -delete
echo "Backup completed: cryptosignal_$DATE.tar.gz"
EOF

chmod +x /root/backup_cryptosignal.sh

# 创建监控脚本
cat > /root/monitor_cryptosignal.sh <<'EOF'
#!/bin/bash

if ! systemctl is-active --quiet cryptosignal; then
    echo "⚠️ CryptoSignal服务已停止！尝试重启..." | \
        curl -s -X POST "https://api.telegram.org/bot7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70/sendMessage" \
        -d "chat_id=-1003142003085" \
        -d "text=$(cat)" > /dev/null
    systemctl start cryptosignal
fi
EOF

chmod +x /root/monitor_cryptosignal.sh

# 添加到crontab
(crontab -l 2>/dev/null | grep -v "backup_cryptosignal\|monitor_cryptosignal"; \
 echo "0 2 * * * /root/backup_cryptosignal.sh"; \
 echo "*/5 * * * * /root/monitor_cryptosignal.sh") | crontab -

echo -e "${GREEN}✅ 管理脚本创建完成${NC}"

echo ""
echo "======================================================================"
echo "🧪 第9步: 测试配置"
echo "======================================================================"

# 测试电报连接
echo "测试电报Bot连接..."
TEST_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70/sendMessage" \
  -d "chat_id=-1003142003085" \
  -d "text=🧪 服务器部署测试消息")

if echo $TEST_RESPONSE | grep -q '"ok":true'; then
    echo -e "${GREEN}✅ 电报连接测试成功${NC}"
else
    echo -e "${RED}❌ 电报连接测试失败${NC}"
    echo "响应: $TEST_RESPONSE"
fi

# 测试币安API连接
echo "测试币安API连接..."
BINANCE_TEST=$(curl -s -X GET "https://fapi.binance.com/fapi/v1/ping")
if [ "$BINANCE_TEST" = "{}" ]; then
    echo -e "${GREEN}✅ 币安API连接测试成功${NC}"
else
    echo -e "${RED}❌ 币安API连接测试失败${NC}"
fi

echo ""
echo "======================================================================"
echo "✅ 部署完成！"
echo "======================================================================"
echo ""
echo -e "${GREEN}🎉 CryptoSignal 自动交易系统部署成功！${NC}"
echo ""
echo "📋 接下来的步骤:"
echo ""
echo "1️⃣  启动服务:"
echo "   systemctl start cryptosignal"
echo ""
echo "2️⃣  查看状态:"
echo "   systemctl status cryptosignal"
echo ""
echo "3️⃣  查看日志:"
echo "   journalctl -u cryptosignal -f"
echo ""
echo "4️⃣  设置开机自启:"
echo "   systemctl enable cryptosignal"
echo ""
echo "⚠️  重要提示:"
echo "   - 当前为 ${YELLOW}模拟模式${NC}，不会执行真实交易"
echo "   - 充分测试后，编辑 /root/cryptosignal/.env"
echo "   - 将 ENABLE_REAL_TRADING 改为 true 启用真实交易"
echo "   - 然后运行: systemctl restart cryptosignal"
echo ""
echo "📖 详细文档: $PROJECT_DIR/docs/SERVER_DEPLOYMENT_GUIDE.md"
echo ""
echo "======================================================================"
