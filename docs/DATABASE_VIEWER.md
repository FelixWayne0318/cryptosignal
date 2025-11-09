# 数据库查看指南

## 📊 数据库位置

### ❌ 数据库**不在**GitHub仓库

数据库文件被`.gitignore`排除（第44行：`data/*.db`），**不会同步到GitHub**。

原因：
- 数据库文件会频繁变化（每5分钟一次扫描）
- 文件较大（会快速增长到几MB）
- 包含实时交易数据，不适合Git版本控制

### ✅ 数据库实际位置

```
服务器: root@139.180.157.152
路径: ~/cryptosignal/data/analysis.db
```

## 📱 如何查看数据库（包括手机）

### 方法1：生成HTML报告（推荐 - 手机友好）

**在服务器上运行：**
```bash
cd ~/cryptosignal
python3 scripts/view_database.py --html
```

生成文件：`reports/database_report.html`

**手机查看步骤：**

#### 选项A：通过GitHub（如果报告已提交）
1. 在手机浏览器打开GitHub仓库
2. 进入 `reports/database_report.html`
3. 点击 "View raw" 或使用GitHub Pages

#### 选项B：通过HTTP服务器（实时数据）
```bash
# 在服务器上运行
cd ~/cryptosignal
python3 -m http.server 8000

# 然后在手机浏览器访问
http://139.180.157.152:8000/reports/database_report.html
```

**报告包含：**
- ✅ 最近50条信号详情
- ✅ F因子、I因子、四道闸门状态
- ✅ 最近7天扫描统计
- ✅ 响应式设计，手机浏览器完美显示

---

### 方法2：导出JSON数据

```bash
cd ~/cryptosignal
python3 scripts/view_database.py --json
```

生成文件：`reports/database_export.json`

可以：
- 下载到手机查看
- 使用JSON查看器APP
- 导入到Excel/Google Sheets分析

---

### 方法3：命令行查看（服务器端）

```bash
# 查看数据库摘要
python3 scripts/view_database.py

# 查看最近20条信号
python3 scripts/view_database.py --recent 20

# 查看特定币种
python3 scripts/view_database.py --symbol BTCUSDT
```

---

### 方法4：直接SQL查询（高级）

```bash
# 连接数据库
sqlite3 ~/cryptosignal/data/analysis.db

# 查询最近信号
SELECT 
    datetime(timestamp/1000, 'unixepoch', '+8 hours') as time,
    symbol, 
    side, 
    confidence, 
    all_gates_passed
FROM signal_analysis 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## 📊 数据库内容说明

### 核心表

1. **signal_analysis** - 完整信号数据
   - 信号ID、时间戳、币种、方向
   - 概率、期望值、置信度
   - 四道闸门状态
   - 完整v7.2增强数据（JSON）

2. **factor_scores** - 因子分数
   - F因子v2（资金领先）
   - I因子（市场独立性）
   - 所有分组因子（TC/VOM/B）

3. **gate_evaluation** - 四道闸门详情
   - Gate1: 数据质量
   - Gate2: 资金支持
   - Gate3: 市场风险
   - Gate4: 执行成本

4. **scan_statistics** - 扫描统计
   - 每次扫描的时间、币种数、信号数
   - 平均Edge、置信度
   - 扫描性能指标

5. **modulator_effects** - 调制器效果
   - F/I调制器对P和EV的影响

---

## 🔄 数据更新频率

- **信号数据**: 每次扫描发现Prime信号时写入（不定期）
- **扫描统计**: 每5分钟写入一次
- **数据库大小**: 每天约增长1-2MB

---

## 📱 手机查看最佳实践

### 快速查看（推荐）

1. **设置自动生成HTML报告**

在服务器上添加crontab：
```bash
# 每小时生成一次HTML报告
0 * * * * cd ~/cryptosignal && python3 scripts/view_database.py --html > /dev/null 2>&1
```

2. **提交报告到GitHub**

修改`auto_commit_reports.sh`，添加：
```bash
git add reports/database_report.html
```

这样每次扫描后报告会自动更新到GitHub。

3. **手机访问**

在手机浏览器直接打开GitHub仓库的`reports/database_report.html`。

---

## 🔒 安全注意事项

### ✅ 安全的
- HTML报告（只包含统计数据，无敏感信息）
- JSON导出（可以提交到GitHub）
- 扫描统计（公开数据）

### ❌ 不要公开
- 数据库原始文件（`analysis.db`）
- 包含API密钥的配置
- 实时交易记录（如果包含个人仓位）

---

## 📝 示例输出

### HTML报告示例

```
📊 交易信号数据库报告

总信号数: 156
扫描次数: 48
更新时间: 2025-11-09 16:30:00

🎯 最近信号
┌──────────────────┬──────────┬────┬────────┬──────┬──────┬────┬────┬────┐
│ 时间             │ 币种     │方向│置信度  │概率  │ EV   │ F  │ I  │闸门│
├──────────────────┼──────────┼────┼────────┼──────┼──────┼────┼────┼────┤
│ 2025-11-09 16:25 │ MAVUSDT  │LONG│  58.0  │0.680 │+0.028│ 55 │ 50 │ ✅ │
│ 2025-11-09 16:20 │ API3USDT │LONG│  55.0  │0.670 │+0.025│ 52 │ 48 │ ✅ │
└──────────────────┴──────────┴────┴────────┴──────┴──────┴────┴────┴────┘
```

---

## 🆘 故障排查

### 问题：数据库为空

**检查：**
```bash
ls -lh ~/cryptosignal/data/analysis.db
```

**可能原因：**
1. 扫描器未运行
2. 没有满足条件的信号
3. 数据库路径错误

**解决：**
```bash
# 检查扫描器进程
ps aux | grep realtime_signal_scanner

# 查看日志
tail -100 ~/cryptosignal/logs/scanner.log
```

---

### 问题：无法生成HTML报告

**检查：**
```bash
python3 scripts/view_database.py --html
```

**可能原因：**
1. 数据库文件不存在
2. Python依赖缺失
3. 权限问题

**解决：**
```bash
# 检查Python环境
python3 --version

# 检查数据库权限
ls -l ~/cryptosignal/data/analysis.db
```

---

## 📞 更多帮助

- 查看扫描器日志：`tail -f ~/cryptosignal/logs/scanner.log`
- 查看数据库工具帮助：`python3 scripts/view_database.py --help`
- GitHub Issues: 提交问题到仓库

