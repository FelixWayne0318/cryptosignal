#!/bin/bash
#
# 测试Vultr服务器到GitHub的写入权限
#
# 使用方法：
# 1. 上传到Vultr服务器
# 2. chmod +x test_github_access.sh
# 3. ./test_github_access.sh

set -e

echo "=========================================="
echo "🧪 测试Vultr服务器到GitHub的访问权限"
echo "=========================================="

# 1. 检查Git配置
echo ""
echo "1️⃣ 检查Git配置..."
echo "Git版本:"
git --version

echo ""
echo "Git用户配置:"
git config user.name || echo "❌ 未配置user.name"
git config user.email || echo "❌ 未配置user.email"

# 2. 检查远程仓库
echo ""
echo "2️⃣ 检查远程仓库..."
git remote -v

CURRENT_REMOTE=$(git remote get-url origin)
echo "当前remote: $CURRENT_REMOTE"

# 3. 检查GitHub认证方式
echo ""
echo "3️⃣ 检查GitHub认证方式..."

# 检查SSH key
if [ -f ~/.ssh/id_rsa ] || [ -f ~/.ssh/id_ed25519 ]; then
    echo "✅ 发现SSH密钥"
    ls -la ~/.ssh/id_* 2>/dev/null | grep -v ".pub" || true

    # 测试SSH连接到GitHub
    echo ""
    echo "测试SSH连接到GitHub..."
    if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        echo "✅ SSH认证成功"
        SSH_OK=true
    else
        echo "❌ SSH认证失败"
        SSH_OK=false
    fi
else
    echo "❌ 未找到SSH密钥"
    SSH_OK=false
fi

# 检查Git凭证
echo ""
if git config credential.helper >/dev/null 2>&1; then
    echo "✅ 配置了凭证助手: $(git config credential.helper)"
else
    echo "⚠️  未配置凭证助手"
fi

# 4. 检查GitHub仓库地址格式
echo ""
echo "4️⃣ 分析仓库地址..."

if [[ $CURRENT_REMOTE == *"github.com"* ]]; then
    echo "✅ 当前remote指向GitHub"

    if [[ $CURRENT_REMOTE == git@github.com:* ]]; then
        echo "📌 使用SSH协议"
        NEEDS_SSH=true
        NEEDS_TOKEN=false
    elif [[ $CURRENT_REMOTE == https://github.com/* ]]; then
        echo "📌 使用HTTPS协议"
        NEEDS_SSH=false
        NEEDS_TOKEN=true
    fi
elif [[ $CURRENT_REMOTE == *"127.0.0.1"* ]] || [[ $CURRENT_REMOTE == *"localhost"* ]]; then
    echo "⚠️  当前remote指向本地代理（开发环境）"
    echo "📝 需要配置真实的GitHub remote"
    echo ""
    echo "建议的GitHub仓库地址："
    echo "  SSH:   git@github.com:FelixWayne0318/cryptosignal.git"
    echo "  HTTPS: https://github.com/FelixWayne0318/cryptosignal.git"
else
    echo "❓ 未知的remote类型"
fi

# 5. 创建测试文件并尝试推送
echo ""
echo "5️⃣ 测试写入权限..."

# 如果不是GitHub remote，跳过测试
if [[ $CURRENT_REMOTE != *"github.com"* ]]; then
    echo "⏭️  跳过推送测试（当前不是GitHub remote）"
    echo ""
    echo "=========================================="
    echo "📋 配置建议"
    echo "=========================================="
    echo ""
    echo "步骤1：配置GitHub remote"
    echo "  cd /path/to/cryptosignal"
    echo "  git remote set-url origin git@github.com:FelixWayne0318/cryptosignal.git"
    echo ""
    echo "步骤2：配置SSH认证（推荐）"
    echo "  # 生成SSH密钥"
    echo "  ssh-keygen -t ed25519 -C \"your_email@example.com\""
    echo "  # 查看公钥"
    echo "  cat ~/.ssh/id_ed25519.pub"
    echo "  # 添加到GitHub: Settings → SSH and GPG keys → New SSH key"
    echo ""
    echo "步骤3：测试连接"
    echo "  ssh -T git@github.com"
    echo ""
    echo "或者使用Personal Access Token（HTTPS）："
    echo "  git remote set-url origin https://github.com/FelixWayne0318/cryptosignal.git"
    echo "  # 生成token: GitHub Settings → Developer settings → Personal access tokens"
    echo "  # 第一次push时输入用户名和token"
    echo ""
    exit 0
fi

# 尝试推送测试
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "当前分支: $BRANCH"

# 创建测试文件
TEST_FILE="test_vultr_github_access_$(date +%s).txt"
echo "测试时间: $(date)" > "$TEST_FILE"
echo "服务器: $(hostname)" >> "$TEST_FILE"

git add "$TEST_FILE"
git commit -m "test: Vultr服务器GitHub写入权限测试" --no-gpg-sign

echo ""
echo "尝试推送到GitHub..."

if git push origin "$BRANCH" 2>&1; then
    echo ""
    echo "=========================================="
    echo "✅ 成功！Vultr服务器可以推送到GitHub"
    echo "=========================================="

    # 清理测试文件
    git rm "$TEST_FILE"
    git commit -m "test: 清理测试文件" --no-gpg-sign
    git push origin "$BRANCH"

    echo "✅ 测试文件已清理"
    exit 0
else
    echo ""
    echo "=========================================="
    echo "❌ 失败！Vultr服务器无法推送到GitHub"
    echo "=========================================="

    # 回滚commit
    git reset --hard HEAD~1

    echo ""
    echo "可能的原因："
    echo "1. SSH密钥未配置或未添加到GitHub"
    echo "2. Personal Access Token未配置或已过期"
    echo "3. 网络问题或防火墙限制"
    echo "4. 仓库权限不足（不是owner或collaborator）"
    echo ""
    echo "请参考上面的配置建议进行设置"

    exit 1
fi
