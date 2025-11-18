# 🚀 部署快速开始

## 方式1: 本地一键部署（推荐）⭐

**最安全、最方便的部署方式**

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

就这么简单！✨

**优势**：
- ✅ 敏感信息安全隔离（不会提交到Git）
- ✅ 自动上传和执行
- ✅ 自动清理临时文件
- ✅ 可重复使用，一次配置永久有效

详细文档：[部署启动器使用指南](docs/DEPLOY_LAUNCHER_GUIDE.md)

---

## 方式2: 手动部署

### 步骤1: 下载模板

```bash
# 从GitHub下载模板
curl -O https://raw.githubusercontent.com/FelixWayne0318/cryptosignal/main/docs/deploy_server_v740_TEMPLATE.sh
```

### 步骤2: 填写配置

```bash
vim deploy_server_v740_TEMPLATE.sh
# 编辑【敏感信息配置区】，填写真实API密钥
```

### 步骤3: 上传到服务器

```bash
scp deploy_server_v740_TEMPLATE.sh root@YOUR_SERVER_IP:~/deploy.sh
```

### 步骤4: 执行部署

```bash
ssh root@YOUR_SERVER_IP
chmod +x ~/deploy.sh
~/deploy.sh
```

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
- 🏆 [审计报告](AUDIT_REPORT_v7.4.0.md)

---

**版本**: v7.4.0
**最后更新**: 2025-11-18
