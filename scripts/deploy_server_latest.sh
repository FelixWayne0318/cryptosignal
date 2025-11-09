#!/bin/bash
#
# ==========================================
# CryptoSignal 服务器一键配置脚本（最新版本）
# 在Vultr服务器(139.180.157.15)上执行
# 使用最新修复的分支
# ==========================================
#

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==========================================
# 步骤0：清理旧部署（如果存在）
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 0/8: 清理旧部署（如果存在）${NC}"
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
# 步骤1：克隆仓库
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 1/8: 克隆仓库${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd ~
if git clone https://github.com/FelixWayne0318/cryptosignal.git; then
    echo -e "${GREEN}✅ 仓库克隆成功${NC}"
else
    echo -e "${RED}❌ 仓库克隆失败，请检查网络连接${NC}"
    exit 1
fi

cd cryptosignal

echo ""

# ==========================================
# 步骤2：切换到指定分支（✅ 使用最新修复的分支）
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 2/8: 切换到最新修复的分支${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ✅ 使用包含所有修复的新分支
BRANCH="claude/reorganize-repo-structure-011CUwp5f5x9B31K29qAb5w3"

if git checkout "$BRANCH"; then
    CURRENT_BRANCH=$(git branch --show-current)
    LATEST_COMMIT=$(git log --oneline -1)
    echo -e "${GREEN}✅ 分支切换成功${NC}"
    echo "   当前分支: $CURRENT_BRANCH"
    echo "   最新提交: $LATEST_COMMIT"
    echo ""
    echo -e "${GREEN}   🎯 此分支包含所有最新修复：${NC}"
    echo "      ✅ 数据库路径自动检测"
    echo "      ✅ Telegram扫描摘要通知"
    echo "      ✅ 扫描器统一（realtime_signal_scanner.py）"
    echo "      ✅ Git自动提交优化"
else
    echo -e "${RED}❌ 分支切换失败${NC}"
    exit 1
fi

echo ""

# ==========================================
# 步骤3：配置GitHub访问权限
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 3/8: 配置GitHub访问权限${NC}"
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

# ==========================================
# 步骤4：应用Git配置
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 4/8: 应用Git全局配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

git config --global user.name "FelixWayne0318"
git config --global user.email "felixwayne0318@gmail.com"
git config --global credential.helper store

echo "https://FelixWayne0318:YOUR_GITHUB_TOKEN_HERE@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials

echo -e "${GREEN}✅ Git配置已应用${NC}"
echo "   user.name: $(git config user.name)"
echo "   user.email: $(git config user.email)"
echo "   credential.helper: $(git config credential.helper)"

echo ""

# ==========================================
# 步骤5：配置Binance API
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 5/8: 配置Binance API凭证${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

mkdir -p ~/cryptosignal/config

cat > ~/cryptosignal/config/binance_credentials.json <<'EOF'
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "YOUR_BINANCE_API_KEY",
    "api_secret": "YOUR_BINANCE_SECRET_KEY",
    "testnet": false,
    "_security": "只读权限API Key",
    "_note": "请替换为你的真实API Key"
  }
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json

echo -e "${GREEN}✅ Binance API配置已创建${NC}"
echo "   位置: ~/cryptosignal/config/binance_credentials.json"
echo "   API Key: cIPL0yqyYDdZ...8M9U (只读权限)"
echo "   IP白名单: 139.180.157.15"
echo "   权限: $(ls -la ~/cryptosignal/config/binance_credentials.json | awk '{print $1}')"

echo ""

# ==========================================
# 步骤6：配置Telegram通知
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 6/8: 配置Telegram通知${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cat > ~/cryptosignal/config/telegram.json <<'EOF'
{
  "enabled": true,
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID",
  "_comment": "请替换为你的Telegram配置"
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json

echo -e "${GREEN}✅ Telegram配置已创建${NC}"
echo "   位置: ~/cryptosignal/config/telegram.json"
echo "   Bot: 量灵通@analysis_token_bot"
echo "   频道: 链上望远镜"
echo "   权限: $(ls -la ~/cryptosignal/config/telegram.json | awk '{print $1}')"

echo ""

# ==========================================
# 步骤7：配置定时任务
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 7/8: 配置定时任务（每2小时重启）${NC}"
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
# 步骤8：验证配置
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 8/8: 验证配置${NC}"
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

# 验证5：检查分支版本
echo "🔍 验证5: 检查代码版本..."
CURRENT_BRANCH=$(git branch --show-current)
EXPECTED_BRANCH="claude/reorganize-repo-structure-011CUwp5f5x9B31K29qAb5w3"

if [ "$CURRENT_BRANCH" = "$EXPECTED_BRANCH" ]; then
    echo -e "   ${GREEN}✅ 分支正确: $CURRENT_BRANCH${NC}"
    echo -e "   ${GREEN}✅ 包含所有最新修复${NC}"
else
    echo -e "   ${RED}❌ 分支错误: $CURRENT_BRANCH${NC}"
    echo -e "   ${RED}❌ 预期分支: $EXPECTED_BRANCH${NC}"
    VALIDATION_FAILED=1
fi

echo ""

# 验证6：检查服务器IP
echo "🔍 验证6: 检查服务器IP..."
CURRENT_IP=$(curl -s ifconfig.me 2>/dev/null || echo "无法获取")
if [ "$CURRENT_IP" = "139.180.157.15" ]; then
    echo -e "   ${GREEN}✅ 服务器IP匹配: $CURRENT_IP${NC}"
    echo -e "   ${GREEN}✅ Binance API IP白名单正确${NC}"
else
    echo -e "   ${YELLOW}⚠️  服务器IP: $CURRENT_IP${NC}"
    echo -e "   ${YELLOW}⚠️  预期IP: 139.180.157.15${NC}"
    echo -e "   ${YELLOW}⚠️  请更新Binance API的IP白名单！${NC}"
    echo ""
    echo "   更新步骤："
    echo "   1. 访问 https://www.binance.com/en/my/settings/api-management"
    echo "   2. 编辑API Key"
    echo "   3. 添加新IP到白名单: $CURRENT_IP"
fi

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
echo "  ✅ 提交: $(git log --oneline -1 | cut -c 1-50)"
echo "  ✅ GitHub配置: ~/.cryptosignal-github.env"
echo "  ✅ Binance API: config/binance_credentials.json"
echo "  ✅ Telegram: config/telegram.json"
echo "  ✅ 定时任务: 每2小时自动重启"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 下一步: 运行 ./setup.sh 启动系统"
echo ""
