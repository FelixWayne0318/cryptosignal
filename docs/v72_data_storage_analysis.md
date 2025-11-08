# v7.2 数据存储全面分析报告

**生成时间**: 2025-11-08
**检查范围**: 信号级别数据 + 扫描级别数据

---

## 📊 执行摘要

### 当前状态
| 数据类型 | 写入数据库 | 写入文件 | 状态 |
|---------|----------|---------|------|
| **扫描统计** (scan-level) | ✅ 已实现 | ✅ 已实现 | 正常 |
| **信号数据** (signal-level) | ❌ 批量扫描缺失 | ✅ 已实现 | **需修复** |

### 关键发现
1. **扫描统计数据**: 已成功写入数据库 ✅
2. **信号级别数据**: 仅在实时扫描器中写入，批量扫描器缺失 ❌
3. **文件存储**: 全部正常工作 ✅

---

## 🔍 详细分析

### 1. 扫描统计数据 (Scan-Level)

#### ✅ 数据库写入
**位置**: `ats_core/pipeline/batch_scan_optimized.py:737-744`

```python
# v7.2+: 写入数据库（历史统计）
try:
    from ats_core.data.analysis_db import get_analysis_db
    analysis_db = get_analysis_db()
    record_id = analysis_db.write_scan_statistics(summary_data)
    log(f"✅ 扫描统计已写入数据库（记录ID: {record_id}）")
except Exception as e:
    warn(f"⚠️  写入数据库失败: {e}")
```

**数据表**: `scan_statistics` (第7个表)

**字段**:
- 基础: total_symbols, signals_found, filtered
- 市场: avg_edge, avg_confidence, new_coins_count
- 性能: scan_duration_sec, scan_speed_coins_per_sec, cache_hit_rate
- 详细: rejection_reasons, factor_distribution, signals_list (JSON)

#### ✅ 文件写入
**位置**: `ats_core/pipeline/batch_scan_optimized.py:727-731`

```python
files = writer.write_scan_report(
    summary=summary_data,
    detail=detail_data,
    text_report=report
)
```

**文件清单**:
```
reports/latest/scan_summary.json    # 最新摘要（覆盖）
reports/latest/scan_summary.md      # 最新摘要（Markdown）
reports/latest/scan_detail.json     # 最新详细数据
reports/history/YYYY-MM-DD_HH-MM-SS_scan.json  # 历史记录
reports/trends.json                 # 趋势数据（最近30次）
```

**验证结果**:
```bash
$ ls -lh reports/latest/
-rw-r--r-- 1 root root 266K Nov  8 02:08 scan_detail.json
-rw-r--r-- 1 root root  53K Nov  8 02:08 scan_summary.json
-rw-r--r-- 1 root root 2.7K Nov  8 02:08 scan_summary.md

$ python3 -c "from ats_core.data.analysis_db import get_analysis_db; ..."
近30天扫描次数: 1
最新扫描: 2025-11-08
扫描币种: 456
发现信号: 12
```

**结论**: 扫描统计数据 **数据库+文件 双写** ✅

---

### 2. 信号级别数据 (Signal-Level)

#### ❌ 数据库写入 - 批量扫描器缺失

**问题**: `batch_scan_optimized.py` 中只收集统计，不写入数据库

**当前代码** (`batch_scan_optimized.py:620-621`):
```python
# v6.8: 收集统计数据（用于扫描后自动分析）
stats = get_global_stats()
stats.add_symbol_result(symbol, result)  # ❌ 只收集，不写数据库
```

**应该添加** (参考 `realtime_signal_scanner_v72.py:210-213`):
```python
if is_prime:  # 只写入Prime信号
    from ats_core.data.analysis_db import get_analysis_db
    analysis_db = get_analysis_db()
    analysis_db.write_complete_signal(result)
```

#### ✅ 数据库写入 - 实时扫描器正常

**位置**: `scripts/realtime_signal_scanner_v72.py:210-213`

```python
if self.record_data:
    self.recorder.record_signal_snapshot(v72_result)
    # 同时写入完善的分析数据库
    self.analysis_db.write_complete_signal(v72_result)
```

**数据表** (6个表):
```
market_data         # 市场原始数据（价格、成交量、资金流）
factor_scores       # 因子计算结果（MVRV, Prime, T, F, I, G）
signal_analysis     # 完整信号数据
gate_evaluation     # 四道闸门评估结果
modulator_effects   # F/I调制器影响
signal_outcomes     # 实际交易结果（人工/自动跟踪）
```

**验证结果**:
```bash
$ python3 -c "check database tables..."
market_data         :      0 条记录  # ❌ 应该有371条（最近扫描）
factor_scores       :      0 条记录  # ❌ 应该有371条
signal_analysis     :      0 条记录  # ❌ 应该有371条
gate_evaluation     :      0 条记录  # ❌ 应该有371条
modulator_effects   :      0 条记录  # ❌ 应该有371条
signal_outcomes     :      0 条记录  # ✅ 正常（需人工跟踪）
scan_statistics     :      1 条记录  # ✅ 正常
```

**原因**: 最近扫描使用的是批量扫描器（auto_commit_reports.sh调用），没有写数据库

---

## 📁 文件存储 vs 数据库存储对比

### 文件存储优势
1. ✅ **简单直观**: 可直接查看JSON/Markdown
2. ✅ **Git跟踪**: 历史变化可追溯
3. ✅ **分享方便**: 直接发送文件
4. ✅ **无需工具**: 文本编辑器即可查看

### 文件存储劣势
1. ❌ **查询困难**: 需要遍历文件
2. ❌ **数据分析**: 需要自己解析JSON
3. ❌ **历史有限**: trends.json只保留30次
4. ❌ **聚合统计**: 需要编写额外代码

### 数据库存储优势
1. ✅ **高效查询**: SQL查询，索引支持
2. ✅ **数据分析**: 直接聚合统计（AVG, SUM, GROUP BY）
3. ✅ **完整历史**: 无限制历史记录
4. ✅ **关联查询**: 多表JOIN分析
5. ✅ **趋势分析**: 时间序列查询
6. ✅ **机器学习**: 可直接导出训练数据

### 数据库存储劣势
1. ❌ **需要工具**: 需要SQLite客户端或Python
2. ❌ **不直观**: 需要编写查询语句
3. ❌ **Git不友好**: 二进制文件，无法diff

### 💡 推荐策略：**双写模式**

**当前实现**:
```
扫描统计: 数据库 ✅ + 文件 ✅  (双写)
信号数据: 数据库 ❌ + 文件 ✅  (只写文件)
```

**推荐配置**:
```
扫描统计: 数据库 + 文件  (保持双写，Git跟踪summary)
信号数据: 数据库 + 文件  (添加数据库写入，便于后续分析)
```

**原因**:
- 文件用于即时查看和Git历史
- 数据库用于深度分析和机器学习
- 双写成本低（每次扫描只多几毫秒）

---

## 🔧 需要修复的问题

### 问题1: 批量扫描器不写信号数据到数据库

**影响范围**:
- `scripts/auto_commit_reports.sh` 触发的定时扫描
- 手动运行的批量扫描

**解决方案**: 在 `batch_scan_optimized.py:653` 附近添加数据库写入

```python
# 当前代码
if is_prime and prime_strength >= min_score:
    results.append(result)
    log(f"✅ {symbol}: Prime强度={prime_strength}, 置信度={confidence:.0f}")

    # 实时回调：立即处理新发现的信号
    if on_signal_found:
        try:
            await on_signal_found(result)
        except Exception as e:
            warn(f"⚠️  信号回调失败: {e}")

# 需要添加 (v7.2增强)
if is_prime and prime_strength >= min_score:
    results.append(result)
    log(f"✅ {symbol}: Prime强度={prime_strength}, 置信度={confidence:.0f}")

    # v7.2: 写入数据库（信号级别完整数据）
    try:
        if not hasattr(self, '_analysis_db_batch'):
            from ats_core.data.analysis_db import get_analysis_db
            self._analysis_db_batch = get_analysis_db()
        self._analysis_db_batch.write_complete_signal(result)
    except Exception as e:
        warn(f"⚠️  写入数据库失败: {e}")

    # 实时回调：立即处理新发现的信号
    if on_signal_found:
        ...
```

**优化**: 使用实例变量缓存数据库连接，避免重复创建

---

## 📈 数据查询示例

### 查询扫描历史
```python
from ats_core.data.analysis_db import get_analysis_db
db = get_analysis_db()

# 查询最近7天扫描
history = db.get_scan_history(days=7)
for scan in history:
    print(f"{scan['scan_date']}: {scan['signals_found']}个信号, "
          f"平均Edge={scan['avg_edge']:.3f}")
```

### 查询信号历史
```python
# 查询最近7天的信号
signals = db.get_recent_signals(days=7, gates_passed_only=True)
for sig in signals:
    print(f"{sig['symbol']}: Conf={sig['confidence']:.1f}, "
          f"P={sig['probability']:.3f}, EV={sig['ev']:.2f}")
```

### 查询因子分析
```python
# 查询某币种的因子历史
history = db.get_factor_analysis('BTCUSDT', limit=30)
for h in history:
    print(f"T={h['t']:.1f}, F={h['f']:.1f}, I={h['i']:.1f}")
```

---

## ✅ 行动计划

1. **立即修复**: 在 `batch_scan_optimized.py` 添加信号数据库写入
2. **测试验证**: 运行一次完整扫描，检查数据库记录
3. **文档更新**: 更新部署文档，说明数据存储机制
4. **监控脚本**: `check_v72_status.sh` 已支持显示数据库统计

---

## 🎯 完成标准

修复完成后，应满足：

```bash
# 运行扫描后
$ python3 -c "check tables..."
market_data         :    371 条记录  # ✅ 等于信号数
factor_scores       :    371 条记录  # ✅ 等于信号数
signal_analysis     :    371 条记录  # ✅ 等于信号数
gate_evaluation     :    371 条记录  # ✅ 等于信号数
modulator_effects   :    371 条记录  # ✅ 等于信号数
signal_outcomes     :      0 条记录  # ✅ 正常（未跟踪结果）
scan_statistics     :      1 条记录  # ✅ 扫描统计
```

**数据一致性**:
- 信号级别表（1-5）记录数相等
- scan_statistics 每次扫描 +1
- 文件和数据库数据一致

---

**报告生成**: 2025-11-08
**下一步**: 修复 batch_scan_optimized.py 中的数据库写入
