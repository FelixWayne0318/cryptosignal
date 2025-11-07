# Vultr服务器GitHub写入权限配置指南

本文档指导如何让Vultr服务器能够自动推送扫描结果到GitHub仓库。

---

## 🎯 目标

让Vultr服务器能够：
1. ✅ 自动扫描币种
2. ✅ 写入报告到 `reports/` 目录
3. ✅ 自动提交到Git
4. ✅ **自动推送到GitHub仓库** ← 需要配置

---

## 🧪 第一步：测试当前状态

在Vultr服务器上运行：

```bash
cd /path/to/cryptosignal
bash test_github_access.sh
```

测试脚本会检查：
- ✅ Git配置
- ✅ 远程仓库地址
- ✅ SSH密钥
- ✅ 推送权限

---

## ⚙️ 第二步：配置方法（二选一）

### **方法1：SSH密钥认证（推荐）** ⭐

#### 优势
- ✅ 更安全
- ✅ 永久有效（除非手动删除）
- ✅ 无需输入密码

#### 配置步骤

**1. 在Vultr服务器生成SSH密钥**
```bash
# 生成ED25519密钥（更安全）
ssh-keygen -t ed25519 -C "vultr-server@cryptosignal"

# 或者生成RSA密钥（兼容性更好）
ssh-keygen -t rsa -b 4096 -C "vultr-server@cryptosignal"

# 按提示操作：
# - 文件位置：直接回车（默认 ~/.ssh/id_ed25519）
# - 密码：直接回车（无密码，方便自动化）
```

**2. 查看公钥**
```bash
cat ~/.ssh/id_ed25519.pub
# 或
cat ~/.ssh/id_rsa.pub
```

**3. 添加公钥到GitHub**
- 登录GitHub
- 点击头像 → Settings
- 左侧菜单 → SSH and GPG keys
- 点击 "New SSH key"
- Title: `Vultr Server - CryptoSignal`
- Key: 粘贴公钥内容
- 点击 "Add SSH key"

**4. 配置Git remote为SSH**
```bash
cd /path/to/cryptosignal
git remote set-url origin git@github.com:FelixWayne0318/cryptosignal.git
```

**5. 测试连接**
```bash
ssh -T git@github.com
```

期望输出：
```
Hi FelixWayne0318! You've successfully authenticated, but GitHub does not provide shell access.
```

**6. 测试推送**
```bash
bash test_github_access.sh
```

---

### **方法2：Personal Access Token（HTTPS）**

#### 优势
- ✅ 配置简单
- ✅ 可设置细粒度权限

#### 配置步骤

**1. 生成Personal Access Token**
- 登录GitHub
- 点击头像 → Settings
- 左侧菜单 → Developer settings → Personal access tokens → Tokens (classic)
- 点击 "Generate new token (classic)"
- Note: `Vultr Server - CryptoSignal`
- Expiration: 根据需要选择（建议No expiration）
- Select scopes:
  - ✅ `repo` (完整仓库访问)
- 点击 "Generate token"
- **⚠️ 立即复制token（只显示一次）**

**2. 配置Git remote为HTTPS**
```bash
cd /path/to/cryptosignal
git remote set-url origin https://github.com/FelixWayne0318/cryptosignal.git
```

**3. 配置凭证存储**
```bash
# 永久存储凭证（明文，谨慎使用）
git config --global credential.helper store

# 或者缓存15分钟
git config --global credential.helper cache
```

**4. 首次推送（输入token）**
```bash
git push origin main
# Username: FelixWayne0318
# Password: <粘贴刚才复制的token>
```

如果使用了 `credential.helper store`，凭证会保存在 `~/.git-credentials`：
```
https://FelixWayne0318:<token>@github.com
```

**5. 测试**
```bash
bash test_github_access.sh
```

---

## 🔒 安全建议

### SSH密钥
- ✅ 建议：为自动化服务生成独立密钥
- ✅ 建议：密钥无密码保护（方便自动化）
- ⚠️ 注意：保护好私钥文件（chmod 600）
- ✅ 优势：可以随时在GitHub删除，立即撤销访问

### Personal Access Token
- ✅ 建议：使用细粒度token（Fine-grained tokens）
- ✅ 建议：只授予必要的仓库和权限
- ⚠️ 注意：token类似密码，不要泄露
- ✅ 优势：可以随时在GitHub撤销

### credential.helper store
- ⚠️ 警告：明文存储在 `~/.git-credentials`
- 建议：确保服务器安全，限制文件权限
```bash
chmod 600 ~/.git-credentials
```

---

## 🧪 验证配置

运行完整测试：

```bash
cd /path/to/cryptosignal
bash test_github_access.sh
```

期望输出：
```
✅ 成功！Vultr服务器可以推送到GitHub
```

---

## 🚀 完整工作流程

配置成功后，每次扫描会自动：

1. 扫描404个币种
2. 写入 `reports/latest/scan_summary.json`
3. 自动 `git add reports/`
4. 自动 `git commit -m "scan: 2025-11-07 ..."`
5. 自动 `git push origin <branch>` ← **现在会成功！**
6. Claude直接读取GitHub仓库的最新报告

---

## 🔧 故障排查

### SSH连接失败
```bash
# 详细调试
ssh -vT git@github.com

# 检查SSH配置
cat ~/.ssh/config

# 确认密钥权限
ls -la ~/.ssh/
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

### HTTPS认证失败
```bash
# 检查凭证配置
git config --global credential.helper

# 清除缓存的凭证
git config --global --unset credential.helper
rm ~/.git-credentials

# 重新配置
git config --global credential.helper store
```

### 推送被拒绝
```bash
# 检查分支保护规则
# GitHub仓库 → Settings → Branches

# 检查仓库权限
# 确保账号是owner或有write权限

# 检查Git用户配置
git config user.name
git config user.email
```

---

## 📋 快速配置检查清单

在Vultr服务器上依次检查：

- [ ] Git已安装：`git --version`
- [ ] 克隆了仓库：`cd /path/to/cryptosignal`
- [ ] SSH密钥已生成：`ls ~/.ssh/id_*`
- [ ] 公钥已添加到GitHub
- [ ] Remote指向GitHub：`git remote -v`
- [ ] SSH连接成功：`ssh -T git@github.com`
- [ ] 测试脚本通过：`bash test_github_access.sh`

---

## 💡 推荐配置

**生产环境（Vultr服务器）：**
- ✅ 使用SSH密钥认证
- ✅ 密钥无密码保护
- ✅ 在GitHub为该密钥设置明确的名称
- ✅ 定期检查密钥是否仍然有效

**原因：**
- 更安全
- 更稳定
- 更容易管理和撤销
