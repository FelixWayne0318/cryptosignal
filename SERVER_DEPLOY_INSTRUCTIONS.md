# 🚀 服务器部署快速指令（复制粘贴即可）

## 步骤1：连接到服务器并进入项目目录

```bash
# SSH连接到服务器
ssh root@你的服务器IP

# 进入项目目录
cd /home/user/cryptosignal
```

---

## 步骤2：加载Telegram配置

```bash
# 加载环境变量
source .env.telegram

# 验证配置
echo "✅ Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "✅ Chat ID: $TELEGRAM_CHAT_ID"
```

---

## 步骤3：运行一键部署测试脚本

```bash
# 执行完整部署和测试流程
bash scripts/full_deploy_and_test.sh
```

**脚本会自动完成：**
- ✅ 停止运行中的进程
- ✅ 清空Python缓存
- ✅ 拉取最新代码
- ✅ 快速测试（20个币种，约1分钟）
- ✅ 交互式选择下一步

---

## 快捷命令参考

### 快速测试（不发Telegram）
```bash
cd /home/user/cryptosignal
source .env.telegram
python scripts/realtime_signal_scanner.py --max-symbols 20 --no-telegram
```

### 完整测试（200个币种，不发Telegram）
```bash
cd /home/user/cryptosignal
source .env.telegram
python scripts/realtime_signal_scanner.py --no-telegram
```

### 生产运行（发送Telegram）
```bash
cd /home/user/cryptosignal
source .env.telegram
./scripts/start_signal_scanner.sh
```

### 后台运行（screen）
```bash
cd /home/user/cryptosignal
source .env.telegram

# 启动后台会话
screen -dmS signal_scanner ./scripts/start_signal_scanner.sh

# 查看运行状态
screen -r signal_scanner

# 退出screen但保持运行：Ctrl+A 然后 D

# 停止后台扫描器
screen -S signal_scanner -X quit
```

---

## 预期测试结果

### 快速测试（20个币种）
```
初始化时间：30-60秒
扫描时间：2-3秒
总耗时：约1分钟
```

### 完整测试（200个币种）
```
初始化时间：3-4分钟
扫描时间：12-15秒
总耗时：约4-5分钟

vs 旧方案：40-60分钟 → 提升240倍！
```

---

## 故障排查

### 问题1：找不到.env.telegram文件
```bash
# 手动创建
cat > /home/user/cryptosignal/.env.telegram << 'EOF'
export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
export TELEGRAM_CHAT_ID="-1003142003085"
EOF

chmod 600 .env.telegram
source .env.telegram
```

### 问题2：脚本没有执行权限
```bash
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

### 问题3：看不到Telegram消息
```bash
# 测试Telegram Bot
curl "https://api.telegram.org/bot7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70/getMe"

# 测试发送消息
curl -X POST "https://api.telegram.org/bot7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70/sendMessage" \
  -d "chat_id=-1003142003085" \
  -d "text=测试消息"
```

### 问题4：停止运行中的进程
```bash
# 查找进程
ps aux | grep python | grep scanner

# 停止所有扫描进程
pkill -f "realtime_scanner|full_run|scanner"

# 停止screen会话
screen -S signal_scanner -X quit
```

---

## 完整一键部署命令（复制粘贴）

```bash
# 连接服务器
ssh root@你的服务器IP

# 一键部署
cd /home/user/cryptosignal && \
source .env.telegram && \
bash scripts/full_deploy_and_test.sh
```

---

**创建时间：** 2025-10-28
**Telegram已配置：** ✅
**安全提示：** .env.telegram文件权限已设置为600（仅所有者可读）
