# 🚀 部署快速开始

## 方式1: 交互式部署（推荐）⭐

**最简单、最安全的部署方式 - 无需预填配置文件**

### 2步完成部署

```bash
# 步骤1: 上传部署脚本到服务器
scp docs/deploy_server_v740_TEMPLATE.sh root@YOUR_SERVER_IP:~/deploy.sh

# 步骤2: SSH连接并运行
ssh root@YOUR_SERVER_IP
chmod +x ~/deploy.sh && ./deploy.sh

# 然后按照提示输入：
# - GitHub用户名和Token
# - Binance API Key和Secret
# - Telegram配置（可选）
# - 确认配置后自动部署
```

就这么简单！✨

**优势**：
- ✅ 无需预填写配置文件（运行时输入）
- ✅ 敏感信息输入时隐藏显示
- ✅ 自动清理部署脚本（无残留）
- ✅ 配置向导式交互（不易出错）

---

## 方式2: 本地自动化部署

**适合需要重复部署的用户**

### 3步完成部署

```bash
# 步骤1: 创建配置文件
cp deploy.config.example deploy.config

# 步骤2: 填写您的真实信息
vim deploy.config
# 需要填写：
# - GITHUB_TOKEN（您的GitHub Token）
# - BINANCE_API_KEY
# - BINANCE_API_SECRET
# - SERVER_IP（服务器IP地址）

# 步骤3: 一键部署
./deploy_launcher.sh
```

**优势**：
- ✅ 配置可重复使用
- ✅ 自动上传和执行
- ✅ 自动清理临时文件

详细文档：[部署启动器使用指南](docs/DEPLOY_LAUNCHER_GUIDE.md)

---

## 部署后操作

### 启动系统（推荐screen方式）

```bash
# SSH连接到服务器
ssh root@YOUR_SERVER_IP

# 使用screen后台启动
screen -S cryptosignal -dm bash -c 'cd ~/cryptosignal && ./setup.sh'

# 查看日志
screen -r cryptosignal

# 退出日志但保持运行
# 按 Ctrl+A 然后按 D
```

### 检查运行状态

```bash
# 查看进程
ps aux | grep realtime_signal_scanner

# 查看screen会话
screen -ls

# 查看日志
tail -f ~/cryptosignal_*.log
```

---

## 需要帮助？

- 📖 [完整部署文档](docs/DEPLOY_SERVER.md)
- 🔧 [部署启动器指南](docs/DEPLOY_LAUNCHER_GUIDE.md)
- 📋 [四步决策系统](docs/FOUR_STEP_IMPLEMENTATION_GUIDE.md)
- 🏆 [审计报告](AUDIT_REPORT_v7.4.2.md)

---

**版本**: v7.4.2
**最后更新**: 2025-11-18
