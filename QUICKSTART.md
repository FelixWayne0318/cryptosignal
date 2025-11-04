# CryptoSignal v6.6 快速开始指南

**一键部署 | 自动运行 | 零配置烦恼**

---

## 🚀 三种使用场景

### 场景1: 新服务器首次部署 ⭐ 推荐

```bash
# 1. 克隆仓库
cd ~
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal

# 2. 运行一键部署脚本（会引导您完成所有配置）
chmod +x setup.sh
./setup.sh
```

**setup.sh 会自动完成**:
- ✅ 检测环境（Python/pip/git/screen）
- ✅ 安装依赖
- ✅ 交互式配置（Binance API、Telegram）
- ✅ 配置定时任务（每2小时自动重启）
- ✅ 启动系统

**完成后**，系统已经在后台运行，您可以关闭SSH连接。

---

### 场景2: 切换到新分支

```bash
cd ~/cryptosignal
git checkout <新分支名>

# 运行setup.sh重新配置
./setup.sh
```

---

### 场景3: 日常运行（系统已配置）

```bash
# 手动重启系统
~/cryptosignal/auto_restart.sh

# 或者等待cron自动重启（每2小时）
# 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00
```

---

## 📂 脚本职责说明

### setup.sh - 首次部署脚本
**用途**: 新服务器或新分支的完整部署

**功能**:
1. 克隆/检出代码
2. 环境检测（Python/pip/git/screen）
3. 安装依赖
4. 交互式配置（Binance API、Telegram）
5. 配置crontab
6. 启动系统

**何时使用**:
- ✅ 新服务器首次部署
- ✅ 切换到新分支
- ✅ 重置所有配置

```bash
chmod +x setup.sh
./setup.sh
```

---

### auto_restart.sh - 自动重启脚本
**用途**: 停止旧进程、拉取最新代码、重新启动

**功能**:
1. 停止旧进程
2. 清理screen会话
3. 拉取最新代码（git pull）
4. 调用 deploy_and_run.sh

**何时使用**:
- ✅ 手动重启系统
- ✅ Cron定时调用（每2小时）

```bash
~/cryptosignal/auto_restart.sh
```

---

### deploy_and_run.sh - 部署和启动脚本
**用途**: 验证环境、配置、测试、启动

**功能**:
1. 快速环境检测
2. 配置验证
3. 清理缓存
4. 10秒快速测试
5. 启动生产环境（screen/nohup）

**何时使用**:
- ✅ 被 setup.sh 自动调用
- ✅ 被 auto_restart.sh 自动调用
- ⚠️  一般不需要手动运行

```bash
./deploy_and_run.sh
```

---

## 🛠️ 配置文件说明

### Binance API 配置
**位置**: `config/binance_credentials.json`

**模板**: `config/binance_credentials.json.example`

**获取方式**:
1. 登录 Binance Futures: https://www.binance.com/en/futures
2. API Management: https://www.binance.com/en/my/settings/api-management
3. 创建新 API Key
4. **权限**: 只需勾选 "读取" (Read)，不要勾选交易和提现

**配置示例**:
```json
{
  "binance": {
    "api_key": "your_api_key_here",
    "api_secret": "your_secret_key_here",
    "testnet": false
  }
}
```

---

### Telegram 配置
**位置**: `config/telegram.json`

**模板**: `config/telegram.json.example`

**获取Bot Token**:
1. 在 Telegram 搜索 @BotFather
2. 发送 `/newbot`
3. 按提示创建机器人
4. 复制 Bot Token

**获取Chat ID**:
1. 创建一个频道或群组
2. 将 Bot 添加为管理员
3. 发送一条消息
4. 访问: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. 找到 `"chat":{"id":-1001234567890}`
6. 复制这个 ID（包括负号）

**配置示例**:
```json
{
  "enabled": true,
  "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
  "chat_id": "-1001234567890"
}
```

---

## 📊 系统参数配置
**位置**: `config/params.json`

**无需手动配置** - 所有参数已优化

**关键参数** (可选调整):
```json
{
  "weights": {
    "T": 24.0,  // 趋势权重
    "M": 17.0,  // 动量权重
    "C": 24.0,  // CVD权重
    "V": 12.0,  // 波动率权重
    "O": 17.0,  // OI权重
    "B": 6.0    // 基差权重
  },
  "publish": {
    "prime_prob_min": 0.58,         // 最低概率阈值
    "prime_dims_ok_min": 3,         // 最少达标维度
    "prime_dim_threshold": 30       // 单维度达标分数
  }
}
```

---

## 🔧 常用管理命令

### 查看系统状态
```bash
# 检查screen会话
screen -ls

# 应该看到:
# There is a screen on:
#   12345.cryptosignal (Detached)

# 检查进程
ps aux | grep realtime_signal_scanner | grep -v grep

# 检查最新日志
tail -f ~/cryptosignal/logs/scanner_*.log
```

---

### 连接到运行中的会话
```bash
# 重连screen会话（查看实时日志）
screen -r cryptosignal

# 分离screen会话（返回命令行）
# 在screen内按: Ctrl+A, 然后按 D
```

---

### 停止系统
```bash
# 方法1: 停止screen会话
screen -S cryptosignal -X quit

# 方法2: 杀死进程
pkill -f "realtime_signal_scanner"
```

---

### 查看日志
```bash
# 查看最新扫描日志
tail -100 ~/cryptosignal/logs/scanner_*.log

# 实时跟踪日志
tail -f ~/cryptosignal/logs/scanner_*.log

# 查看部署日志
tail -100 ~/cryptosignal_*.log

# 查看最新3个日志文件
ls -lht ~/cryptosignal_*.log | head -3
```

---

### 检查定时任务
```bash
# 查看crontab配置
crontab -l

# 应该看到:
# 0 */2 * * * ~/cryptosignal/auto_restart.sh  (每2小时重启)
# 0 1 * * * find ~ -name "cryptosignal_*.log" -mtime +7 -delete  (清理旧日志)

# 检查cron服务状态
systemctl status cron
```

---

### 手动更新代码
```bash
cd ~/cryptosignal
git pull

# 然后重启
./auto_restart.sh
```

---

## 🐛 故障排查

### 问题1: 系统没有运行
```bash
# 检查screen会话
screen -ls

# 如果没有会话，查看最新部署日志找原因
tail -100 $(ls -t ~/cryptosignal_*.log | head -1)

# 手动启动
cd ~/cryptosignal
./deploy_and_run.sh
```

---

### 问题2: 没有收到Telegram通知
```bash
# 检查配置文件
cat ~/cryptosignal/config/telegram.json

# 测试Bot Token和Chat ID
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# 查看日志中的Telegram相关错误
grep -i "telegram\|发送" ~/cryptosignal/logs/scanner_*.log
```

---

### 问题3: 没有产生信号
```bash
# 查看扫描日志
tail -200 ~/cryptosignal/logs/scanner_*.log | grep "Prime强度"

# 检查prime_strength最高值
grep -o "prime_strength=[0-9.]*" ~/cryptosignal/logs/scanner_*.log | cut -d= -f2 | sort -n | tail -10

# 如果所有值都<15，说明当前市场没有强信号（正常现象）
# 可以考虑降低阈值（参考 SYSTEM_AUDIT_REPORT_20251104.md）
```

---

### 问题4: Screen启动失败
```bash
# 检查screen是否安装
command -v screen

# 如果未安装
sudo apt install screen

# 或者系统会自动fallback到nohup模式
```

---

### 问题5: 定时任务不工作
```bash
# 检查cron服务
systemctl status cron

# 如果未运行，启动cron服务
sudo systemctl start cron
sudo systemctl enable cron

# 检查crontab是否配置
crontab -l | grep auto_restart

# 手动测试脚本
~/cryptosignal/auto_restart.sh
```

---

## 📈 系统监控指标

### 性能指标
- **初始化时间**: <4分钟（首次）
- **扫描时间**: <30秒（200个币种）
- **扫描间隔**: 5分钟
- **内存使用**: ~300MB
- **API调用**: 0次/扫描（使用WebSocket）

### 信号质量指标
- **Prime强度阈值**: 25分（成熟币）
- **概率阈值**: 0.58
- **达标维度**: ≥3个（共6个）
- **防抖动**: 1/2确认，60秒冷却

---

## 🎯 使用建议

### 日常维护
1. **每天检查一次**:
   - Screen会话是否存活
   - 日志文件是否更新
   - 是否有信号产生

2. **每周检查一次**:
   - 磁盘空间是否充足
   - 日志清理是否正常

3. **无需关注**:
   - 代码自动更新（每次重启时）
   - 定时重启（cron自动执行）
   - 日志清理（cron自动执行）

### 信号接收
- Telegram频道会自动推送信号
- 每个信号包含完整的分析和建议
- 系统7x24小时自动运行

### 系统调优
- 参考 `SYSTEM_AUDIT_REPORT_20251104.md`
- 如需调整信号阈值，修改 `ats_core/pipeline/analyze_symbol.py`
- 建议先运行一周，观察信号质量再调整

---

## 📚 相关文档

- **DEPLOYMENT_GUIDE.md** - 完整部署流程（详细版）
- **SYSTEM_AUDIT_REPORT_20251104.md** - 系统审计报告
- **DATA_UPDATE_SCHEDULE.md** - 数据更新时间表
- **ORDERBOOK_UPDATE_SOLUTION.md** - 订单簿更新方案

---

## ✅ 完成部署后的检查清单

- [ ] Screen会话正在运行 (`screen -ls`)
- [ ] Python进程正在运行 (`ps aux | grep realtime_signal_scanner`)
- [ ] 日志文件在更新 (`ls -lht ~/cryptosignal/logs/`)
- [ ] Telegram配置正确 (`cat config/telegram.json`)
- [ ] Binance API配置正确 (`cat config/binance_credentials.json`)
- [ ] Crontab已配置 (`crontab -l`)
- [ ] 收到Telegram启动通知

---

**🎉 恭喜！您已成功部署 CryptoSignal v6.6**

**日常使用**: 只需运行 `./auto_restart.sh` 或等待定时自动重启

**问题反馈**: https://github.com/FelixWayne0318/cryptosignal/issues
