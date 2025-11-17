#!/bin/bash
#
# CryptoSignal v7.4.0 方案B 部署脚本生成器（模板）
# 用途：在服务器上生成完整的部署脚本
#
# 使用说明：
#   1. 修改下面的配置变量（填入真实值）
#   2. 执行此脚本生成部署脚本
#   3. 执行生成的部署脚本
#
# v7.4.0方案B特性：
#   - 每日3am保险重启（取代2h频繁重启）
#   - 动态币种刷新（6h/次，无需重启发现新币）
#   - 保护AntiJitter 2h冷却状态
#

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  CryptoSignal v7.4.0 方案B 部署脚本生成器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  请先配置以下变量（填入真实值）："
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 配置区域 - 请修改为真实值
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"           # GitHub Personal Access Token
GIT_USER_NAME="YOUR_GITHUB_USERNAME"            # GitHub用户名
GIT_USER_EMAIL="YOUR_EMAIL@example.com"         # GitHub邮箱
TARGET_BRANCH="claude/reorganize-audit-signals-01PavGxKBtm1yUZ1iz7ADXkA"  # 目标分支
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"          # Binance API Key
BINANCE_API_SECRET="YOUR_BINANCE_API_SECRET"    # Binance API Secret
BINANCE_TESTNET="false"                          # 是否使用测试网
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"    # Telegram Bot Token
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"        # Telegram Chat ID
TELEGRAM_ENABLED="true"                          # 是否启用Telegram
SERVER_IP_WHITELIST="YOUR_SERVER_IP"            # Binance API白名单IP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 检查配置是否已修改
if [[ "$GITHUB_TOKEN" == "YOUR_GITHUB_TOKEN_HERE" ]] || \
   [[ "$BINANCE_API_KEY" == "YOUR_BINANCE_API_KEY" ]] || \
   [[ "$TELEGRAM_BOT_TOKEN" == "YOUR_TELEGRAM_BOT_TOKEN" ]]; then
    echo "❌ 错误：请先修改配置变量（填入真实值）"
    echo ""
    echo "需要修改的变量："
    echo "  - GITHUB_TOKEN"
    echo "  - GIT_USER_NAME"
    echo "  - GIT_USER_EMAIL"
    echo "  - BINANCE_API_KEY"
    echo "  - BINANCE_API_SECRET"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - TELEGRAM_CHAT_ID"
    echo "  - SERVER_IP_WHITELIST"
    echo ""
    exit 1
fi

echo "正在创建v7.4.0方案B部署脚本..."

# 创建部署脚本
cat > ~/vultr_deploy_v7.4.0_planB.sh << 'DEPLOY_SCRIPT_EOF'
#!/bin/bash
set -e

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 配置区域 - 从父脚本传入
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GITHUB_TOKEN="GITHUB_TOKEN_PLACEHOLDER"
GIT_USER_NAME="GIT_USER_NAME_PLACEHOLDER"
GIT_USER_EMAIL="GIT_USER_EMAIL_PLACEHOLDER"
TARGET_BRANCH="TARGET_BRANCH_PLACEHOLDER"
BINANCE_API_KEY="BINANCE_API_KEY_PLACEHOLDER"
BINANCE_API_SECRET="BINANCE_API_SECRET_PLACEHOLDER"
BINANCE_TESTNET="BINANCE_TESTNET_PLACEHOLDER"
TELEGRAM_BOT_TOKEN="TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TELEGRAM_CHAT_ID="TELEGRAM_CHAT_ID_PLACEHOLDER"
TELEGRAM_ENABLED="TELEGRAM_ENABLED_PLACEHOLDER"
SERVER_IP_WHITELIST="SERVER_IP_WHITELIST_PLACEHOLDER"

# v7.4.0方案B配置更新
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 取消2小时自动重启配置（已废弃）
# 原因：
#   1. 破坏AntiJitter 2h冷却状态
#   2. 与动态刷新机制冲突
#   3. 导致新币发现机制失效
#
# 新方案：
#   1. 每日3am保险重启（避免长期运行的内存泄漏）
#   2. 动态币种刷新（6h/次，无需重启）
#   3. 保护2h冷却期完整性
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() { echo ""; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo ""; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }

clear
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       CryptoSignal v7.4.0 方案B 服务器自动部署系统       ║${NC}"
echo -e "${CYAN}║       Powered by Claude AI                                ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}v7.4.0方案B特性：${NC}"
echo "  • 每日3am保险重启（取代2h频繁重启）"
echo "  • 动态币种刷新（6h/次，无需重启发现新币）"
echo "  • 保护AntiJitter 2h冷却状态"
echo ""
print_info "目标分支: $TARGET_BRANCH"
print_info "服务器IP白名单: $SERVER_IP_WHITELIST"
echo ""
read -p "是否继续部署？(y/N): " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && { print_warning "部署已取消"; exit 0; }

print_header "步骤 0/10: 环境检查"
command -v python3 &> /dev/null && print_success "Python版本: $(python3 --version 2>&1 | awk '{print $2}')" || { print_error "未安装Python3，正在安装..."; sudo apt-get update && sudo apt-get install -y python3 python3-pip; }
command -v pip3 &> /dev/null && print_success "pip3已安装" || { print_error "未安装pip3，正在安装..."; sudo apt-get install -y python3-pip; }
command -v git &> /dev/null && print_success "git已安装" || { print_error "未安装git，正在安装..."; sudo apt-get install -y git; }
command -v screen &> /dev/null && print_success "screen已安装" || print_warning "screen未安装，将使用nohup运行"
CURRENT_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "未知")
print_info "当前服务器IP: $CURRENT_IP"
[ "$CURRENT_IP" != "$SERVER_IP_WHITELIST" ] && [ "$CURRENT_IP" != "未知" ] && { print_warning "服务器IP与配置的白名单IP不一致"; print_warning "配置IP: $SERVER_IP_WHITELIST"; print_warning "当前IP: $CURRENT_IP"; echo ""; }

print_header "步骤 1/10: 停止旧进程"
ps aux | grep -v grep | grep "python.*cryptosignal" > /dev/null && { print_info "发现运行中的Python进程，正在停止..."; pkill -f "python.*cryptosignal" 2>/dev/null || true; sleep 2; pkill -9 -f "python.*cryptosignal" 2>/dev/null || true; print_success "Python进程已停止"; } || print_info "无运行中的Python进程"
command -v screen &> /dev/null && screen -ls 2>/dev/null | grep -q cryptosignal && { print_info "发现Screen会话，正在停止..."; screen -S cryptosignal -X quit 2>/dev/null || true; print_success "Screen会话已停止"; }

print_header "步骤 2/10: 备份旧配置"
BACKUP_DIR="$HOME/cryptosignal_backup_$(date +%Y%m%d_%H%M%S)"
if [ -d ~/cryptosignal ]; then
    print_info "发现旧安装，正在备份..."
    mkdir -p "$BACKUP_DIR"
    [ -d ~/cryptosignal/config ] && { cp -r ~/cryptosignal/config "$BACKUP_DIR/" 2>/dev/null || true; print_success "配置文件已备份"; }
    [ -d ~/cryptosignal/data ] && { cp -r ~/cryptosignal/data "$BACKUP_DIR/" 2>/dev/null || true; print_success "数据库已备份"; }
    [ -f ~/cryptosignal/cryptosignal.log ] && { cp ~/cryptosignal/cryptosignal.log "$BACKUP_DIR/" 2>/dev/null || true; print_success "日志已备份"; }
    print_success "备份完成: $BACKUP_DIR"
    print_info "删除旧代码..."
    rm -rf ~/cryptosignal
    print_success "旧代码已删除"
else
    print_info "未发现旧安装，跳过备份"
fi
[ -f ~/.cryptosignal-github.env ] && cp ~/.cryptosignal-github.env "$BACKUP_DIR/" 2>/dev/null || true

print_header "步骤 3/10: 克隆仓库"
cd ~
print_info "正在克隆仓库..."
git clone https://github.com/FelixWayne0318/cryptosignal.git && print_success "仓库克隆成功" || { print_error "仓库克隆失败，请检查网络连接"; exit 1; }

print_header "步骤 4/10: 切换到目标分支"
cd ~/cryptosignal
print_info "切换到分支: $TARGET_BRANCH"
if git checkout "$TARGET_BRANCH"; then
    print_success "分支切换成功"
    print_info "拉取最新代码..."
    git pull origin "$TARGET_BRANCH" && print_success "代码已更新到最新版本" || print_warning "拉取失败，使用当前版本"
    CURRENT_BRANCH=$(git branch --show-current)
    LATEST_COMMIT=$(git log --oneline -1)
    echo ""
    print_info "当前分支: $CURRENT_BRANCH"
    print_info "最新提交: $LATEST_COMMIT"
    echo ""
    print_success "v7.4.0方案B功能包含:"
    echo "   • 动态币种刷新机制（6h/次）"
    echo "   • 每日3am保险重启（替代2h频繁重启）"
    echo "   • AntiJitter 2h冷却期保护"
    echo "   • P1: 2小时多样化冷却期"
    echo "   • P2: 订单簿分析配置化"
else
    print_error "分支切换失败"
    print_warning "可用分支列表:"
    git branch -r | head -10
    exit 1
fi

print_header "步骤 5/10: 配置GitHub访问权限"
cat > ~/.cryptosignal-github.env <<EOF
GITHUB_TOKEN="$GITHUB_TOKEN"
GIT_USER_NAME="$GIT_USER_NAME"
GIT_USER_EMAIL="$GIT_USER_EMAIL"
EOF
chmod 600 ~/.cryptosignal-github.env
print_success "GitHub配置文件已创建"
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
git config --global credential.helper store
echo "https://$GIT_USER_NAME:$GITHUB_TOKEN@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
print_success "Git全局配置已应用"

print_header "步骤 6/10: 配置Binance API凭证"
mkdir -p ~/cryptosignal/config
cat > ~/cryptosignal/config/binance_credentials.json <<EOF
{
  "_comment": "Binance Futures API凭证配置 - 自动生成于 $(date)",
  "binance": {
    "api_key": "$BINANCE_API_KEY",
    "api_secret": "$BINANCE_API_SECRET",
    "testnet": $BINANCE_TESTNET,
    "_security": "只读权限API Key",
    "_ip_whitelist": "$SERVER_IP_WHITELIST",
    "_current_ip": "$CURRENT_IP"
  }
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json
print_success "Binance API配置已创建"
[ "$CURRENT_IP" != "$SERVER_IP_WHITELIST" ] && [ "$CURRENT_IP" != "未知" ] && { echo ""; print_warning "IP不匹配！请在Binance添加当前IP到白名单"; print_info "访问: https://www.binance.com/en/my/settings/api-management"; print_info "添加IP: $CURRENT_IP"; }

print_header "步骤 7/10: 配置Telegram通知"
cat > ~/cryptosignal/config/telegram.json <<EOF
{
  "_comment": "Telegram Bot配置 - 自动生成于 $(date)",
  "enabled": $TELEGRAM_ENABLED,
  "bot_token": "$TELEGRAM_BOT_TOKEN",
  "chat_id": "$TELEGRAM_CHAT_ID"
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json
print_success "Telegram配置已创建"

print_header "步骤 8/10: 验证重启脚本"
print_info "使用仓库中的auto_restart.sh（已包含v7.4.0方案B更新）"
chmod +x ~/cryptosignal/auto_restart.sh
print_success "自动重启脚本权限已设置"

print_header "步骤 9/10: 配置定时任务（v7.4.0方案B）"
crontab -l 2>/dev/null | grep -v "cryptosignal" | grep -v "auto_restart" > /tmp/crontab.tmp || true
cat >> /tmp/crontab.tmp <<'CRON_EOF'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CryptoSignal v7.4.0 方案B 自动化任务
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 每日3am保险重启（避免长期运行的内存泄漏）
0 3 * * * ~/cryptosignal/auto_restart.sh
# 日志清理（保留7天）
0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete
# 重启日志轮转
0 2 * * * tail -n 100 ~/cryptosignal/auto_restart.log > ~/cryptosignal/auto_restart.log.tmp && mv ~/cryptosignal/auto_restart.log.tmp ~/cryptosignal/auto_restart.log
CRON_EOF
crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp
print_success "定时任务已配置（v7.4.0方案B）"

print_header "步骤 10/10: 验证配置"
VALIDATION_ERRORS=0
[ -f ~/cryptosignal/config/binance_credentials.json ] && print_success "Binance配置" || { print_error "Binance配置不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/config/telegram.json ] && print_success "Telegram配置" || { print_error "Telegram配置不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/auto_restart.sh ] && print_success "重启脚本" || { print_error "重启脚本不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/setup.sh ] && print_success "启动脚本" || { print_error "启动脚本不存在"; ((VALIDATION_ERRORS++)); }
crontab -l 2>/dev/null | grep -q "0 3 \* \* \*" && print_success "每日3am重启已配置" || { print_warning "3am重启未配置"; }
crontab -l 2>/dev/null | grep -q "0 \*/2 \* \* \*" && print_error "检测到旧的2h重启配置！" || print_success "无2h重启配置（正确）"

print_header "部署完成"
[ $VALIDATION_ERRORS -eq 0 ] && print_success "✅ 部署成功！" || print_warning "⚠️  部署完成，但有验证错误"
echo ""
echo "🚀 启动系统: cd ~/cryptosignal && ./setup.sh"
echo "🗑️  删除脚本: rm ~/vultr_deploy_v7.4.0_planB.sh"
echo ""
DEPLOY_SCRIPT_EOF

# 替换占位符
sed -i "s|GITHUB_TOKEN_PLACEHOLDER|$GITHUB_TOKEN|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|GIT_USER_NAME_PLACEHOLDER|$GIT_USER_NAME|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|GIT_USER_EMAIL_PLACEHOLDER|$GIT_USER_EMAIL|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|TARGET_BRANCH_PLACEHOLDER|$TARGET_BRANCH|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|BINANCE_API_KEY_PLACEHOLDER|$BINANCE_API_KEY|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|BINANCE_API_SECRET_PLACEHOLDER|$BINANCE_API_SECRET|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|BINANCE_TESTNET_PLACEHOLDER|$BINANCE_TESTNET|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|TELEGRAM_BOT_TOKEN_PLACEHOLDER|$TELEGRAM_BOT_TOKEN|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|TELEGRAM_CHAT_ID_PLACEHOLDER|$TELEGRAM_CHAT_ID|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|TELEGRAM_ENABLED_PLACEHOLDER|$TELEGRAM_ENABLED|g" ~/vultr_deploy_v7.4.0_planB.sh
sed -i "s|SERVER_IP_WHITELIST_PLACEHOLDER|$SERVER_IP_WHITELIST|g" ~/vultr_deploy_v7.4.0_planB.sh

chmod +x ~/vultr_deploy_v7.4.0_planB.sh

echo ""
echo "✅ v7.4.0方案B部署脚本已创建: ~/vultr_deploy_v7.4.0_planB.sh"
echo ""
echo "📱 下一步："
echo "  1. 执行部署: ~/vultr_deploy_v7.4.0_planB.sh"
echo "  2. 删除脚本: rm ~/vultr_deploy_v7.4.0_planB.sh ~/deploy_server_v7.4.0_planB.template.sh"
echo ""
