# 🚀 CryptoSignal v6.0 快速启动

## ⚡ 一键启动（最快）

```bash
cd /home/user/cryptosignal
./start.sh
```

**这会做什么？**
- 拉取最新代码
- 启动定期扫描（每5分钟）
- 发送信号到Telegram

---

## 🧪 测试运行（验证系统）

```bash
./test_scan.sh
```

**这会做什么？**
- 拉取最新代码
- 仅扫描20个币种（约3分钟）
- 验证系统正常运行

---

## 📋 完整部署（首次使用）

```bash
./deploy_and_run.sh
```

**这会做什么？**
1. 拉取最新代码
2. 检查Python环境
3. 验证Telegram配置
4. 提供5种运行模式选择

---

## 🎯 常用命令

### 单次扫描（完整）
```bash
python3 scripts/realtime_signal_scanner.py
```

### 定期扫描（每5分钟）
```bash
python3 scripts/realtime_signal_scanner.py --interval 300
```

### 定期扫描（每15分钟）
```bash
python3 scripts/realtime_signal_scanner.py --interval 900
```

### 测试模式（20个币种）
```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 20
```

### 高质量信号（分数≥80）
```bash
python3 scripts/realtime_signal_scanner.py --interval 300 --min-score 80
```

### 仅测试不发Telegram
```bash
python3 scripts/realtime_signal_scanner.py --no-telegram
```

---

## 📱 配置Telegram（首次使用）

### 1. 创建配置文件

```bash
mkdir -p config
nano config/telegram.json
```

### 2. 填写配置

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "chat_id": "YOUR_CHAT_ID_HERE"
}
```

### 3. 获取Bot Token

1. 在Telegram搜索 @BotFather
2. 发送 `/newbot` 创建机器人
3. 获得Bot Token

### 4. 获取Chat ID

1. 向你的机器人发送任意消息
2. 访问：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. 找到 `"chat":{"id":123456789}`

---

## 🔄 更新代码

### 方法1: 使用脚本（推荐）
```bash
./deploy_and_run.sh
# 或
./start.sh  # 会自动拉取
```

### 方法2: 手动更新
```bash
git pull origin claude/review-system-overview-011CUfa54C3QqQuZNhcVBDgA
```

---

## 🖥️ 后台运行

### 使用nohup
```bash
nohup ./start.sh > logs/scanner.log 2>&1 &
```

### 使用screen
```bash
screen -S cryptosignal
./start.sh
# 按Ctrl+A然后D分离
# 重新连接: screen -r cryptosignal
```

### 使用tmux
```bash
tmux new -s cryptosignal
./start.sh
# 按Ctrl+B然后D分离
# 重新连接: tmux attach -t cryptosignal
```

---

## 📊 查看运行状态

### 查看日志（nohup）
```bash
tail -f logs/scanner.log
```

### 查看日志（systemd）
```bash
sudo journalctl -u cryptosignal -f
```

### 重新连接screen
```bash
screen -r cryptosignal
```

### 重新连接tmux
```bash
tmux attach -t cryptosignal
```

---

## ❓ 常见问题

### Q: 为什么没有收到信号？

**A**: 可能原因：
1. 当前市场没有符合条件的信号（正常）
2. 分数阈值太高（降低 `--min-score`）
3. Telegram配置错误

**测试**：
```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --min-score 40
```

### Q: 初始化太慢？

**A**:
- 正常情况3-4分钟（首次运行）
- 使用测试模式更快：`./test_scan.sh`

### Q: Telegram配置错误？

**A**:
1. 检查 `config/telegram.json` 是否存在
2. 确认格式正确（JSON）
3. 确认bot_token和chat_id已填写

---

## 📚 详细文档

- **完整部署指南**: `DEPLOYMENT.md`
- **增强型监控**: `docs/ENHANCED_MONITORING_USAGE.md`
- **系统架构**: `standards/SYSTEM_OVERVIEW.md`
- **对称性分析**: `docs/archive/SYMMETRY_ANALYSIS_REPORT.md`

---

## 🎯 推荐配置

### 生产环境（24/7运行）
```bash
# 使用systemd或screen
screen -S cryptosignal
python3 scripts/realtime_signal_scanner.py --interval 300 --min-score 70
```

### 测试环境
```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --min-score 60
```

### 高频扫描
```bash
python3 scripts/realtime_signal_scanner.py --interval 180 --min-score 65
```

### 严格筛选
```bash
python3 scripts/realtime_signal_scanner.py --interval 600 --min-score 80
```

---

## ✅ 快速检查清单

- [ ] 已克隆代码仓库
- [ ] 已安装Python 3.8+
- [ ] 已安装依赖包（numpy, pandas, websockets, aiohttp）
- [ ] 已配置Telegram（config/telegram.json）
- [ ] 已赋予脚本执行权限（chmod +x）
- [ ] 网络正常（能访问Binance API）

---

**系统版本**: v6.0 newstandards整合版
**分支**: `claude/review-system-overview-011CUfa54C3QqQuZNhcVBDgA`

🎉 **开始使用**: `./start.sh`
