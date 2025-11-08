# v7.2部署指南

## 快速开始

v7.2阶段1已经开发完成并通过所有测试。本指南将帮助你部署v7.2到生产环境，并开始积累数据为阶段2做准备。

---

## 🎯 v7.2阶段1概述

### 核心改进

| 特性 | v6.6 | v7.2阶段1 |
|------|------|----------|
| **胜率计算** | Sigmoid映射（假概率） | Bootstrap校准（启发式） |
| **因子展示** | 6个独立因子 | 3组分组因子 (TC/VOM/B) |
| **F因子** | 调制器 | v2精确计算 |
| **信号过滤** | 软约束 | 四道硬闸门 |
| **数据采集** | ❌ 无 | ✅ TradeRecorder |

### 新增组件

```
v7.2阶段1组件树：
├── ats_core/features/fund_leading.py         [F因子v2]
├── ats_core/scoring/factor_groups.py         [因子分组]
├── ats_core/calibration/empirical_calibration.py  [统计校准]
├── ats_core/pipeline/gates.py                [四道闸门]
├── ats_core/pipeline/analyze_symbol_v72.py   [v7.2集成]
├── ats_core/data/trade_recorder.py           [数据采集]
├── ats_core/outputs/telegram_fmt.py          [v7.2消息格式]
└── scripts/realtime_signal_scanner_v72.py    [v7.2扫描器]
```

---

## 📦 部署步骤

### 步骤1: 确认环境

在服务器上确认v7.2代码已更新：

```bash
cd ~/cryptosignal
git fetch origin
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
git pull

# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
```

### 步骤2: 运行集成测试

测试v7.2集成和数据采集：

```bash
python3 test_v72_integration.py
```

**预期输出：**
```
🧪 v7.2集成测试套件
======================================
测试1: TradeRecorder基础功能
✅ TradeRecorder初始化成功
✅ 测试信号已记录: BTCUSDT_TEST_1699364400000
✅ TradeRecorder测试通过

测试2: v7.2扫描器（小规模测试）
✅ v7.2扫描器创建成功
开始扫描5个币种...
✅ v7.2扫描测试完成

测试3: 数据访问和查询
✅ 数据访问测试通过

📊 测试总结
✅ 通过: TradeRecorder基础功能
✅ 通过: v7.2扫描器
✅ 通过: 数据访问和查询

总计: 3/3 测试通过
🎉 所有测试通过！v7.2集成就绪
```

### 步骤3: 小规模测试（推荐）

先用5-10个币种测试v7.2扫描器：

```bash
# 测试扫描（不发送Telegram，只记录数据）
python3 scripts/realtime_signal_scanner_v72.py --max-symbols 10 --no-telegram

# 查看数据统计
python3 scripts/realtime_signal_scanner_v72.py --show-stats
```

### 步骤4: 单次扫描测试（发送Telegram）

确认Telegram配置正确：

```bash
# 检查config/telegram.json是否存在
cat config/telegram.json

# 或者设置环境变量
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# 单次扫描，发送Telegram（测试5个币种）
python3 scripts/realtime_signal_scanner_v72.py --max-symbols 5
```

### 步骤5: 启动定期扫描

一切正常后，启动定期扫描模式：

```bash
# 方案A: 前台运行（测试用）
python3 scripts/realtime_signal_scanner_v72.py --interval 300

# 方案B: 后台运行（生产环境）
nohup python3 scripts/realtime_signal_scanner_v72.py --interval 300 > logs/v72_scanner.log 2>&1 &

# 查看运行日志
tail -f logs/v72_scanner.log

# 查看进程
ps aux | grep realtime_signal_scanner_v72
```

### 步骤6: 使用systemd服务（推荐）

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/ats-v72-scanner.service
```

内容：
```ini
[Unit]
Description=ATS v7.2 Signal Scanner
After=network.target

[Service]
Type=simple
User=cryptosignal
WorkingDirectory=/home/cryptosignal/cryptosignal
ExecStart=/usr/bin/python3 scripts/realtime_signal_scanner_v72.py --interval 300
Restart=always
RestartSec=10
StandardOutput=append:/home/cryptosignal/cryptosignal/logs/v72_scanner.log
StandardError=append:/home/cryptosignal/cryptosignal/logs/v72_scanner_error.log

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start ats-v72-scanner

# 设置开机自启
sudo systemctl enable ats-v72-scanner

# 查看状态
sudo systemctl status ats-v72-scanner

# 查看日志
sudo journalctl -u ats-v72-scanner -f
```

---

## 🔍 监控和维护

### 查看数据统计

随时查看数据采集统计：

```bash
python3 scripts/realtime_signal_scanner_v72.py --show-stats
```

**示例输出：**
```
📊 v7.2数据采集统计
======================================
总信号数: 152
通过闸门: 48 (31.6%)
平均confidence: 42.5
平均预测概率: 0.523
平均预测EV: +0.0089

多空分布:
  long: 28个
  short: 20个

最近10个信号:
  16:25:30 BTCUSDT     long  conf= 65.5 P=0.630 ✅
  16:30:15 ETHUSDT     short conf= 58.2 P=0.585 ✅
  ...
```

### 数据库位置

数据库文件：`data/trade_history.db`

可以使用SQLite工具查询：
```bash
sqlite3 data/trade_history.db

# SQL查询示例
SELECT COUNT(*) FROM signal_snapshots;
SELECT * FROM signal_snapshots ORDER BY timestamp DESC LIMIT 10;
```

### 日志文件

- 扫描器日志：`logs/v72_scanner.log`
- 错误日志：`logs/v72_scanner_error.log`
- systemd日志：`sudo journalctl -u ats-v72-scanner`

---

## ⚙️ 配置选项

### 命令行参数

```bash
python3 scripts/realtime_signal_scanner_v72.py --help
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--interval` | 扫描间隔(秒) | 不指定=单次 |
| `--max-symbols` | 最大币种数 | 全部 |
| `--min-score` | 最低confidence | 35 |
| `--no-telegram` | 禁用Telegram | False |
| `--no-record` | 禁用数据记录 | False |
| `--show-stats` | 显示统计 | False |

### 使用示例

```bash
# 单次扫描20个币种（测试）
python3 scripts/realtime_signal_scanner_v72.py --max-symbols 20

# 定期扫描，最低confidence=40
python3 scripts/realtime_signal_scanner_v72.py --interval 300 --min-score 40

# 只记录数据，不发送Telegram
python3 scripts/realtime_signal_scanner_v72.py --interval 300 --no-telegram

# 只查看统计信息
python3 scripts/realtime_signal_scanner_v72.py --show-stats
```

---

## 📊 v7.2 vs v6.6对比

### Telegram消息对比

**v6.6消息**（327字符）：
```
🔹 BTCUSDT · 现价 95,234
🟩 做多 概率55% · 有效期24h
期望收益 +1.0% · 盈亏比 1:0.0

📍 入场价: 95,234

多维分析
━━━ 🎯 A层：方向判断 ━━━
🟠 趋势    0  中性震荡
🟠 动量    0  动量中性
...
```

**v7.2消息**（565字符）：
```
🚀 交易信号
━━━━━━━━━━━━━━━━━━━━
币种：BTCUSDT
现价：95,234
方向：🟢 做多

📊 核心指标
━━━━━━━━━━━━━━━━━━━━
胜率(校准)：63.0%
期望值EV：+1.28%
盈亏比RR：2.00:1
信心度：64.5/100

🔬 v7.2因子分析
━━━━━━━━━━━━━━━━━━━━
F资金领先：94 💪 资金强势领先
TC组(50%)：78 [趋势+资金流]
VOM组(35%)：64 [量能+持仓+动量]
B组(15%)：20 [基差]

🚪 四道闸门
━━━━━━━━━━━━━━━━━━━━
✅ Gate1 数据质量：200根K线
✅ Gate2 资金支撑：F_dir=94
✅ Gate3 市场环境：独立性=55
✅ Gate4 执行成本：EV=+1.28%

✅ 全部通过，可发布

💰 执行参数
━━━━━━━━━━━━━━━━━━━━
入场：95,234
止盈：98,092 (+3.0%)
止损：93,806 (-1.5%)
仓位：5.0%

🏷 版本：v7.2 Stage1
```

---

## 🚨 故障排查

### 问题1: 模块导入失败

```bash
# 确保在正确目录
pwd  # 应该在~/cryptosignal

# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 测试导入
python3 -c "from ats_core.data.trade_recorder import get_recorder; print('OK')"
```

### 问题2: 数据库权限问题

```bash
# 检查data目录权限
ls -la data/

# 创建data目录（如果不存在）
mkdir -p data
chmod 755 data

# 检查数据库文件
ls -la data/trade_history.db
```

### 问题3: Telegram发送失败

```bash
# 检查配置
cat config/telegram.json

# 测试Telegram连接
python3 -c "
import requests
token = 'YOUR_BOT_TOKEN'
chat_id = 'YOUR_CHAT_ID'
url = f'https://api.telegram.org/bot{token}/sendMessage'
response = requests.post(url, json={'chat_id': chat_id, 'text': 'Test'})
print(response.status_code, response.text)
"
```

### 问题4: 扫描器卡住

```bash
# 查看进程
ps aux | grep python

# 查看日志
tail -100 logs/v72_scanner.log

# 杀死进程
pkill -f realtime_signal_scanner_v72

# 重新启动
python3 scripts/realtime_signal_scanner_v72.py --interval 300
```

---

## 📈 数据积累里程碑

v7.2阶段2需要足够的真实数据。以下是数据积累的里程碑：

| 时间 | 目标样本数 | 可以做什么 |
|------|-----------|----------|
| **第1天** | 50+ | 初步验证系统稳定性 |
| **第1周** | 300+ | 开始校准表优化（Bootstrap → 统计） |
| **第2周** | 500+ | 闸门阈值初步调整 |
| **第4周** | 1000+ | 校准表切换到5分位 |
| **第8周** | 2000+ | **启动阶段2全面优化** |

### 查询当前进度

```bash
# 方法1: 使用--show-stats
python3 scripts/realtime_signal_scanner_v72.py --show-stats

# 方法2: 直接查询数据库
sqlite3 data/trade_history.db "SELECT COUNT(*) FROM signal_snapshots;"

# 方法3: Python脚本
python3 -c "
from ats_core.data.trade_recorder import get_recorder
recorder = get_recorder()
stats = recorder.get_statistics()
print(f'总信号: {stats[\"total_signals\"]}')
print(f'通过闸门: {stats[\"gates_passed\"]} ({stats[\"gates_pass_rate\"]*100:.1f}%)')
"
```

---

## 🎯 下一步

### 短期（1周内）

- [ ] 部署v7.2到生产环境
- [ ] 验证Telegram消息正常发送
- [ ] 积累第一批数据（目标：50+信号）
- [ ] 监控系统稳定性

### 中期（1-2个月）

- [ ] 积累500+样本数据
- [ ] 分析数据质量
- [ ] 准备阶段2开发（统计优化）

### 长期（2-3个月后）

- [ ] 启动v7.2阶段2
- [ ] 校准表从Bootstrap切换到统计
- [ ] 闸门阈值数据驱动优化
- [ ] 成本模型精细化

---

## 📚 相关文档

- [v7.2阶段2/3详细方案](v7.2_stage2_stage3_roadmap.md)
- [v7系统演进路线图](v7_roadmap_summary.md)
- [服务器测试指南](../SERVER_TEST_INSTRUCTIONS.md)
- [服务器测试报告](../SERVER_TEST_REPORT_v72.md)

---

## 🆘 需要帮助？

如果遇到问题：
1. 查看日志文件
2. 运行测试脚本：`python3 test_v72_integration.py`
3. 查看数据统计：`python3 scripts/realtime_signal_scanner_v72.py --show-stats`
4. 检查数据库：`sqlite3 data/trade_history.db`

---

**部署愉快！** 🚀
