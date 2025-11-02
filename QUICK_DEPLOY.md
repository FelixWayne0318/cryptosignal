# 🚀 CryptoSignal 快速部署参考卡

> 一页纸快速参考 | 详细文档见 `standards/DEPLOYMENT_STANDARD.md`

---

## ⚡ 标准部署流程（3步）⭐

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第 1 步：拉取代码
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/cryptosignal
git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第 2 步：配置 Binance API（首次部署必需）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cat > config/binance_credentials.json <<'EOF'
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "您的API_KEY",
    "api_secret": "您的SECRET_KEY",
    "testnet": false,
    "_security": "只读权限API Key"
  }
}
EOF

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第 3 步：一键部署+启动（推荐）⭐
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
./deploy.sh
# 脚本会自动完成：
#  1. 停止旧进程
#  2. 备份配置
#  3. 验证代码（8步验证）
#  4. 清理缓存
#  5. 快速测试
#  6. 询问是否启动 → 输入 y 即可完成部署 ✅
```

---

## 🔄 日常运维命令

### 查看运行状态

```bash
# 检查进程
ps aux | grep realtime_signal_scanner

# 重连 Screen 会话
screen -r cryptosignal

# 查看日志
tail -f logs/scanner_*.log
```

### 停止系统

```bash
# 停止进程
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill

# 或在 Screen 中按 Ctrl+C
```

### 重启系统

```bash
cd ~/cryptosignal

# 停止
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill

# 启动
./start_production.sh
```

---

## 📊 监控命令

```bash
# 统计今日信号数
grep -c "🔔 Prime信号" logs/scanner_*.log

# 查看最近10个信号
grep "🔔 Prime信号" logs/scanner_*.log | tail -10

# 检查错误
grep -i "error" logs/scanner_*.log | tail -20
```

---

## 🆘 快速故障排查

| 问题 | 解决方案 |
|------|---------|
| **依赖缺失** | `pip3 install -r requirements.txt` |
| **API连接失败** | 检查 `config/binance_credentials.json` |
| **进程异常退出** | 查看日志 `tail -100 logs/scanner_*.log` |
| **配置错误** | 运行 `./deploy.sh` 重新验证 |

---

## 📋 三种启动方式

### 方式 A：Screen（推荐）

```bash
screen -S cryptosignal
python3 scripts/realtime_signal_scanner.py --interval 300
# 按 Ctrl+A 然后 D 分离
```

### 方式 B：快速启动脚本

```bash
./start_production.sh  # 选择 1
```

### 方式 C：后台运行

```bash
mkdir -p logs
nohup python3 scripts/realtime_signal_scanner.py --interval 300 \
  > logs/scanner_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

---

## ✅ 部署验证清单

- [ ] 代码已更新到最新提交
- [ ] Binance API 配置已填写
- [ ] `./deploy.sh` 所有验证通过
- [ ] 系统成功启动
- [ ] 进程正常运行
- [ ] WebSocket 连接成功
- [ ] 能够扫描币种并生成信号

---

## 🔐 安全提醒

- ✅ 使用**只读权限** API Key
- ✅ 配置文件不会提交到 Git
- ✅ 建议启用 IP 白名单
- ✅ 定期轮换 API Key（30-90天）

---

## 📚 详细文档

| 文档 | 内容 |
|------|------|
| `standards/DEPLOYMENT_STANDARD.md` | 完整部署规范 |
| `DEPLOYMENT_v6.1.md` | v6.1 详细指南 |
| `SERVER_DEPLOY.txt` | 命令清单 |

---

## 📞 当前版本

- **分支**: `claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ`
- **最新提交**: `6ee6bbe`
- **版本**: v6.1
- **修复内容**: I因子架构 + 阈值优化

**预期效果**: 3-7个 Prime 信号/小时（140币种）
