#!/bin/bash
#
# 服务器GitHub配置向导
# 用途：在Vultr服务器首次部署时快速配置GitHub访问
# 使用：bash scripts/setup_github_config.sh
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🔐 GitHub访问配置向导"
echo "=========================================="
echo ""
echo "本向导将帮助您配置GitHub访问权限"
echo "配置后，系统可以自动提交扫描报告到仓库"
echo ""

# 配置文件路径
GITHUB_CONFIG="$HOME/.cryptosignal-github.env"

# 检查是否已存在配置
if [ -f "$GITHUB_CONFIG" ]; then
    echo -e "${YELLOW}⚠️  配置文件已存在: $GITHUB_CONFIG${NC}"
    echo ""
    read -p "是否覆盖现有配置？(y/N): " OVERWRITE
    if [[ ! $OVERWRITE =~ ^[Yy]$ ]]; then
        echo "取消配置，保留现有配置"
        exit 0
    fi
    echo ""
fi

# ==========================================
# 1. 配置Git用户信息
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 1/2: 配置Git用户信息${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查现有配置
CURRENT_NAME=$(git config user.name 2>/dev/null || echo "")
CURRENT_EMAIL=$(git config user.email 2>/dev/null || echo "")

if [ -n "$CURRENT_NAME" ]; then
    echo "当前Git用户名: $CURRENT_NAME"
    read -p "使用此用户名？(Y/n): " USE_CURRENT_NAME
    if [[ ! $USE_CURRENT_NAME =~ ^[Nn]$ ]]; then
        GIT_USER_NAME="$CURRENT_NAME"
    fi
fi

if [ -z "$GIT_USER_NAME" ]; then
    read -p "请输入Git用户名 (如: FelixWayne0318): " GIT_USER_NAME
fi

if [ -n "$CURRENT_EMAIL" ]; then
    echo "当前Git邮箱: $CURRENT_EMAIL"
    read -p "使用此邮箱？(Y/n): " USE_CURRENT_EMAIL
    if [[ ! $USE_CURRENT_EMAIL =~ ^[Nn]$ ]]; then
        GIT_USER_EMAIL="$CURRENT_EMAIL"
    fi
fi

if [ -z "$GIT_USER_EMAIL" ]; then
    read -p "请输入Git邮箱 (如: your@example.com): " GIT_USER_EMAIL
fi

# ==========================================
# 2. 配置GitHub Token
# ==========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}步骤 2/2: 配置GitHub Personal Access Token${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Personal Access Token用于HTTPS方式推送到GitHub"
echo ""
echo "如何获取Token："
echo "  1. 访问 https://github.com/settings/tokens"
echo "  2. 点击 'Generate new token (classic)'"
echo "  3. 勾选 'repo' 权限"
echo "  4. 复制生成的token（格式: ghp_xxxxxxxxxxxxx）"
echo ""

read -p "请输入GitHub Token（留空则跳过）: " GITHUB_TOKEN

# ==========================================
# 3. 保存配置
# ==========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}保存配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 创建配置文件
cat > "$GITHUB_CONFIG" <<EOF
# CryptoSignal GitHub访问配置
# 此文件包含敏感信息，请勿提交到Git仓库

# Git用户信息
GIT_USER_NAME="$GIT_USER_NAME"
GIT_USER_EMAIL="$GIT_USER_EMAIL"

# GitHub Personal Access Token (HTTPS认证)
EOF

if [ -n "$GITHUB_TOKEN" ]; then
    echo "GITHUB_TOKEN=\"$GITHUB_TOKEN\"" >> "$GITHUB_CONFIG"
else
    echo "# GITHUB_TOKEN=\"ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx\"" >> "$GITHUB_CONFIG"
fi

# 设置文件权限（仅当前用户可读写）
chmod 600 "$GITHUB_CONFIG"

echo -e "${GREEN}✅ 配置已保存到: $GITHUB_CONFIG${NC}"
echo ""

# ==========================================
# 4. 应用配置
# ==========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}应用配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 配置Git全局用户信息
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
echo -e "${GREEN}✅ Git用户信息已配置${NC}"

# 配置credential helper
if ! git config credential.helper &>/dev/null; then
    git config --global credential.helper store
    echo -e "${GREEN}✅ Git credential helper已配置${NC}"
fi

# 如果提供了token，配置凭证文件
if [ -n "$GITHUB_TOKEN" ]; then
    CREDENTIALS_FILE="$HOME/.git-credentials"

    # 检测仓库URL
    if [ -d ~/cryptosignal/.git ]; then
        cd ~/cryptosignal
        REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")

        if [[ $REMOTE_URL == https://github.com/* ]]; then
            # 提取GitHub用户名
            GITHUB_USER=$(echo "$REMOTE_URL" | sed -n 's#https://github.com/\([^/]*\)/.*#\1#p')

            # 写入凭证
            echo "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com" > "$CREDENTIALS_FILE"
            chmod 600 "$CREDENTIALS_FILE"

            echo -e "${GREEN}✅ GitHub Token已配置${NC}"
        fi
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 配置完成！${NC}"
echo "=========================================="
echo ""
echo "📋 配置摘要："
echo "  Git用户名: $GIT_USER_NAME"
echo "  Git邮箱: $GIT_USER_EMAIL"
if [ -n "$GITHUB_TOKEN" ]; then
    echo "  GitHub Token: 已配置 ✅"
else
    echo "  GitHub Token: 未配置（首次推送时会提示输入）"
fi
echo ""
echo "💡 提示："
echo "  • 配置文件: $GITHUB_CONFIG"
echo "  • 此文件已被.gitignore排除，不会提交到仓库"
echo "  • 每次运行 setup.sh 或 deploy_and_run.sh 会自动应用此配置"
echo ""
echo "🚀 现在可以运行部署脚本："
echo "  bash setup.sh"
echo ""
