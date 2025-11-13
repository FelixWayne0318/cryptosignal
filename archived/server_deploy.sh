#!/bin/bash
#
# ==========================================
# CryptoSignal 服务器一键配置脚本
# 用途：自动配置服务器环境、拉取代码、配置凭证
# 特性：支持指定分支或使用默认分支
# ⚠️  此文件包含敏感信息，请勿提交到Git
# ==========================================
#
# 使用方法：
#   ./server_deploy.sh              # 使用仓库默认分支
#   ./server_deploy.sh main         # 使用main分支
#   ./server_deploy.sh feature-xyz  # 使用指定分支
#

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 获取分支参数（可选）
TARGET_BRANCH="${1:-}"  # 第一个参数作为目标分支，如果未提供则为空

# ==========================================
# 步骤0：环境检查
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 0/9: 环境检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查Python版本
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✅ Python版本: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ 未安装Python3${NC}"
    exit 1
fi

# 检查pip
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✅ pip3已安装${NC}"
else
    echo -e "${RED}❌ 未安装pip3${NC}"
    exit 1
fi

# 检查git
if command -v git &> /dev/null; then
    echo -e "${GREEN}✅ git已安装${NC}"
else
    echo -e "${RED}❌ 未安装git${NC}"
    exit 1
fi

echo ""

# ==========================================
# 步骤1：清理旧部署
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 1/9: 清理旧部署${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 停止旧进程
if ps aux | grep -v grep | grep "python.*cryptosignal" > /dev/null; then
    echo "  🛑 发现运行中的Python进程，正在停止..."
    pkill -f "python.*cryptosignal" 2>/dev/null || true
    sleep 2
    pkill -9 -f "python.*cryptosignal" 2>/dev/null || true
    echo -e "${GREEN}  ✅ Python进程已停止${NC}"
fi

# 停止Screen会话
if screen -ls 2>/dev/null | grep -q cryptosignal; then
    echo "  🛑 发现Screen会话，正在停止..."
    screen -S cryptosignal -X quit 2>/dev/null || true
    echo -e "${GREEN}  ✅ Screen会话已停止${NC}"
fi

# 备份旧配置
BACKUP_DIR="$HOME/cryptosignal_backup_$(date +%Y%m%d_%H%M%S)"

if [ -f ~/cryptosignal/config/binance_credentials.json ] || \
   [ -f ~/cryptosignal/config/telegram.json ] || \
   [ -f ~/.cryptosignal-github.env ]; then
    echo "  📦 发现旧配置，正在备份..."
    mkdir -p "$BACKUP_DIR"
    cp ~/cryptosignal/config/binance_credentials.json "$BACKUP_DIR/" 2>/dev/null || true
    cp ~/cryptosignal/config/telegram.json "$BACKUP_DIR/" 2>/dev/null || true
    cp ~/.cryptosignal-github.env "$BACKUP_DIR/" 2>/dev/null || true
    echo -e "${GREEN}  ✅ 配置已备份到: $BACKUP_DIR${NC}"
fi

# 删除旧代码
if [ -d ~/cryptosignal ]; then
    echo "  🗑️  删除旧代码目录..."
    rm -rf ~/cryptosignal
    echo -e "${GREEN}  ✅ 旧代码已删除${NC}"
fi

echo ""

# ==========================================
# 步骤2：克隆仓库
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 2/9: 克隆仓库${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd ~

# 如果指定了分支，克隆特定分支；否则克隆默认分支
if [ -n "$TARGET_BRANCH" ]; then
    echo "  📥 克隆指定分支: $TARGET_BRANCH"
    if git clone -b "$TARGET_BRANCH" https://github.com/FelixWayne0318/cryptosignal.git; then
        echo -e "${GREEN}✅ 仓库克隆成功（分支: $TARGET_BRANCH）${NC}"
    else
        echo -e "${RED}❌ 分支 $TARGET_BRANCH 不存在或克隆失败${NC}"
        echo "   提示：检查分支名是否正确，或尝试不指定分支参数"
        exit 1
    fi
else
    echo "  📥 克隆默认分支"
    if git clone https://github.com/FelixWayne0318/cryptosignal.git; then
        echo -e "${GREEN}✅ 仓库克隆成功${NC}"
    else
        echo -e "${RED}❌ 仓库克隆失败，请检查网络连接${NC}"
        exit 1
    fi
fi

cd cryptosignal

echo ""

# ==========================================
# 步骤3：拉取最新代码
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 3/9: 拉取最新代码${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

CURRENT_BRANCH=$(git branch --show-current)
echo "  📍 当前分支: $CURRENT_BRANCH"
echo ""

echo "  🔄 正在拉取最新代码..."
if git pull origin "$CURRENT_BRANCH"; then
    echo -e "${GREEN}  ✅ 代码已更新到最新版本${NC}"
else
    echo -e "${YELLOW}  ⚠️  拉取失败（可能已是最新版本）${NC}"
fi

# 显示当前版本信息
LATEST_COMMIT=$(git log --oneline -1)
echo ""
echo "   📌 当前分支: $CURRENT_BRANCH"
echo "   📌 最新提交: $LATEST_COMMIT"
echo ""

# 清理Python缓存（确保新代码生效）
echo "  🧹 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}  ✅ Python缓存已清理${NC}"

echo ""

# ==========================================
# 步骤4：配置GitHub访问权限
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 4/9: 配置GitHub访问权限${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cat > ~/.cryptosignal-github.env <<'EOF'
GIT_USER_NAME="FelixWayne0318"
GIT_USER_EMAIL="felixwayne0318@gmail.com"
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
EOF
chmod 600 ~/.cryptosignal-github.env

echo -e "${GREEN}✅ GitHub配置文件已创建${NC}"
echo "   位置: ~/.cryptosignal-github.env"
echo "   权限: $(ls -la ~/.cryptosignal-github.env | awk '{print $1}')"
echo ""
echo -e "${YELLOW}⚠️  请编辑 ~/.cryptosignal-github.env 填入真实的GitHub Token${NC}"

echo ""

# ==========================================
# 步骤5：应用Git配置
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 5/9: 应用Git全局配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

git config --global user.name "FelixWayne0318"
git config --global user.email "felixwayne0318@gmail.com"
git config --global credential.helper store

# 从环境文件读取Token（如果存在）
if [ -f ~/.cryptosignal-github.env ]; then
    source ~/.cryptosignal-github.env
    if [ "$GITHUB_TOKEN" != "YOUR_GITHUB_TOKEN_HERE" ] && [ -n "$GITHUB_TOKEN" ]; then
        echo "https://FelixWayne0318:${GITHUB_TOKEN}@github.com" > ~/.git-credentials
        chmod 600 ~/.git-credentials
        echo -e "${GREEN}✅ Git凭证已配置${NC}"
    else
        echo -e "${YELLOW}⚠️  GitHub Token未配置，跳过凭证设置${NC}"
    fi
fi

echo -e "${GREEN}✅ Git配置已应用${NC}"
echo "   user.name: $(git config user.name)"
echo "   user.email: $(git config user.email)"
echo "   credential.helper: $(git config credential.helper)"

echo ""

# ==========================================
# 步骤6：配置Binance API
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 6/9: 配置Binance API凭证${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

mkdir -p ~/cryptosignal/config

cat > ~/cryptosignal/config/binance_credentials.json <<'EOF'
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "YOUR_BINANCE_API_KEY",
    "api_secret": "YOUR_BINANCE_API_SECRET",
    "testnet": false,
    "_security": "只读权限API Key",
    "_ip_whitelist": "请填写服务器IP"
  }
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json

echo -e "${GREEN}✅ Binance API配置已创建${NC}"
echo "   位置: ~/cryptosignal/config/binance_credentials.json"
echo "   权限: $(ls -la ~/cryptosignal/config/binance_credentials.json | awk '{print $1}')"
echo ""
echo -e "${YELLOW}⚠️  请编辑该文件填入真实的Binance API凭证${NC}"

echo ""

# ==========================================
# 步骤7：配置Telegram通知
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 7/9: 配置Telegram通知${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cat > ~/cryptosignal/config/telegram.json <<'EOF'
{
  "enabled": true,
  "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "chat_id": "YOUR_TELEGRAM_CHAT_ID",
  "_comment": "Telegram Bot配置"
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json

echo -e "${GREEN}✅ Telegram配置已创建${NC}"
echo "   位置: ~/cryptosignal/config/telegram.json"
echo "   权限: $(ls -la ~/cryptosignal/config/telegram.json | awk '{print $1}')"
echo ""
echo -e "${YELLOW}⚠️  请编辑该文件填入真实的Telegram Bot Token和Chat ID${NC}"

echo ""

# ==========================================
# 步骤8：配置定时任务
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 8/9: 配置定时任务（每2小时重启）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 清理旧的定时任务
crontab -l 2>/dev/null | grep -v "cryptosignal" | grep -v "auto_restart" > /tmp/crontab.tmp || true

# 添加新的定时任务
cat >> /tmp/crontab.tmp <<'EOF'

# CryptoSignal自动重启
0 */2 * * * ~/cryptosignal/auto_restart.sh
0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete
EOF

crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

echo -e "${GREEN}✅ 定时任务已配置${NC}"
echo "   • 每2小时自动重启: 0 */2 * * *"
echo "   • 每天清理旧日志: 0 1 * * *"
echo ""
echo "   当前定时任务:"
crontab -l | grep -A2 "CryptoSignal" || true

echo ""

# ==========================================
# 步骤9：验证配置
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 9/9: 验证配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

VALIDATION_FAILED=0

# 验证1：检查配置文件存在性
echo "🔍 验证1: 检查配置文件..."
if [ -f ~/.cryptosignal-github.env ]; then
    echo -e "   ${GREEN}✅ GitHub配置存在${NC}"
else
    echo -e "   ${RED}❌ GitHub配置不存在${NC}"
    VALIDATION_FAILED=1
fi

if [ -f ~/cryptosignal/config/binance_credentials.json ]; then
    echo -e "   ${GREEN}✅ Binance配置存在${NC}"
else
    echo -e "   ${RED}❌ Binance配置不存在${NC}"
    VALIDATION_FAILED=1
fi

if [ -f ~/cryptosignal/config/telegram.json ]; then
    echo -e "   ${GREEN}✅ Telegram配置存在${NC}"
else
    echo -e "   ${RED}❌ Telegram配置不存在${NC}"
    VALIDATION_FAILED=1
fi

echo ""

# 验证2：检查文件权限
echo "🔍 验证2: 检查文件权限..."
GITHUB_PERM=$(stat -c "%a" ~/.cryptosignal-github.env 2>/dev/null || echo "")
BINANCE_PERM=$(stat -c "%a" ~/cryptosignal/config/binance_credentials.json 2>/dev/null || echo "")
TELEGRAM_PERM=$(stat -c "%a" ~/cryptosignal/config/telegram.json 2>/dev/null || echo "")

if [ "$GITHUB_PERM" = "600" ]; then
    echo -e "   ${GREEN}✅ GitHub配置权限正确 (600)${NC}"
else
    echo -e "   ${YELLOW}⚠️  GitHub配置权限: $GITHUB_PERM (建议600)${NC}"
fi

if [ "$BINANCE_PERM" = "600" ]; then
    echo -e "   ${GREEN}✅ Binance配置权限正确 (600)${NC}"
else
    echo -e "   ${YELLOW}⚠️  Binance配置权限: $BINANCE_PERM (建议600)${NC}"
fi

if [ "$TELEGRAM_PERM" = "600" ]; then
    echo -e "   ${GREEN}✅ Telegram配置权限正确 (600)${NC}"
else
    echo -e "   ${YELLOW}⚠️  Telegram配置权限: $TELEGRAM_PERM (建议600)${NC}"
fi

echo ""

# 验证3：检查Git配置
echo "🔍 验证3: 检查Git配置..."
if [ "$(git config user.name)" = "FelixWayne0318" ]; then
    echo -e "   ${GREEN}✅ Git user.name配置正确${NC}"
else
    echo -e "   ${RED}❌ Git user.name配置错误${NC}"
    VALIDATION_FAILED=1
fi

if [ "$(git config user.email)" = "felixwayne0318@gmail.com" ]; then
    echo -e "   ${GREEN}✅ Git user.email配置正确${NC}"
else
    echo -e "   ${RED}❌ Git user.email配置错误${NC}"
    VALIDATION_FAILED=1
fi

echo ""

# 验证4：检查定时任务
echo "🔍 验证4: 检查定时任务..."
if crontab -l 2>/dev/null | grep -q "auto_restart.sh"; then
    echo -e "   ${GREEN}✅ 定时任务已配置${NC}"
else
    echo -e "   ${RED}❌ 定时任务未配置${NC}"
    VALIDATION_FAILED=1
fi

echo ""

# 验证5：检查代码版本
echo "🔍 验证5: 检查代码版本..."
CURRENT_BRANCH=$(git branch --show-current)
LATEST_COMMIT=$(git log --oneline -1)

echo -e "   ${GREEN}✅ 当前分支: $CURRENT_BRANCH${NC}"
echo -e "   ${GREEN}✅ 最新提交: $LATEST_COMMIT${NC}"

# 检查系统版本
if [ -f "setup.sh" ]; then
    VERSION=$(grep -m 1 "CryptoSignal v" setup.sh | grep -oP 'v[\d.]+' || echo "未知")
    echo -e "   ${GREEN}✅ 系统版本: $VERSION${NC}"
fi

echo ""

# 验证6：检查服务器IP
echo "🔍 验证6: 检查服务器IP..."
CURRENT_IP=$(curl -s ifconfig.me 2>/dev/null || echo "无法获取")
if [ "$CURRENT_IP" = "139.180.157.152" ]; then
    echo -e "   ${GREEN}✅ 服务器IP匹配: $CURRENT_IP${NC}"
    echo -e "   ${GREEN}✅ Binance API IP白名单正确${NC}"
else
    echo -e "   ${YELLOW}⚠️  服务器IP: $CURRENT_IP${NC}"
    echo -e "   ${YELLOW}⚠️  配置中的IP: 139.180.157.152${NC}"
    echo -e "   ${YELLOW}⚠️  请更新Binance API的IP白名单！${NC}"
    echo ""
    echo "   更新步骤："
    echo "   1. 访问 https://www.binance.com/en/my/settings/api-management"
    echo "   2. 编辑API Key"
    echo "   3. 添加新IP到白名单: $CURRENT_IP"
fi

echo ""

# 验证7：检查关键文件
echo "🔍 验证7: 检查关键文件..."
CRITICAL_FILES=(
    "scripts/realtime_signal_scanner.py"
    "ats_core/pipeline/analyze_symbol_v72.py"
    "ats_core/outputs/telegram_fmt.py"
    "setup.sh"
    "auto_restart.sh"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✅ $file${NC}"
    else
        echo -e "   ${RED}❌ $file 不存在${NC}"
        VALIDATION_FAILED=1
    fi
done

echo ""

# ==========================================
# 配置完成
# ==========================================
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo "=========================================="
    echo -e "${GREEN}✅ 配置完成！所有验证通过！${NC}"
    echo "=========================================="
else
    echo "=========================================="
    echo -e "${YELLOW}⚠️  配置完成，但有部分验证失败${NC}"
    echo "=========================================="
fi

echo ""
echo "📋 配置摘要:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 仓库: ~/cryptosignal"
echo "  ✅ 分支: $(git branch --show-current)"
echo "  ✅ 提交: $(git log --oneline -1 | cut -c 1-60)"
echo "  ✅ GitHub配置: ~/.cryptosignal-github.env"
echo "  ✅ Binance API: config/binance_credentials.json"
echo "  ✅ Telegram: config/telegram.json"
echo "  ✅ 定时任务: 每2小时自动重启"
echo "  ✅ 当前IP: $CURRENT_IP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}🚀 下一步: 运行 ./setup.sh 启动系统${NC}"
echo ""
echo "   cd ~/cryptosignal"
echo "   ./setup.sh"
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo "   - 首次运行setup.sh会安装Python依赖（需要3-5分钟）"
echo "   - 系统会自动检测并连接WebSocket"
echo "   - Telegram会收到启动通知"
echo "   - 扫描结果会自动推送到频道"
echo ""
echo -e "${BLUE}📌 分支切换说明：${NC}"
echo "   如需切换到其他分支，运行："
echo "   ./server_deploy.sh <分支名>"
echo ""
echo "   示例："
echo "   ./server_deploy.sh main"
echo "   ./server_deploy.sh claude/feature-xyz"
echo ""
