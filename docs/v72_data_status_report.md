# v7.2 数据持久化状态报告

**生成时间**: 2025-11-08 04:15
**检查范围**: 数据库、报告文件、Git提交

---

## 📊 数据现状

### 1. **trade_history.db** (TradeRecorder)
```
总记录数: 1条
内容: 测试数据（TESTUSDT, 2025-11-08 03:49:43）
状态: ❌ 无生产数据
```

**表结构**: ✅ 正常
**最后修改**: 2025-11-08 03:49

---

### 2. **analysis.db** (AnalysisDB)
```
总表数: 7个
scan_statistics: 1条记录 ✅
market_data: 0条记录 ❌
factor_scores: 0条记录 ❌
signal_analysis: 0条记录 ❌
gate_evaluation: 0条记录 ❌
modulator_effects: 0条记录 ❌
signal_outcomes: 0条记录 ❌
```

**scan_statistics记录**:
- 时间: 2025-11-08 02:07:53
- 币种数: 456
- 信号数: 12
- 过滤数: 444

**问题**: scan_statistics显示只找到**12个信号**，但reports文件显示**371个信号**！

---

### 3. **reports/latest/** (报告文件)
```
scan_summary.json: 2025-11-08 02:08:50
scan_summary.md:   2025-11-08 02:08:50
scan_detail.json:  2025-11-08 02:08:50
```

**内容**:
- 扫描时间: 2025-11-08 02:07:54
- 扫描币种: 456个
- 信号数量: **371个** ← 与数据库不一致！
- 前5个信号: XPLUSDT, WALUSDT, PROVEUSDT, FLMUSDT, MAGICUSDT

---

### 4. **reports/history/** (历史报告)
```
总文件数: 2个
最新: 2025-11-08_00-00-57_scan.json
最旧: 2025-11-07_03-29-34_scan.json
```

---

### 5. **Git提交历史**
```
4449f6d - scan: 2025-11-08 02:07:54 - 456币种, 371信号 ⚡
```

---

## ❌ 核心问题

### 问题1: 信号数量不一致
| 数据源 | 信号数 | 时间 |
|--------|--------|------|
| reports/latest/ | **371个** | 02:07:54 |
| analysis.db (scan_statistics) | **12个** | 02:07:53 |
| Git提交 | **371个** | 02:07:54 |

**结论**: scan_statistics中的数据是错误的！

### 问题2: 信号详细数据缺失
- 02:07:54扫描找到了371个Prime信号
- 但371个信号的详细数据（market_data, factor_scores等）**完全没有写入**
- 只写入了scan_statistics（而且数据还是错的）

### 问题3: TradeRecorder未被使用
- trade_history.db只有测试数据
- 实际扫描没有调用TradeRecorder

---

## 🔍 原因分析

### 1. **batch_scan_optimized.py 的写入逻辑**

```python
# 第656-665行
try:
    if not hasattr(self, '_analysis_db_batch'):
        from ats_core.data.analysis_db import get_analysis_db
        self._analysis_db_batch = get_analysis_db()

    # 写入信号详细数据
    self._analysis_db_batch.write_complete_signal(result)
except Exception as e:
    # ❌ 异常被捕获但只warn，不影响主流程
    warn(f"⚠️  {symbol} 写入数据库失败: {e}")
```

**问题**:
- 如果write_complete_signal()抛出异常
- 异常被捕获，只输出warn
- 但warn信息可能没有被记录到日志
- 导致数据静默失败

### 2. **write_complete_signal() 可能失败的原因**

```python
def write_complete_signal(self, data: Dict[str, Any]) -> str:
    self.write_market_data(data)      # 需要特定字段
    self.write_factor_scores(data)    # 需要特定字段
    self.write_signal_analysis(data)  # 需要特定字段
    self.write_gate_evaluation(...)   # 需要v72_enhancements
    self.write_modulator_effects(...) # 需要v72_enhancements
```

**可能的失败点**:
1. `data`结构不符合预期（缺少v72_enhancements）
2. 某个必需字段缺失（如timestamp, symbol等）
3. 类型不匹配（expected REAL but got None）

### 3. **为什么scan_statistics有数据但只有12个信号？**

```python
# 第750-755行
try:
    from ats_core.data.analysis_db import get_analysis_db
    analysis_db = get_analysis_db()
    record_id = analysis_db.write_scan_statistics(summary_data)
    log(f"✅ 扫描统计已写入数据库（记录ID: {record_id}）")
except Exception as e:
    warn(f"⚠️  写入数据库失败: {e}")
```

**分析**:
- write_scan_statistics成功执行
- 但summary_data中的signals_found=12（错误）
- 实际应该是371

---

## 🎯 关键发现

### 用户提供的03:37:46日志
```
[2025-11-08 03:37:46Z] 📊 扫描统计:
   总币种数: 277
   v7.2增强: 277
   Prime信号: 0
```

这个日志来自 **realtime_signal_scanner_v72.py**，不是batch_scan_optimized.py！

**重要**:
1. realtime_signal_scanner_v72.py 使用TradeRecorder
2. batch_scan_optimized.py 使用AnalysisDB
3. 02:07的扫描使用的是batch_scan_optimized.py
4. 03:37的扫描可能使用的是realtime_signal_scanner_v72.py（但数据丢失）

---

## ✅ 已修复的问题

1. ✅ 路径问题：改用绝对路径
2. ✅ TradeRecorder路径：`/home/user/cryptosignal/data/trade_history.db`
3. ✅ AnalysisDB路径：`/home/user/cryptosignal/data/analysis.db`

---

## ❌ 仍需解决的问题

### 1. **write_complete_signal() 静默失败**
- 需要查看02:07扫描的完整日志
- 检查是否有warn信息
- 修复数据结构不匹配问题

### 2. **scan_statistics 数据错误**
- signals_found应该是371，不是12
- 需要检查write_scan_statistics()的实现

### 3. **没有扫描器在运行**
- 当前没有realtime_signal_scanner_v72.py在运行
- 需要重启服务

---

## 💡 下一步建议

### 1. 立即操作
```bash
# 拉取最新修复
cd ~/cryptosignal
git pull

# 重启扫描器
bash setup.sh
```

### 2. 调试write_complete_signal失败
```bash
# 手动测试写入
cd ~/cryptosignal
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.data.analysis_db import get_analysis_db
import json

# 读取最新报告中的一个信号
with open('/home/user/cryptosignal/reports/latest/scan_detail.json') as f:
    data = json.load(f)

# 尝试写入第一个信号
if data.get('signals'):
    signal = data['signals'][0]

    db = get_analysis_db()
    try:
        signal_id = db.write_complete_signal(signal)
        print(f"✅ 写入成功: {signal_id}")
    except Exception as e:
        print(f"❌ 写入失败: {e}")
        import traceback
        traceback.print_exc()
EOF
```

### 3. 监控下次扫描
- 等待下次扫描（每5分钟）
- 检查数据是否正确写入
- 查看日志是否有异常

---

## 📋 数据验证清单

- [ ] trade_history.db有新记录
- [ ] analysis.db的market_data有数据
- [ ] analysis.db的factor_scores有数据
- [ ] analysis.db的signal_analysis有数据
- [ ] scan_statistics的signals_found正确
- [ ] reports/latest/文件更新
- [ ] reports/history/有新文件
- [ ] Git有新的scan提交

---

**报告生成时间**: 2025-11-08 04:15
**修复状态**: 路径已修复 ✅ | 数据写入待验证 ⏳
