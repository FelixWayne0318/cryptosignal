#!/bin/bash
# ==========================================
# CryptoSignal v7.4.0 本地部署启动器
# ==========================================
# 用途：从本地一键部署到服务器，自动填充配置
# 运行位置：本地电脑（Mac/Linux）
# ==========================================
#
# 🎯 工作流程：
#   1. 读取本地配置文件（deploy.config）
#   2. 替换模板中的占位符
#   3. 上传到服务器并执行
#   4. 清理服务器上的临时文件
#
# 使用方法：
#   1. 复制 deploy.config.example 为 deploy.config
#   2. 编辑 deploy.config 填写真实信息
#   3. 执行: ./deploy_launcher.sh
# ==========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 打印函数
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
print_step() { echo -e "\n${BLUE}━━━ $1 ━━━${NC}\n"; }

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/deploy.config"
TEMPLATE_FILE="$SCRIPT_DIR/docs/deploy_server_v740_TEMPLATE.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "    CryptoSignal v7.4.0 本地部署启动器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ==========================================
# 步骤1: 检查配置文件
# ==========================================
print_step "步骤1/5：检查配置文件"

if [ ! -f "$CONFIG_FILE" ]; then
    print_error "配置文件不存在: $CONFIG_FILE"
    echo ""
    print_info "请先创建配置文件："
    echo "   1. cp deploy.config.example deploy.config"
    echo "   2. vim deploy.config  # 填写真实配置"
    echo "   3. ./deploy_launcher.sh"
    echo ""
    exit 1
fi

print_success "配置文件已找到: $CONFIG_FILE"

# 加载配置
source "$CONFIG_FILE"

# 验证必填配置
ERRORS=0
[ -z "$GITHUB_TOKEN" ] && { print_error "GITHUB_TOKEN未配置"; ((ERRORS++)); }
[ -z "$BINANCE_API_KEY" ] && { print_error "BINANCE_API_KEY未配置"; ((ERRORS++)); }
[ -z "$BINANCE_API_SECRET" ] && { print_error "BINANCE_API_SECRET未配置"; ((ERRORS++)); }
[ -z "$SERVER_IP" ] || [ "$SERVER_IP" = "YOUR_SERVER_IP_HERE" ] && { print_error "SERVER_IP未配置"; ((ERRORS++)); }

if [ $ERRORS -gt 0 ]; then
    print_error "配置验证失败，请检查 deploy.config"
    exit 1
fi

print_success "配置验证通过"

# 显示配置概览
echo ""
print_info "配置概览："
echo "   GitHub用户: $GITHUB_USER"
echo "   目标分支: $GITHUB_BRANCH"
echo "   服务器: $SERVER_USER@$SERVER_IP:$SERVER_PORT"
echo "   时区: $SERVER_TIMEZONE"
echo "   Telegram: $TELEGRAM_ENABLED"
echo ""

# ==========================================
# 步骤2: 检查模板文件
# ==========================================
print_step "步骤2/5：检查模板文件"

if [ ! -f "$TEMPLATE_FILE" ]; then
    print_error "模板文件不存在: $TEMPLATE_FILE"
    print_info "请确保您在CryptoSignal项目根目录下运行此脚本"
    exit 1
fi

print_success "模板文件已找到"

# ==========================================
# 步骤3: 生成部署脚本
# ==========================================
print_step "步骤3/5：生成部署脚本"

# 创建临时部署脚本
DEPLOY_SCRIPT="/tmp/cryptosignal_deploy_$(date +%s).sh"

# 读取模板并替换占位符
cp "$TEMPLATE_FILE" "$DEPLOY_SCRIPT"

# 使用sed替换配置
sed -i.bak \
    -e "s|GITHUB_TOKEN=\"YOUR_GITHUB_TOKEN_HERE\"|GITHUB_TOKEN=\"$GITHUB_TOKEN\"|g" \
    -e "s|GITHUB_USER=\"YOUR_GITHUB_USERNAME\"|GITHUB_USER=\"$GITHUB_USER\"|g" \
    -e "s|GITHUB_REPO=\"cryptosignal\"|GITHUB_REPO=\"$GITHUB_REPO\"|g" \
    -e "s|GITHUB_BRANCH=\"main\"|GITHUB_BRANCH=\"$GITHUB_BRANCH\"|g" \
    -e "s|BINANCE_API_KEY=\"YOUR_BINANCE_API_KEY_HERE\"|BINANCE_API_KEY=\"$BINANCE_API_KEY\"|g" \
    -e "s|BINANCE_API_SECRET=\"YOUR_BINANCE_API_SECRET_HERE\"|BINANCE_API_SECRET=\"$BINANCE_API_SECRET\"|g" \
    -e "s|BINANCE_TESTNET=\"false\"|BINANCE_TESTNET=\"$BINANCE_TESTNET\"|g" \
    -e "s|TELEGRAM_ENABLED=\"false\"|TELEGRAM_ENABLED=\"$TELEGRAM_ENABLED\"|g" \
    -e "s|TELEGRAM_BOT_TOKEN=\"\"|TELEGRAM_BOT_TOKEN=\"$TELEGRAM_BOT_TOKEN\"|g" \
    -e "s|TELEGRAM_CHAT_ID=\"\"|TELEGRAM_CHAT_ID=\"$TELEGRAM_CHAT_ID\"|g" \
    -e "s|SERVER_TIMEZONE=\"Asia/Singapore\"|SERVER_TIMEZONE=\"$SERVER_TIMEZONE\"|g" \
    -e "s|PYTHON_VERSION=\"3.10\"|PYTHON_VERSION=\"$PYTHON_VERSION\"|g" \
    "$DEPLOY_SCRIPT"

# 删除备份文件
rm -f "${DEPLOY_SCRIPT}.bak"

print_success "部署脚本已生成: $DEPLOY_SCRIPT"

# ==========================================
# 步骤4: 上传并执行
# ==========================================
print_step "步骤4/5：上传并执行部署"

# 确认执行
read -p "确认开始部署？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "部署已取消"
    rm -f "$DEPLOY_SCRIPT"
    exit 0
fi

# 上传脚本到服务器
print_info "上传部署脚本到服务器..."
if scp -P "$SERVER_PORT" "$DEPLOY_SCRIPT" "$SERVER_USER@$SERVER_IP:~/deploy_cryptosignal_v740.sh"; then
    print_success "上传成功"
else
    print_error "上传失败，请检查SSH连接"
    rm -f "$DEPLOY_SCRIPT"
    exit 1
fi

# 执行部署
print_info "开始远程部署..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_IP" "chmod +x ~/deploy_cryptosignal_v740.sh && ~/deploy_cryptosignal_v740.sh"

SSH_EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $SSH_EXIT_CODE -eq 0 ]; then
    print_success "部署完成"
else
    print_error "部署失败（退出代码: $SSH_EXIT_CODE）"
fi

# ==========================================
# 步骤5: 清理临时文件
# ==========================================
print_step "步骤5/5：清理临时文件"

# 删除本地临时文件
rm -f "$DEPLOY_SCRIPT"
print_success "本地临时文件已清理"

# 清理服务器上的部署脚本
print_info "清理服务器临时文件..."
ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_IP" "rm -f ~/deploy_cryptosignal_v740.sh" || true
print_success "服务器临时文件已清理"

# ==========================================
# 部署后操作提示
# ==========================================
if [ $SSH_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✅ 部署成功！${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${CYAN}🚀 下一步操作${NC}"
    echo ""
    echo "1️⃣  SSH连接到服务器："
    echo "   ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP"
    echo ""
    echo "2️⃣  启动系统（推荐screen方式）："
    echo "   screen -S cryptosignal -dm bash -c 'cd ~/cryptosignal && ./setup.sh'"
    echo ""
    echo "3️⃣  查看日志："
    echo "   screen -r cryptosignal"
    echo ""
    echo "4️⃣  退出日志但保持运行："
    echo "   按 Ctrl+A 然后按 D"
    echo ""
    echo "5️⃣  检查运行状态："
    echo "   ps aux | grep realtime_signal_scanner"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

exit $SSH_EXIT_CODE
