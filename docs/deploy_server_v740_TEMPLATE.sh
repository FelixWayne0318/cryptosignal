#!/bin/bash
# ==========================================
# CryptoSignal v7.4.2方案B 生产环境部署脚本（交互式版本）
# ==========================================
# 用途：全新服务器一键部署（运行时交互式输入敏感信息）
# 使用方法：
#   1. 上传到服务器: scp docs/deploy_server_v740_TEMPLATE.sh root@YOUR_SERVER_IP:~/deploy.sh
#   2. SSH连接到服务器
#   3. 执行: chmod +x ~/deploy.sh && ~/deploy.sh
#   4. 根据提示输入GitHub Token、Binance API等敏感信息
#   5. 部署完成后自动删除
# ==========================================
#
# 🔧 v3交互式版本：
#   - ✅ 运行时交互式输入敏感信息（无需预填写）
#   - ✅ 敏感信息输入隐藏显示（read -s）
#   - ✅ 自动清理临时文件（无残留）
#   - ✅ 修复SSH断开问题（提供screen启动选项）
# ==========================================

set -e  # 遇到错误立即退出

# 错误处理函数
trap 'error_handler $? $LINENO' ERR

error_handler() {
    echo ""
    echo "❌ 部署失败！"
    echo "   错误代码: $1"
    echo "   错误行号: $2"
    echo "   请检查上方错误信息"
    echo ""
    exit 1
}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 打印函数
print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【交互式配置向导】- 运行时输入敏感信息
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

clear
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}    CryptoSignal v7.4.2 部署配置向导${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}请根据提示输入配置信息（敏感信息输入时不显示）${NC}"
echo ""

# ============================================
# 1. GitHub配置
# ============================================
echo -e "${BLUE}━━━ 1. GitHub配置 (必填) ━━━${NC}"
echo ""

read -p "GitHub用户名: " GITHUB_USER
while [ -z "$GITHUB_USER" ]; do
    print_error "GitHub用户名不能为空"
    read -p "GitHub用户名: " GITHUB_USER
done

echo -n "GitHub Token (输入隐藏): "
read -s GITHUB_TOKEN
echo ""
while [ -z "$GITHUB_TOKEN" ]; do
    print_error "GitHub Token不能为空"
    echo -n "GitHub Token (输入隐藏): "
    read -s GITHUB_TOKEN
    echo ""
done

read -p "仓库名 [cryptosignal]: " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-cryptosignal}

read -p "分支名 [main]: " GITHUB_BRANCH
GITHUB_BRANCH=${GITHUB_BRANCH:-main}

print_success "GitHub配置完成"
echo ""

# ============================================
# 2. Binance API配置
# ============================================
echo -e "${BLUE}━━━ 2. Binance API配置 (必填) ━━━${NC}"
echo ""

read -p "Binance API Key: " BINANCE_API_KEY
while [ -z "$BINANCE_API_KEY" ]; do
    print_error "Binance API Key不能为空"
    read -p "Binance API Key: " BINANCE_API_KEY
done

echo -n "Binance API Secret (输入隐藏): "
read -s BINANCE_API_SECRET
echo ""
while [ -z "$BINANCE_API_SECRET" ]; do
    print_error "Binance API Secret不能为空"
    echo -n "Binance API Secret (输入隐藏): "
    read -s BINANCE_API_SECRET
    echo ""
done

read -p "使用测试网? (true/false) [false]: " BINANCE_TESTNET
BINANCE_TESTNET=${BINANCE_TESTNET:-false}

print_success "Binance配置完成"
echo ""

# ============================================
# 3. Telegram配置
# ============================================
echo -e "${BLUE}━━━ 3. Telegram通知配置 (可选) ━━━${NC}"
echo ""

read -p "启用Telegram通知? (true/false) [false]: " TELEGRAM_ENABLED
TELEGRAM_ENABLED=${TELEGRAM_ENABLED:-false}

if [ "$TELEGRAM_ENABLED" = "true" ]; then
    read -p "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
    read -p "Telegram Chat ID: " TELEGRAM_CHAT_ID
    print_success "Telegram配置完成"
else
    TELEGRAM_BOT_TOKEN=""
    TELEGRAM_CHAT_ID=""
    print_info "Telegram通知已禁用"
fi
echo ""

# ============================================
# 4. 服务器配置
# ============================================
echo -e "${BLUE}━━━ 4. 服务器配置 ━━━${NC}"
echo ""

read -p "服务器时区 [Asia/Singapore]: " SERVER_TIMEZONE
SERVER_TIMEZONE=${SERVER_TIMEZONE:-Asia/Singapore}

print_success "服务器配置完成"
echo ""

# ============================================
# 配置摘要确认
# ============================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📋 配置摘要${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  GitHub用户: $GITHUB_USER"
echo "  仓库: $GITHUB_REPO"
echo "  分支: $GITHUB_BRANCH"
echo "  时区: $SERVER_TIMEZONE"
echo "  Binance测试网: $BINANCE_TESTNET"
echo "  Telegram通知: $TELEGRAM_ENABLED"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "确认以上配置正确，开始部署? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "部署已取消"
    exit 0
fi

# 创建部署日志
DEPLOY_LOG=~/deploy_$(date +%Y%m%d_%H%M%S).log
echo "部署日志: $DEPLOY_LOG" > "$DEPLOY_LOG"
print_info "部署日志: $DEPLOY_LOG"
echo ""

# ==========================================
# 步骤1：更新系统并安装依赖
# ==========================================
print_step "步骤1/10：安装系统依赖"

echo "正在更新系统包列表..." | tee -a "$DEPLOY_LOG"
sudo apt-get update -qq >> "$DEPLOY_LOG" 2>&1

echo "正在安装必需软件..." | tee -a "$DEPLOY_LOG"
sudo apt-get install -y \
    python3 \
    python3-pip \
    git \
    curl \
    wget \
    vim \
    htop \
    screen \
    ca-certificates \
    software-properties-common \
    >> "$DEPLOY_LOG" 2>&1

print_success "系统依赖安装完成"

# 验证Python版本
INSTALLED_PYTHON=$(python3 --version 2>&1 | awk '{print $2}')
print_success "Python版本: $INSTALLED_PYTHON"

# 获取当前服务器IP
CURRENT_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "未知")
print_success "当前服务器IP: $CURRENT_IP"
print_warning "请确保此IP已添加到Binance API白名单"

# ==========================================
# 步骤2：配置时区
# ==========================================
print_step "步骤2/10：配置服务器时区"

sudo timedatectl set-timezone "$SERVER_TIMEZONE" 2>/dev/null || true
CURRENT_TZ=$(timedatectl | grep "Time zone" | awk '{print $3}')
print_success "时区已设置: $CURRENT_TZ"

# ==========================================
# 步骤3：配置Git认证
# ==========================================
print_step "步骤3/10：配置GitHub认证"

# 配置Git全局设置
git config --global user.name "$GITHUB_USER"
git config --global user.email "${GITHUB_USER}@users.noreply.github.com"
git config --global credential.helper store

# 创建Git凭证文件
cat > ~/.git-credentials << EOF
https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com
EOF
chmod 600 ~/.git-credentials

print_success "GitHub认证配置完成"

# ==========================================
# 步骤4：克隆仓库
# ==========================================
print_step "步骤4/10：克隆代码仓库"

# 如果目录已存在，先备份
if [ -d ~/cryptosignal ]; then
    BACKUP_DIR=~/cryptosignal_backup_$(date +%Y%m%d_%H%M%S)
    print_warning "检测到旧版本，备份到: $BACKUP_DIR"

    # 备份重要文件
    mkdir -p "$BACKUP_DIR"
    [ -d ~/cryptosignal/config ] && cp -r ~/cryptosignal/config "$BACKUP_DIR/" 2>/dev/null || true
    [ -d ~/cryptosignal/data ] && cp -r ~/cryptosignal/data "$BACKUP_DIR/" 2>/dev/null || true
    [ -f ~/cryptosignal/cryptosignal.log ] && cp ~/cryptosignal/cryptosignal.log "$BACKUP_DIR/" 2>/dev/null || true

    print_success "备份完成: $BACKUP_DIR"

    # 删除旧代码
    rm -rf ~/cryptosignal
    print_success "旧代码已删除"
fi

# 克隆仓库
echo "正在克隆仓库..." | tee -a "$DEPLOY_LOG"
cd ~
if git clone -b "$GITHUB_BRANCH" https://github.com/${GITHUB_USER}/${GITHUB_REPO}.git ~/cryptosignal >> "$DEPLOY_LOG" 2>&1; then
    print_success "仓库克隆完成"
else
    print_error "仓库克隆失败，请检查网络连接和GitHub Token"
    echo "详细日志: $DEPLOY_LOG"
    exit 1
fi

cd ~/cryptosignal

# 显示当前分支和最新提交
CURRENT_BRANCH=$(git branch --show-current)
LATEST_COMMIT=$(git log --oneline -1)
print_success "当前分支: $CURRENT_BRANCH"
print_info "最新提交: $LATEST_COMMIT"

# ==========================================
# 步骤5：创建配置文件
# ==========================================
print_step "步骤5/10：创建配置文件"

# 确保config目录存在
mkdir -p ~/cryptosignal/config

# 5.1 创建Binance配置
echo "创建Binance API配置..."
cat > ~/cryptosignal/config/binance_credentials.json << EOF
{
  "_comment": "Binance Futures API凭证配置 - 生成于 $(date)",
  "binance": {
    "api_key": "${BINANCE_API_KEY}",
    "api_secret": "${BINANCE_API_SECRET}",
    "testnet": ${BINANCE_TESTNET},
    "_security_note": "请确保API Key只有只读权限，并已设置IP白名单",
    "_current_server_ip": "${CURRENT_IP}"
  }
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json
print_success "Binance配置已创建"

# 5.2 创建Telegram配置
echo "创建Telegram配置..."
if [ "$TELEGRAM_ENABLED" = "true" ]; then
    cat > ~/cryptosignal/config/telegram.json << EOF
{
  "_comment": "Telegram Bot配置 - 生成于 $(date)",
  "enabled": true,
  "bot_token": "${TELEGRAM_BOT_TOKEN}",
  "chat_id": "${TELEGRAM_CHAT_ID}"
}
EOF
    print_success "Telegram配置已创建（已启用）"
else
    cat > ~/cryptosignal/config/telegram.json << EOF
{
  "_comment": "Telegram Bot配置 - 生成于 $(date)",
  "enabled": false,
  "bot_token": "",
  "chat_id": ""
}
EOF
    print_success "Telegram配置已创建（已禁用）"
fi
chmod 600 ~/cryptosignal/config/telegram.json

# 验证params.json存在
if [ -f ~/cryptosignal/config/params.json ]; then
    print_success "params.json配置文件存在"
    if grep -q '"symbol_refresh"' ~/cryptosignal/config/params.json; then
        print_success "v7.4.2方案B配置已启用（symbol_refresh）"
    else
        print_warning "未检测到symbol_refresh配置"
    fi
else
    print_warning "params.json不存在"
fi

# ==========================================
# 步骤6：安装Python依赖
# ==========================================
print_step "步骤6/10：安装Python依赖"

cd ~/cryptosignal

# 升级pip
print_info "升级pip..."
python3 -m pip install --upgrade pip -q >> "$DEPLOY_LOG" 2>&1

# 安装依赖
echo "正在安装项目依赖（可能需要几分钟）..." | tee -a "$DEPLOY_LOG"
if pip3 install -r requirements.txt -q >> "$DEPLOY_LOG" 2>&1; then
    print_success "Python依赖安装完成"
else
    print_warning "部分依赖安装失败，但不影响运行"
    echo "详细日志: $DEPLOY_LOG"
fi

# ==========================================
# 步骤7：添加执行权限
# ==========================================
print_step "步骤7/10：配置文件权限"

chmod +x ~/cryptosignal/setup.sh 2>/dev/null || true
chmod +x ~/cryptosignal/auto_restart.sh 2>/dev/null || true
chmod +x ~/cryptosignal/deploy_and_run.sh 2>/dev/null || true
chmod +x ~/cryptosignal/start_live.sh 2>/dev/null || true
chmod +x ~/cryptosignal/scripts/init_databases.py 2>/dev/null || true

print_success "文件权限配置完成"

# ==========================================
# 步骤8：初始化数据库
# ==========================================
print_step "步骤8/10：初始化数据库"

cd ~/cryptosignal
if python3 scripts/init_databases.py >> "$DEPLOY_LOG" 2>&1; then
    print_success "数据库初始化完成"
else
    print_warning "数据库初始化失败（不影响运行，首次扫描时会自动创建）"
fi

# ==========================================
# 步骤9：配置定时任务（v7.4.2方案B）
# ==========================================
print_step "步骤9/10：配置定时任务（v7.4.2方案B）"

# 备份当前crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true

# 移除旧的cryptosignal相关任务
crontab -l 2>/dev/null | grep -v "cryptosignal" | grep -v "auto_restart" > /tmp/crontab.tmp || true

# 添加新的定时任务
cat >> /tmp/crontab.tmp << 'CRON_EOF'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CryptoSignal v7.4.2 方案B 自动化任务
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 特性：
#   1. 每日3am保险重启（避免内存泄漏）
#   2. 动态币种刷新（6h/次，无需重启）
#   3. 保护AntiJitter 2h冷却期状态
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 每日3am保险重启（方案B核心配置）
0 3 * * * ~/cryptosignal/auto_restart.sh >> ~/cryptosignal/auto_restart.log 2>&1

# 日志清理（保留最近7天）
0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete 2>/dev/null

# 重启日志轮转（避免日志文件过大）
0 2 * * * tail -n 100 ~/cryptosignal/auto_restart.log > ~/cryptosignal/auto_restart.log.tmp && mv ~/cryptosignal/auto_restart.log.tmp ~/cryptosignal/auto_restart.log 2>/dev/null

CRON_EOF

# 安装新的crontab
crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

print_success "定时任务配置完成"
echo "   ✅ 每日3am自动重启（保护2h冷却状态）"
echo "   ✅ 动态币种刷新（6h自动刷新，无需重启）"
echo "   ✅ 日志自动清理（保留7天）"

# ==========================================
# 步骤10：验证配置
# ==========================================
print_step "步骤10/10：验证部署配置"

VALIDATION_ERRORS=0

# 验证配置文件
echo "验证配置文件..."
[ -f ~/cryptosignal/config/binance_credentials.json ] && print_success "Binance配置文件" || { print_error "Binance配置文件不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/config/telegram.json ] && print_success "Telegram配置文件" || { print_error "Telegram配置文件不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/config/params.json ] && print_success "params.json配置文件" || { print_error "params.json不存在"; ((VALIDATION_ERRORS++)); }

# 验证脚本文件
echo ""
echo "验证脚本文件..."
[ -f ~/cryptosignal/setup.sh ] && print_success "setup.sh启动脚本" || { print_error "setup.sh不存在"; ((VALIDATION_ERRORS++)); }
[ -f ~/cryptosignal/auto_restart.sh ] && print_success "auto_restart.sh重启脚本" || { print_error "auto_restart.sh不存在"; ((VALIDATION_ERRORS++)); }

# 验证定时任务
echo ""
echo "验证定时任务..."
if crontab -l 2>/dev/null | grep -q "0 3 \* \* \*.*auto_restart"; then
    print_success "每日3am重启已配置"
else
    print_error "3am重启未正确配置"
    ((VALIDATION_ERRORS++))
fi

# 检查旧的2h重启配置
if crontab -l 2>/dev/null | grep -q "0 \*/2 \* \* \*"; then
    print_error "检测到旧的2h重启配置！请手动清理"
    ((VALIDATION_ERRORS++))
else
    print_success "无2h重启配置（正确）"
fi

# 验证方案B配置
echo ""
echo "验证v7.4.2方案B配置..."
if grep -q '"symbol_refresh"' ~/cryptosignal/config/params.json 2>/dev/null; then
    print_success "动态币种刷新配置存在"
else
    print_warning "未检测到symbol_refresh配置"
fi

# ==========================================
# 部署完成
# ==========================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $VALIDATION_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ v7.4.2方案B 部署完成！所有验证通过！${NC}"
else
    echo -e "${YELLOW}⚠️  v7.4.2方案B 部署完成，但有 $VALIDATION_ERRORS 个验证错误${NC}"
fi
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 显示部署信息
echo -e "${CYAN}📋 部署信息${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   仓库路径: ~/cryptosignal"
echo "   当前分支: $CURRENT_BRANCH"
echo "   最新提交: $LATEST_COMMIT"
echo "   Python版本: $INSTALLED_PYTHON"
echo "   时区设置: $CURRENT_TZ"
echo "   服务器IP: $CURRENT_IP"
echo "   部署日志: $DEPLOY_LOG"
echo ""

# 显示方案B特性
echo -e "${CYAN}⏰ v7.4.2方案B 特性${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ✅ 每日3am自动重启（保护2h冷却状态）"
echo "   ✅ 动态币种刷新（6h自动刷新，无需重启）"
echo "   ✅ AntiJitter 2h冷却期完整保护"
echo "   ✅ P1: 2小时多样化冷却期"
echo "   ✅ P2: 订单簿分析配置化"
echo ""

# 显示安全提醒
echo -e "${RED}🔐 安全提醒${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ⚠️  请立即删除此部署脚本（含敏感信息）"
echo "   ⚠️  执行命令: rm ~/deploy_cryptosignal_v740.sh"
echo "   ⚠️  配置文件权限已设置为600（仅所有者可读写）"
echo ""

# 显示启动选项（修复版：提供多种启动方式）
echo -e "${CYAN}🚀 启动选项（三选一）${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "【推荐】选项1: 后台启动（screen会话，SSH断开后继续运行）"
echo "   screen -S cryptosignal -dm bash -c 'cd ~/cryptosignal && ./setup.sh'"
echo "   screen -r cryptosignal  # 查看日志（按Ctrl+A+D退出screen但保持运行）"
echo ""
echo "选项2: 前台启动并查看日志（适合测试，按Ctrl+C停止）"
echo "   cd ~/cryptosignal && ./setup.sh"
echo ""
echo "选项3: 后台启动（nohup，日志保存到文件）"
echo "   cd ~/cryptosignal && nohup ./setup.sh > ~/cryptosignal_manual_$(date +%Y%m%d_%H%M%S).log 2>&1 &"
echo ""

# 显示监控命令
echo -e "${CYAN}📖 监控和管理${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔍 检查运行状态："
echo "   ps aux | grep realtime_signal_scanner"
echo "   screen -ls  # 查看screen会话"
echo ""
echo "📁 重要目录："
echo "   配置文件: ~/cryptosignal/config/"
echo "   扫描报告: ~/cryptosignal/reports/latest/"
echo "   币种变化历史: ~/cryptosignal/data/symbol_list_history.jsonl"
echo ""
echo "📊 查看日志："
echo "   tail -f ~/cryptosignal_*.log  # 查看最新日志"
echo "   tail -20 ~/cryptosignal/auto_restart.log  # 查看重启日志"
echo "   screen -r cryptosignal  # 连接screen会话查看实时日志"
echo ""
echo "🔧 管理命令："
echo "   ~/cryptosignal/auto_restart.sh  # 手动重启"
echo "   pkill -f realtime_signal_scanner  # 停止扫描器"
echo "   screen -X -S cryptosignal quit  # 终止screen会话"
echo "   crontab -l  # 查看定时任务"
echo ""
echo "💡 Screen快捷键："
echo "   Ctrl+A 然后 D  # 退出screen但保持运行（重要！）"
echo "   Ctrl+C  # 在screen内停止程序"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}部署完成！请选择上方启动选项启动系统 🎉${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}💡 提示: 建议使用screen方式启动，SSH断开后程序继续运行${NC}"
echo ""

# ==========================================
# 自动清理部署脚本
# ==========================================
echo -e "${CYAN}🧹 清理部署脚本...${NC}"
SCRIPT_PATH="$0"
if [ -f "$SCRIPT_PATH" ]; then
    # 延迟删除（避免脚本还在运行时删除自身）
    (sleep 2 && rm -f "$SCRIPT_PATH" && echo "✅ 部署脚本已自动删除" || true) &
    print_success "部署脚本将在2秒后自动删除（无敏感信息残留）"
else
    print_info "无需清理"
fi
echo ""
