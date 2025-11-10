# 私有配置指南

**用途**: 在服务器上安全管理敏感凭证
**安全级别**: 高（仅服务器本地，不提交Git）

---

## 📋 为什么需要私有配置

### 问题

部署脚本 `server_deploy.sh` 使用占位符，需要用户手动填写真实凭证：

```json
// config/binance_credentials.json
{
  "api_key": "YOUR_BINANCE_API_KEY",  // ← 需要手动替换
  "api_secret": "YOUR_BINANCE_API_SECRET"
}
```

### 解决方案

使用 `server_deploy_private.sh.example` 模板：
1. ✅ 集中管理所有敏感凭证
2. ✅ 一键应用所有配置
3. ✅ 不提交到Git（安全）
4. ✅ 仅在服务器本地使用

---

## 🚀 快速开始

### 步骤1: 下载模板

```bash
# 在服务器上
cd ~
wget https://raw.githubusercontent.com/FelixWayne0318/cryptosignal/main/server_deploy_private.sh.example
```

### 步骤2: 填入真实凭证

```bash
# 编辑文件
vim server_deploy_private.sh.example

# 替换以下占位符：
# - YOUR_GITHUB_TOKEN_HERE
# - YOUR_BINANCE_API_KEY
# - YOUR_BINANCE_API_SECRET
# - YOUR_SERVER_IP
# - YOUR_TELEGRAM_BOT_TOKEN
# - YOUR_TELEGRAM_CHAT_ID
```

### 步骤3: 保存为私有文件

```bash
# 重命名并设置权限
mv server_deploy_private.sh.example ~/.cryptosignal-private.sh
chmod 600 ~/.cryptosignal-private.sh
```

### 步骤4: 应用配置并部署

```bash
# 应用私有配置
source ~/.cryptosignal-private.sh

# 运行部署脚本
./server_deploy.sh
```

---

## 📝 完整示例

### 真实凭证填写示例

```bash
# GitHub配置
export GIT_USER_NAME="FelixWayne0318"
export GIT_USER_EMAIL="felixwayne0318@gmail.com"
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Binance API配置
export BINANCE_API_KEY="cIPL0yqyYDdZLG6xhOY4HymSJFGOYN4yzbPkaqE3frx7zcQSVTSpwwmAjwTh8M9U"
export BINANCE_API_SECRET="Kywus30lpY2Xy1w4LH6OOVnm2mavb7uKuVfvlZC3bR5nbvXTQLh485sZDl3R9wqa"
export BINANCE_IP_WHITELIST="139.180.157.152"

# Telegram配置
export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
export TELEGRAM_CHAT_ID="-1003142003085"
```

---

## 🔒 安全最佳实践

### 1. 文件权限

```bash
# 确保只有所有者可读写
chmod 600 ~/.cryptosignal-private.sh

# 验证权限
ls -la ~/.cryptosignal-private.sh
# 应该显示: -rw------- (600)
```

### 2. 不提交到Git

```bash
# 确保文件在 .gitignore 中
echo "server_deploy_private.sh" >> .gitignore
echo ".cryptosignal-private.sh" >> .gitignore
```

### 3. 定期轮换凭证

```bash
# 建议每3个月更新一次
# 1. 在Binance生成新API Key
# 2. 在Telegram创建新Bot
# 3. 在GitHub生成新Token
# 4. 更新 ~/.cryptosignal-private.sh
```

### 4. 备份私有配置

```bash
# 加密备份
gpg -c ~/.cryptosignal-private.sh
# 生成 ~/.cryptosignal-private.sh.gpg

# 恢复备份
gpg ~/.cryptosignal-private.sh.gpg
```

---

## 🛠️ 使用场景

### 场景1: 首次部署

```bash
# 1. 创建私有配置
vim ~/.cryptosignal-private.sh
chmod 600 ~/.cryptosignal-private.sh

# 2. 应用配置
source ~/.cryptosignal-private.sh

# 3. 部署
./server_deploy.sh
```

---

### 场景2: 更新凭证

```bash
# 1. 编辑私有配置
vim ~/.cryptosignal-private.sh

# 2. 重新应用
source ~/.cryptosignal-private.sh

# 3. 验证
cat ~/.cryptosignal-github.env
cat ~/cryptosignal/config/binance_credentials.json
cat ~/cryptosignal/config/telegram.json
```

---

### 场景3: 自动化部署

```bash
# 创建自动部署脚本
cat > ~/auto_deploy.sh <<'EOF'
#!/bin/bash
source ~/.cryptosignal-private.sh
cd ~
./server_deploy.sh
EOF
chmod +x ~/auto_deploy.sh

# 一键部署
./auto_deploy.sh
```

---

## 📊 配置文件说明

### 1. GitHub配置

**作用**: 支持自动提交报告到Git

**文件**: `~/.cryptosignal-github.env`

**内容**:
```bash
GIT_USER_NAME="FelixWayne0318"
GIT_USER_EMAIL="felixwayne0318@gmail.com"
GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**获取Token**:
1. 访问 https://github.com/settings/tokens
2. 生成新Token（scopes: repo, workflow）
3. 复制Token填入配置

---

### 2. Binance API配置

**作用**: 获取市场数据

**文件**: `~/cryptosignal/config/binance_credentials.json`

**内容**:
```json
{
  "binance": {
    "api_key": "cIPL0yqyYDdZLG6xhOY4HymSJFGOYN4yzbPkaqE3frx7zcQSVTSpwwmAjwTh8M9U",
    "api_secret": "Kywus30lpY2Xy1w4LH6OOVnm2mavb7uKuVfvlZC3bR5nbvXTQLh485sZDl3R9wqa",
    "testnet": false,
    "_ip_whitelist": "139.180.157.152"
  }
}
```

**获取API Key**:
1. 访问 https://www.binance.com/en/my/settings/api-management
2. 创建API Key（只读权限）
3. 设置IP白名单
4. 复制API Key和Secret

---

### 3. Telegram配置

**作用**: 发送信号通知

**文件**: `~/cryptosignal/config/telegram.json`

**内容**:
```json
{
  "enabled": true,
  "bot_token": "7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70",
  "chat_id": "-1003142003085"
}
```

**获取Bot Token**:
1. 与 @BotFather 对话
2. 发送 /newbot
3. 按提示创建Bot
4. 复制Bot Token

**获取Chat ID**:
1. 将Bot添加到频道/群组
2. 发送一条消息
3. 访问 https://api.telegram.org/bot<TOKEN>/getUpdates
4. 查找 "chat":{"id":-1003142003085}

---

## 🔍 故障排查

### 问题1: 配置未生效

**症状**: 运行 `./server_deploy.sh` 后仍显示占位符

**解决方案**:
```bash
# 确认已应用私有配置
source ~/.cryptosignal-private.sh

# 验证环境变量
echo $GITHUB_TOKEN
echo $BINANCE_API_KEY
echo $TELEGRAM_BOT_TOKEN

# 重新运行部署
./server_deploy.sh
```

---

### 问题2: 权限错误

**症状**: `Permission denied`

**解决方案**:
```bash
# 检查文件权限
ls -la ~/.cryptosignal-private.sh

# 设置正确权限
chmod 600 ~/.cryptosignal-private.sh

# 验证
stat ~/.cryptosignal-private.sh
```

---

### 问题3: Git推送失败

**症状**: `Authentication failed`

**解决方案**:
```bash
# 检查Token是否正确
cat ~/.cryptosignal-github.env

# 检查Token权限（需要repo和workflow）
# 访问 https://github.com/settings/tokens

# 重新生成Token并更新
vim ~/.cryptosignal-private.sh
source ~/.cryptosignal-private.sh
```

---

## 📌 常见问题

### Q1: 私有配置文件会被提交到Git吗？

**A**: 不会。文件名以 `.cryptosignal-private` 开头或包含 `private`，已在 `.gitignore` 中排除。

---

### Q2: 可以在本地电脑使用吗？

**A**: 可以，但需要注意：
- Binance API的IP白名单需要包含本地IP
- 建议使用testnet进行本地测试

---

### Q3: 如何在多个服务器上使用？

**A**:
```bash
# 服务器1
scp ~/.cryptosignal-private.sh server1:~/
ssh server1 "source ~/.cryptosignal-private.sh && ./server_deploy.sh"

# 服务器2
scp ~/.cryptosignal-private.sh server2:~/
ssh server2 "source ~/.cryptosignal-private.sh && ./server_deploy.sh"
```

---

### Q4: 忘记私有配置文件内容怎么办？

**A**: 重新创建：
```bash
# 使用模板
cp server_deploy_private.sh.example ~/.cryptosignal-private.sh

# 从现有配置文件提取
cat ~/.cryptosignal-github.env
cat ~/cryptosignal/config/binance_credentials.json
cat ~/cryptosignal/config/telegram.json
```

---

## ✅ 安全检查清单

部署前检查：

- [ ] 私有配置文件权限 = 600
- [ ] 文件名不包含在Git中（.gitignore）
- [ ] GitHub Token有效且权限正确
- [ ] Binance API只读权限
- [ ] Binance IP白名单包含服务器IP
- [ ] Telegram Bot Token有效
- [ ] 所有占位符已替换为真实值

---

**文档结束**

相关文档：
- 部署脚本: `server_deploy.sh`
- 部署指南: `docs/SERVER_DEPLOY_GUIDE.md`
- 私有配置模板: `server_deploy_private.sh.example`
