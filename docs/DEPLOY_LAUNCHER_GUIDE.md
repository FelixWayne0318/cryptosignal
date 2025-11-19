# 部署启动器使用指南

## 🎯 什么是部署启动器？

**部署启动器**是一个本地运行的脚本，可以：
- ✅ 从本地配置文件读取敏感信息
- ✅ 自动替换模板中的占位符
- ✅ 通过SSH上传并执行部署
- ✅ **敏感信息永远不会提交到Git**

## 🚀 快速开始

### 步骤1: 创建配置文件

```bash
# 在项目根目录
cd ~/cryptosignal

# 复制配置模板
cp deploy.config.example deploy.config

# 编辑配置文件，填写真实信息
vim deploy.config
```

### 步骤2: 填写配置信息

编辑 `deploy.config`，填写以下信息：

```bash
# GitHub配置
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
GITHUB_USER=YourGitHubUsername
GITHUB_BRANCH=main  # 或您想部署的分支

# Binance API配置
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=false

# Telegram配置（可选）
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# 服务器配置
SERVER_TIMEZONE=Asia/Singapore
SERVER_IP=1.2.3.4  # ← 您的服务器IP
SERVER_USER=root
SERVER_PORT=22
```

### 步骤3: 执行部署

```bash
# 一键部署
./deploy_launcher.sh
```

就这么简单！脚本会自动：
1. 验证配置
2. 生成部署脚本
3. 上传到服务器
4. 执行部署
5. 清理临时文件

---

## 📋 完整工作流程

```
┌─────────────────────────────────────┐
│  1. 本地配置文件                      │
│     deploy.config                    │
│     （不会提交到Git）                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. 部署启动器                        │
│     deploy_launcher.sh               │
│     - 读取配置                        │
│     - 替换模板占位符                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. 生成部署脚本                      │
│     /tmp/cryptosignal_deploy_xxx.sh  │
│     （临时文件，包含真实API密钥）      │
└──────────────┬──────────────────────┘
               │
               ▼ SSH上传
┌─────────────────────────────────────┐
│  4. 服务器执行                        │
│     ~/deploy_cryptosignal_v740.sh    │
│     - 安装依赖                        │
│     - 克隆代码                        │
│     - 创建配置                        │
│     - 初始化数据库                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  5. 自动清理                          │
│     - 删除本地临时文件                 │
│     - 删除服务器临时文件               │
└─────────────────────────────────────┘
```

---

## 🔐 安全性保证

### 1. 配置文件不会泄露
```bash
# .gitignore 已包含
deploy.config
deploy_cryptosignal_*.sh
```

即使您不小心执行 `git add .`，这些文件也**不会**被提交。

### 2. 临时文件自动清理
- 本地临时脚本：自动删除
- 服务器临时脚本：部署完成后自动删除

### 3. SSH传输加密
所有数据通过SSH加密传输，安全可靠。

---

## 📊 对比传统部署方式

| 特性 | 传统方式 | 部署启动器 |
|------|---------|----------|
| 编辑部署脚本 | ✅ 需要 | ❌ 不需要 |
| 手动上传 | ✅ 需要 | ❌ 自动 |
| 敏感信息管理 | ⚠️ 容易泄露 | ✅ 安全隔离 |
| 重复部署 | ⚠️ 每次重新编辑 | ✅ 重复使用配置 |
| 多服务器部署 | ⚠️ 麻烦 | ✅ 只需修改SERVER_IP |
| 临时文件清理 | ⚠️ 手动 | ✅ 自动 |

---

## 🎯 使用场景

### 场景1: 首次部署

```bash
# 1. 创建配置
cp deploy.config.example deploy.config
vim deploy.config  # 填写信息

# 2. 执行部署
./deploy_launcher.sh

# 3. SSH登录服务器启动
ssh root@YOUR_SERVER_IP
screen -S cryptosignal -dm bash -c 'cd ~/cryptosignal && ./setup.sh'
```

### 场景2: 更新部署（代码更新后）

```bash
# 配置文件已存在，直接部署
./deploy_launcher.sh
```

### 场景3: 多服务器部署

```bash
# 服务器A
vim deploy.config  # 修改SERVER_IP=1.2.3.4
./deploy_launcher.sh

# 服务器B
vim deploy.config  # 修改SERVER_IP=5.6.7.8
./deploy_launcher.sh
```

---

## 🛠️ 高级用法

### 使用不同的配置文件

```bash
# 创建多个配置文件
cp deploy.config.example deploy.config.production
cp deploy.config.example deploy.config.staging

# 修改deploy_launcher.sh中的CONFIG_FILE变量
# 或创建多个启动器脚本
```

### 自动化部署（CI/CD）

```bash
#!/bin/bash
# 在CI/CD环境中使用环境变量

export GITHUB_TOKEN="$CI_GITHUB_TOKEN"
export BINANCE_API_KEY="$CI_BINANCE_KEY"
export BINANCE_API_SECRET="$CI_BINANCE_SECRET"
export SERVER_IP="$PROD_SERVER_IP"

./deploy_launcher.sh
```

---

## ❓ 常见问题

### Q1: deploy.config会被提交到Git吗？
**A**: 不会。已添加到`.gitignore`，Git会自动忽略。

### Q2: 如何验证配置文件正确性？
**A**: 执行部署启动器时会自动验证，缺少配置会报错。

### Q3: 部署失败怎么办？
**A**:
1. 检查SSH连接：`ssh root@YOUR_SERVER_IP`
2. 查看部署日志：`~/deploy_YYYYMMDD_HHMMSS.log`
3. 检查配置文件：`cat deploy.config`

### Q4: 可以部署到Windows服务器吗？
**A**: 部署启动器需要在本地Mac/Linux运行，目标服务器必须是Linux。

### Q5: 如何切换部署分支？
**A**: 修改 `deploy.config` 中的 `GITHUB_BRANCH`

---

## 📞 需要帮助？

如果遇到问题，请检查：
1. 配置文件格式是否正确（无空格、引号）
2. SSH能否连接到服务器
3. 服务器IP是否在Binance API白名单
4. GitHub Token是否有效

---

## 🔗 相关文档

- [部署脚本模板](deploy_server_v740_TEMPLATE.sh)
- [服务器部署指南](DEPLOY_SERVER.md)
- [系统增强标准](../standards/SYSTEM_ENHANCEMENT_STANDARD.md)

---

**最后更新**: 2025-11-18
**版本**: v7.4.2
