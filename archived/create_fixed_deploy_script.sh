#!/bin/bash
#
# CryptoSignal 部署脚本生成器（修复版 - 正确的分支名）
# 执行后会自动创建完整的部署脚本
#

echo "正在创建部署脚本（修复版）..."

# 创建部署脚本
cat > ~/vultr_deploy_complete_fixed.sh << 'DEPLOY_SCRIPT_EOF'
#!/bin/bash
set -e

# 配置区域 - 请替换为您的实际值
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"  # 替换为您的GitHub Personal Access Token
GIT_USER_NAME="YOUR_GITHUB_USERNAME"   # 替换为您的GitHub用户名
GIT_USER_EMAIL="your.email@example.com"  # 替换为您的邮箱
TARGET_BRANCH="claude/system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH"  # ✅ 修复：添加claude/前缀
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"  # 替换为您的Binance API Key
BINANCE_API_SECRET="YOUR_BINANCE_API_SECRET"  # 替换为您的Binance API Secret
BINANCE_TESTNET="false"  # 正式环境用false，测试网用true
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"  # 替换为您的Telegram Bot Token
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"  # 替换为您的Telegram Chat ID
TELEGRAM_ENABLED="true"
SERVER_IP_WHITELIST="YOUR_SERVER_IP"  # 替换为您的服务器IP（用于Binance白名单）
AUTO_RESTART_INTERVAL=2  # 自动重启间隔（小时）

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
echo -e "${CYAN}║       CryptoSignal v7.2.17 服务器自动部署系统             ║${NC}"
echo -e "${CYAN}║       修复版 - 正确的分支名                                ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
print_info "目标分支: $TARGET_BRANCH"
print_info "服务器IP白名单: $SERVER_IP_WHITELIST"
echo ""
read -p "是否继续部署？(y/N): " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && { print_warning "部署已取消"; exit 0; }

print_header "步骤 0/11: 环境检查"
command -v python3 &> /dev/null && print_success "Python版本: $(python3 --version 2>&1 | awk '{print $2}')" || { print_error "未安装Python3，正在安装..."; sudo apt-get update && sudo apt-get install -y python3 python3-pip; }
command -v pip3 &> /dev/null && print_success "pip3已安装" || { print_error "未安装pip3，正在安装..."; sudo apt-get install -y python3-pip; }
command -v git &> /dev/null && print_success "git已安装" || { print_error "未安装git，正在安装..."; sudo apt-get install -y git; }
command -v screen &> /dev/null && print_success "screen已安装" || print_warning "screen未安装，将使用nohup运行"
CURRENT_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "未知")
print_info "当前服务器IP: $CURRENT_IP"
[ "$CURRENT_IP" != "$SERVER_IP_WHITELIST" ] && [ "$CURRENT_IP" != "未知" ] && { print_warning "服务器IP与配置的白名单IP不一致"; print_warning "配置IP: $SERVER_IP_WHITELIST"; print_warning "当前IP: $CURRENT_IP"; echo ""; }

print_header "步骤 1/11: 停止旧进程"
ps aux | grep -v grep | grep "python.*cryptosignal" > /dev/null && { print_info "发现运行中的Python进程，正在停止..."; pkill -f "python.*cryptosignal" 2>/dev/null || true; sleep 2; pkill -9 -f "python.*cryptosignal" 2>/dev/null || true; print_success "Python进程已停止"; } || print_info "无运行中的Python进程"
command -v screen &> /dev/null && screen -ls 2>/dev/null | grep -q cryptosignal && { print_info "发现Screen会话，正在停止..."; screen -S cryptosignal -X quit 2>/dev/null || true; print_success "Screen会话已停止"; }

print_header "步骤 2/11: 备份旧配置"
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

print_header "步骤 3/11: 克隆仓库"
cd ~
print_info "正在克隆仓库..."
git clone https://github.com/FelixWayne0318/cryptosignal.git && print_success "仓库克隆成功" || { print_error "仓库克隆失败，请检查网络连接"; exit 1; }

print_header "步骤 4/11: 切换到目标分支"
cd ~/cryptosignal
print_info "拉取所有分支信息..."
git fetch --all
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
    print_success "分支功能包含:"
    echo "   • v7.2.17: 类型安全全面修复（40个位置）"
    echo "   • v7.2.16: Telegram类型安全修复"
    echo "   • v7.2.15: F_comparison冗余结构移除"
    echo "   • v7.2: 系统规范化重构"
else
    print_error "分支切换失败"
    print_warning "可用分支列表:"
    git branch -r | grep claude | head -10
    print_error "请检查分支名是否正确"
    exit 1
fi

print_header "步骤 5/11: 验证v7.2.17修复"
print_info "检查_get_dict函数..."
if grep -q "def _get_dict" ats_core/outputs/telegram_fmt.py; then
    print_success "_get_dict函数存在"
    GET_DICT_COUNT=$(grep -c "_get_dict(" ats_core/outputs/telegram_fmt.py || echo "0")
    print_info "_get_dict调用次数: $GET_DICT_COUNT"
    if [ "$GET_DICT_COUNT" -ge 35 ]; then
        print_success "v7.2.17修复已完整应用（预期≥35次调用）"
    else
        print_warning "调用次数少于预期，可能修复不完整"
    fi
else
    print_error "_get_dict函数不存在"
    print_error "v7.2.17修复未找到！"
    print_error "这可能导致'str' object has no attribute 'get'错误"
    echo ""
    read -p "是否继续部署？(y/N): " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && { print_warning "部署已取消"; exit 1; }
fi

print_header "步骤 6/11: 配置GitHub访问权限"
cat > ~/.cryptosignal-github.env <<EOF
GITHUB_TOKEN="$GITHUB_TOKEN"
GIT_USER_NAME="$GIT_USER_NAME"
GIT_USER_EMAIL="$GIT_USER_EMAIL"
EOF
chmod 600 ~/.cryptosignal-github.env
print_success "GitHub配置文件已创建"
print_info "位置: ~/.cryptosignal-github.env"
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
git config --global credential.helper store
echo "https://$GIT_USER_NAME:$GITHUB_TOKEN@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
print_success "Git全局配置已应用"

print_header "步骤 7/11: 配置Binance API凭证"
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
print_info "API Key: ${BINANCE_API_KEY:0:20}...${BINANCE_API_KEY: -4}"
[ "$CURRENT_IP" != "$SERVER_IP_WHITELIST" ] && [ "$CURRENT_IP" != "未知" ] && { echo ""; print_warning "IP不匹配！请在Binance添加当前IP到白名单"; print_info "访问: https://www.binance.com/en/my/settings/api-management"; print_info "添加IP: $CURRENT_IP"; }

print_header "步骤 8/11: 配置Telegram通知"
cat > ~/cryptosignal/config/telegram.json <<EOF
{
  "_comment": "Telegram Bot配置 - 自动生成于 $(date)",
  "enabled": $TELEGRAM_ENABLED,
  "bot_token": "$TELEGRAM_BOT_TOKEN",
  "chat_id": "$TELEGRAM_CHAT_ID",
  "_bot_name": "量灵通@analysis_token_bot",
  "_channel": "链上望远镜"
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json
print_success "Telegram配置已创建"

print_header "步骤 9/11: 清理Python缓存"
print_info "清理所有Python缓存..."
find ~/cryptosignal -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find ~/cryptosignal -name "*.pyc" -delete 2>/dev/null || true
print_success "Python缓存已清理"

print_header "步骤 10/11: 创建自动重启脚本"
cat > ~/cryptosignal/auto_restart.sh <<'RESTART_EOF'
#!/bin/bash
LOG_FILE="$HOME/cryptosignal/auto_restart.log"
echo "========================================" >> "$LOG_FILE"
echo "自动重启时间: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
pkill -f "python.*cryptosignal" 2>/dev/null || true
sleep 2
cd ~/cryptosignal
# 清理缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
# 拉取最新代码
git pull origin claude/system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH >> "$LOG_FILE" 2>&1
# 启动
./setup.sh >> "$LOG_FILE" 2>&1 &
echo "重启完成" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
RESTART_EOF
chmod +x ~/cryptosignal/auto_restart.sh
print_success "自动重启脚本已创建"

print_header "步骤 11/11: 配置定时任务"
crontab -l 2>/dev/null | grep -v "cryptosignal" | grep -v "auto_restart" > /tmp/crontab.tmp || true
cat >> /tmp/crontab.tmp <<EOF

# CryptoSignal 自动化任务 - $(date)
0 */${AUTO_RESTART_INTERVAL} * * * ~/cryptosignal/auto_restart.sh
0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete
0 2 * * * tail -n 100 ~/cryptosignal/auto_restart.log > ~/cryptosignal/auto_restart.log.tmp && mv ~/cryptosignal/auto_restart.log.tmp ~/cryptosignal/auto_restart.log
EOF
crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp
print_success "定时任务已配置"

print_header "验证配置完整性"
VALIDATION_ERRORS=0
echo "🔍 执行配置验证..."
echo ""
echo "1️⃣  配置文件检查:"
[ -f ~/.cryptosignal-github.env ] && print_success "GitHub配置" || { print_error "GitHub配置不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/config/binance_credentials.json ] && print_success "Binance配置" || { print_error "Binance配置不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/config/telegram.json ] && print_success "Telegram配置" || { print_error "Telegram配置不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/auto_restart.sh ] && print_success "重启脚本" || { print_error "重启脚本不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/setup.sh ] && print_success "启动脚本" || { print_error "启动脚本不存在"; ((VALIDATION_ERRORS++)); }
echo ""

echo "2️⃣  v7.2.17修复验证:"
if [ -f ~/cryptosignal/test_v7217_fix.py ]; then
    print_success "测试脚本存在"
    print_info "建议运行: cd ~/cryptosignal && python3 test_v7217_fix.py"
else
    print_warning "测试脚本不存在（可能是旧版本）"
fi
echo ""

print_header "部署完成"
[ $VALIDATION_ERRORS -eq 0 ] && { echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"; echo -e "${GREEN}║            ✅ 部署成功！所有验证通过！                 ║${NC}"; echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"; } || { echo -e "${YELLOW}╔═══════════════════════════════════════════════════════╗${NC}"; echo -e "${YELLOW}║      ⚠️  部署完成，但有验证错误，请检查上述输出        ║${NC}"; echo -e "${YELLOW}╚═══════════════════════════════════════════════════════╝${NC}"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 部署摘要"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📂 安装目录:  ~/cryptosignal"
echo "  🌿 当前分支:  $(git branch --show-current)"
echo "  📝 最新提交:  $(git log --oneline -1)"
echo "  ⏰ 定时任务:  每${AUTO_RESTART_INTERVAL}小时自动重启"
echo "  🌐 服务器IP:  $CURRENT_IP"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 下一步操作："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  运行测试验证v7.2.17修复:"
echo "    cd ~/cryptosignal && python3 test_v7217_fix.py"
echo ""
echo "2️⃣  启动系统:"
echo "    cd ~/cryptosignal && ./setup.sh"
echo ""
echo "3️⃣  查看日志:"
echo "    tail -f ~/cryptosignal/logs/*.log"
echo ""
echo "4️⃣  安全清理（可选）:"
echo "    rm ~/vultr_deploy_complete_fixed.sh"
echo ""
print_warning "重要：如果仍有'str' object has no attribute 'get'错误，"
print_warning "请运行 test_v7217_fix.py 并提供输出"
echo ""
DEPLOY_SCRIPT_EOF

chmod +x ~/vultr_deploy_complete_fixed.sh

echo ""
echo "✅ 修复版部署脚本已创建: ~/vultr_deploy_complete_fixed.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 修复内容："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ 分支名修复: 添加 claude/ 前缀"
echo "   旧: system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH"
echo "   新: claude/system-v7-refactor-cleanup-011CUzRUdHXVF1UFGJj9HaCH"
echo ""
echo "✅ 新增步骤: 验证v7.2.17修复（_get_dict函数）"
echo "✅ 新增步骤: 自动清理Python缓存"
echo "✅ 改进: 自动重启脚本包含git pull"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 在Termius中执行："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "    ~/vultr_deploy_complete_fixed.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
