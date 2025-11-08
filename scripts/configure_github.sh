#!/bin/bash
#
# GitHub访问配置脚本
# 用途：自动配置Git用户信息和GitHub认证
# 调用：被deploy_and_run.sh自动调用，或手动运行
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "🔧 配置GitHub访问权限"
echo "=========================================="
echo ""

# ==========================================
# 配置文件路径（不在Git仓库中）
# ==========================================
GITHUB_CONFIG="$HOME/.cryptosignal-github.env"

# ==========================================
# 1. 检查并配置Git用户信息
# ==========================================
echo "1️⃣ 配置Git用户信息..."

# 检查是否已配置
if git config user.name &>/dev/null && git config user.email &>/dev/null; then
    CURRENT_NAME=$(git config user.name)
    CURRENT_EMAIL=$(git config user.email)
    echo -e "${GREEN}✅ Git用户已配置${NC}"
    echo "   user.name: $CURRENT_NAME"
    echo "   user.email: $CURRENT_EMAIL"
else
    # 尝试从配置文件读取
    if [ -f "$GITHUB_CONFIG" ]; then
        source "$GITHUB_CONFIG"

        if [ -n "$GIT_USER_NAME" ] && [ -n "$GIT_USER_EMAIL" ]; then
            git config --global user.name "$GIT_USER_NAME"
            git config --global user.email "$GIT_USER_EMAIL"
            echo -e "${GREEN}✅ Git用户信息配置成功${NC}"
            echo "   user.name: $GIT_USER_NAME"
            echo "   user.email: $GIT_USER_EMAIL"
        else
            echo -e "${RED}❌ 配置文件缺少 GIT_USER_NAME 或 GIT_USER_EMAIL${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Git用户未配置，且未找到配置文件${NC}"
        echo ""
        echo "请创建配置文件: $GITHUB_CONFIG"
        echo "内容示例："
        echo "---"
        echo "GIT_USER_NAME=\"FelixWayne0318\""
        echo "GIT_USER_EMAIL=\"your_email@example.com\""
        echo "GITHUB_TOKEN=\"ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx\""
        echo "---"
        exit 1
    fi
fi

echo ""

# ==========================================
# 2. 配置GitHub Token（HTTPS认证）
# ==========================================
echo "2️⃣ 配置GitHub认证..."

# 检查remote是否为GitHub HTTPS
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")

if [[ $REMOTE_URL == https://github.com/* ]]; then
    echo "   Remote: $REMOTE_URL (HTTPS)"

    # 检查credential helper是否已配置
    if git config credential.helper &>/dev/null; then
        HELPER=$(git config credential.helper)
        echo -e "${GREEN}✅ Credential helper已配置: $HELPER${NC}"
    else
        # 配置credential store
        git config --global credential.helper store
        echo -e "${GREEN}✅ Credential helper已配置: store${NC}"
    fi

    # 检查是否需要配置token
    CREDENTIALS_FILE="$HOME/.git-credentials"

    if [ -f "$CREDENTIALS_FILE" ] && grep -q "github.com" "$CREDENTIALS_FILE"; then
        echo -e "${GREEN}✅ GitHub凭证已存在${NC}"
    else
        # 尝试从配置文件读取token
        if [ -f "$GITHUB_CONFIG" ]; then
            source "$GITHUB_CONFIG"

            if [ -n "$GITHUB_TOKEN" ]; then
                # 从remote URL提取用户名
                GITHUB_USER=$(echo "$REMOTE_URL" | sed -n 's#https://github.com/\([^/]*\)/.*#\1#p')

                # 写入凭证文件
                echo "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com" > "$CREDENTIALS_FILE"
                chmod 600 "$CREDENTIALS_FILE"

                echo -e "${GREEN}✅ GitHub Token已配置${NC}"
            else
                echo -e "${YELLOW}⚠️  配置文件未包含 GITHUB_TOKEN${NC}"
                echo "   首次推送时会提示输入，输入后会自动保存"
            fi
        else
            echo -e "${YELLOW}⚠️  未找到配置文件${NC}"
            echo "   首次推送时会提示输入token，输入后会自动保存"
        fi
    fi

elif [[ $REMOTE_URL == git@github.com:* ]]; then
    echo "   Remote: $REMOTE_URL (SSH)"

    # 检查SSH密钥
    if [ -f ~/.ssh/id_rsa ] || [ -f ~/.ssh/id_ed25519 ]; then
        echo -e "${GREEN}✅ SSH密钥已存在${NC}"

        # 测试SSH连接
        if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
            echo -e "${GREEN}✅ SSH认证成功${NC}"
        else
            echo -e "${YELLOW}⚠️  SSH认证失败，请检查密钥是否已添加到GitHub${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  SSH密钥不存在${NC}"
        echo "   建议切换到HTTPS或配置SSH密钥"
    fi

else
    echo -e "${YELLOW}⚠️  Remote不是GitHub，跳过配置${NC}"
    echo "   Remote: $REMOTE_URL"
fi

echo ""
echo -e "${GREEN}✅ GitHub配置完成${NC}"
echo "=========================================="
