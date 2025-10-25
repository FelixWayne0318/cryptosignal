# 批次1部署指南 - 数据持久化系统

**状态**: ✅ 已完成并推送到GitHub
**分支**: `claude/analyze-system-improvements-011CUTZA4j28R7iSVXcgcAs9`
**完成时间**: 2025-10-25

---

## 📦 批次1包含内容

### 新增文件（7个）
```
ats_core/database/
├── __init__.py                 # 模块初始化
├── models.py                   # 数据库模型（Signal/DailyMetrics表）
└── operations.py               # CRUD操作封装

scripts/
├── init_database.py            # 数据库初始化脚本
└── query_stats.py              # 统计查询脚本

requirements.txt                # Python依赖包列表
```

### 修改文件（1个）
```
tools/manual_run.py             # 添加数据库记录功能
```

---

## 🚀 部署步骤（在Vultr服务器上执行）

### 步骤1：拉取最新代码

```bash
# 1. 进入项目目录
cd ~/cryptosignal

# 2. 拉取最新代码
git fetch
git checkout claude/analyze-system-improvements-011CUTZA4j28R7iSVXcgcAs9
git pull

# 3. 验证文件
ls -la ats_core/database/
ls -la scripts/init_database.py scripts/query_stats.py
cat requirements.txt
```

**预期结果**：
```
✅ ats_core/database/ 目录存在
✅ init_database.py 和 query_stats.py 存在
✅ requirements.txt 包含 numpy, sqlalchemy 等
```

---

### 步骤2：安装Python依赖

```bash
# 1. 确保pip最新
pip3 install --upgrade pip

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 验证安装
python3 -c "import numpy, pandas, sqlalchemy, aiohttp, pytest; print('✅ All packages installed successfully')"
```

**预期结果**：
```
✅ All packages installed successfully
```

**如果失败**：
```bash
# 单独安装可能失败的包
pip3 install numpy==1.24.3
pip3 install pandas==2.0.3
pip3 install sqlalchemy==2.0.19
pip3 install aiohttp==3.8.5
pip3 install pytest==7.4.0
```

---

### 步骤3：初始化数据库

```bash
# 1. 创建数据目录（如果不存在）
mkdir -p data/database

# 2. 初始化数据库
python3 scripts/init_database.py

# 3. 验证数据库文件已创建
ls -lh data/database/cryptosignal.db

# 4. 检查表结构（可选）
sqlite3 data/database/cryptosignal.db ".tables"
```

**预期结果**：
```
✅ Database tables created successfully
✅ data/database/cryptosignal.db 文件已创建（几KB大小）

SQLite tables:
daily_metrics  signals
```

---

### 步骤4：测试运行

```bash
# 测试1：分析3个币种（不发送Telegram，保存到数据库）
python3 tools/manual_run.py --top 3

# 测试2：查看数据库统计
python3 scripts/query_stats.py

# 测试3：查看最近的信号
python3 scripts/query_stats.py --recent 10
```

**预期结果**：
```
测试1输出：
  [1/3] 分析 BTCUSDT...
  ✅ Signal saved: #1 BTCUSDT LONG 62.5%
  [2/3] 分析 ETHUSDT...
  ✅ Signal saved: #2 ETHUSDT LONG 58.3%
  ...
  ============================================================
  分析摘要
  ============================================================
  候选总数: 3
  分析成功: 3
  已发送: 0
  已保存到数据库: 3
  失败: 0
  ============================================================

测试2输出：
  ======================================================================
    Performance Summary (Last 30 Days)
  ======================================================================

  📊 Trading Statistics
    Total Trades:      0
    ⚠️  No closed trades in the last 30 days

测试3输出：
  ======================================================================
    Recent Signals (Last 10)
  ======================================================================

  ID     Symbol       Side   Prob   Status   PnL%     Time
  ----------------------------------------------------------------------
  3      BNBUSDT      🟩long  60.2%  🔵open    -        10-25 08:45
  2      ETHUSDT      🟩long  58.3%  🔵open    -        10-25 08:44
  1      BTCUSDT      🟩long  62.5%  🔵open    -        10-25 08:43
```

---

### 步骤5：完整测试（带Telegram发送）

```bash
# 确保环境变量已设置
source .env
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID

# 分析并发送前5个币种
python3 tools/manual_run.py --send --top 5

# 再次查看统计
python3 scripts/query_stats.py
```

**预期结果**：
```
✅ 数据库记录已启用
✅ Telegram消息成功发送
✅ 数据库中有新记录
```

---

## ✅ 验收标准

### 必须通过的测试

- [ ] **依赖安装**：`python3 -c "import sqlalchemy"` 成功
- [ ] **数据库创建**：`data/database/cryptosignal.db` 文件存在
- [ ] **信号保存**：运行 `manual_run.py` 后能看到 "已保存到数据库: X"
- [ ] **统计查询**：`query_stats.py` 能显示信号列表
- [ ] **未平仓查询**：`query_stats.py --open` 能显示持仓
- [ ] **向后兼容**：不影响现有功能（Telegram发送仍正常）

---

## 🎯 使用示例

### 示例1：每日运行并记录

```bash
#!/bin/bash
# daily_analysis.sh - 每日定时任务

cd ~/cryptosignal
source .env

# 分析前20个币种，发送到Telegram，保存到数据库
python3 tools/manual_run.py --send --top 20

# 计算今日指标
python3 -c "
from ats_core.database.operations import calculate_daily_metrics
calculate_daily_metrics()
"

# 查看今日统计
python3 scripts/query_stats.py --days 1
```

### 示例2：查询性能摘要

```bash
# 最近7天摘要
python3 scripts/query_stats.py --days 7

# 最近30天详细
python3 scripts/query_stats.py --days 30 --recent 50
```

### 示例3：手动更新信号结果

```python
# update_signal.py
from ats_core.database import update_signal_exit

# 手动平仓信号#1
update_signal_exit(
    signal_id=1,
    exit_price=67850.5,
    exit_reason='tp1',
    pnl_percent=2.5,  # 可选，会自动计算
    notes='手动止盈'
)
```

---

## 🐛 常见问题

### 问题1：找不到 sqlalchemy 模块

**原因**：依赖未安装

**解决**：
```bash
pip3 install sqlalchemy==2.0.19
```

---

### 问题2：数据库文件权限错误

**原因**：data/database 目录权限问题

**解决**：
```bash
mkdir -p data/database
chmod 755 data/database
python3 scripts/init_database.py
```

---

### 问题3：Database not available 警告

**原因**：数据库模块导入失败

**检查**：
```bash
python3 -c "from ats_core.database import save_signal; print('OK')"
```

**如果失败**：检查 ats_core/database/ 目录是否存在

---

### 问题4：想禁用数据库记录

**解决**：
```bash
# 使用 --no-db 选项
python3 tools/manual_run.py --send --top 10 --no-db
```

---

## 📊 数据库schema参考

### Signal表（主要字段）

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    timestamp DATETIME,
    side TEXT,              -- 'long' or 'short'
    probability FLOAT,
    scores TEXT,            -- JSON: {"T": 85, "M": 70, ...}
    f_score FLOAT,
    f_adjustment FLOAT,
    entry_price FLOAT,
    stop_loss FLOAT,
    take_profit_1 FLOAT,
    take_profit_2 FLOAT,
    status TEXT,            -- 'open', 'closed', 'expired'
    exit_price FLOAT,
    exit_time DATETIME,
    pnl_percent FLOAT,
    created_at DATETIME
);
```

### 查询示例

```sql
-- 查看最近10个信号
SELECT id, symbol, side, probability, status, pnl_percent
FROM signals
ORDER BY timestamp DESC
LIMIT 10;

-- 统计胜率
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END) as wins,
    AVG(pnl_percent) as avg_pnl
FROM signals
WHERE status = 'closed';

-- 分方向统计
SELECT
    side,
    COUNT(*) as count,
    AVG(probability) as avg_prob,
    SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate
FROM signals
WHERE status = 'closed'
GROUP BY side;
```

---

## 📈 后续步骤

批次1部署成功后，请：

1. **运行至少1周**
   - 每天使用 `manual_run.py --send` 运行
   - 积累至少50-100个信号样本

2. **观察数据质量**
   - 使用 `query_stats.py` 查看统计
   - 记录哪些维度准确率低

3. **准备批次2**
   - 有了数据后，可以开始实施回测系统
   - 验证和优化参数配置

---

## 🎉 批次1完成标志

当你看到以下输出，表示批次1成功部署：

```bash
$ python3 scripts/query_stats.py --days 7

======================================================================
  CryptoSignal Database Statistics
======================================================================

======================================================================
  Performance Summary (Last 7 Days)
======================================================================

📊 Trading Statistics
  Total Trades:      15
  Winning Trades:    8 (53.3%)
  Losing Trades:     7 (46.7%)

💰 P&L Statistics
  Total PnL:         +12.5%
  Average Win:       +5.2%
  Average Loss:      -3.1%
  Profit Factor:     1.89
  ...

⭐ Performance Rating
  ✅ Good (Win Rate: 53.3%)
```

---

## 📞 需要帮助？

如果遇到问题：

1. 检查日志输出
2. 运行测试脚本验证
3. 查看本文档的"常见问题"部分
4. 告诉我具体的错误信息

**准备好后，告诉我测试结果，我们继续批次2（回测系统）！** 🚀
