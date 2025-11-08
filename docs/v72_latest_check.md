# v7.2 数据持久化问题 - 最新检查结果

**检查时间**: 2025-11-08 04:48
**最新扫描**: 2025-11-08 04:14:55

---

## 📊 当前状态

### 1. 报告文件 ✅ 正常更新
```
scan_summary.json: 04:15:55 (4,960 bytes)
scan_summary.md:   04:15:55 (2,769 bytes)
scan_detail.json:  04:15:55 (301,753 bytes)
```

**内容**:
- 扫描时间: 04:14:55
- 总币种: 453
- 发现信号: **2个** (WALUSDT, KAIAUSDT)
- Git已提交: ✅ (ea4f523)

---

### 2. 数据库 ❌ **完全没有写入**

**trade_history.db**:
```
总记录: 1条（测试数据TESTUSDT）
最后修改: 11-08 03:49:43
状态: ❌ 无生产数据
```

**analysis.db**:
```
market_data: 0条 ❌
factor_scores: 0条 ❌
signal_analysis: 0条 ❌
gate_evaluation: 0条 ❌
modulator_effects: 0条 ❌
scan_statistics: 1条 (02:07的旧数据) ❌
```

**结论**: 04:14的扫描数据**完全没有写入数据库**

---

### 3. 历史报告 ❌ **没有新增**
```
reports/history/目录:
- 2025-11-08_00-00-57_scan.json
- 2025-11-07_03-29-34_scan.json

❌ 没有 2025-11-08_04-14-55_scan.json
```

---

### 4. 电报通知 ❌ **没有发送**
- 发现2个信号但电报没收到
- 可能原因：扫描器未运行或Telegram配置问题

---

## 🔍 关键发现

### 问题1: Prime状态不一致

| 币种 | scan_summary.json | scan_detail.json |
|------|-------------------|------------------|
| WALUSDT | ✅ 是信号 (Edge=0.63, Prime=77) | ❌ prime=False |
| KAIAUSDT | ✅ 是信号 (Edge=0.50, Prime=67) | ❌ prime=False |

**分析**:
- `scan_summary.json` 来自 `ScanStatistics.signals` 列表
- 币种在分析时被标记为Prime并添加到列表
- 但`scan_detail.json`中这些币种的`publish.prime=False`
- **说明有两套不同的Prime判断逻辑，或者数据在两个阶段被修改**

### 问题2: 数据库写入完全失败

**batch_scan_optimized.py 第656-665行**:
```python
try:
    self._analysis_db_batch.write_complete_signal(result)
except Exception as e:
    warn(f"⚠️  {symbol} 写入数据库失败: {e}")
    # ❌ 异常被捕获但只warn，数据静默丢失
```

**推测**:
1. 对于WALUSDT和KAIAUSDT调用了`write_complete_signal()`
2. 但抛出异常（可能缺少v72_enhancements或其他字段）
3. 异常被捕获，只输出warn（但warn可能没有记录到日志）
4. 导致数据静默失败

### 问题3: 历史报告未生成

**batch_scan_optimized.py 第776行**:
```python
history_file = self.history_dir / f"{ts_str}_scan.json"
with open(history_file, 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
```

但04:14的扫描没有生成历史文件，说明`write_scan_report()`可能有问题。

---

## 🎯 核心问题总结

### 问题A: 没有扫描器在运行
```bash
ps aux | grep scanner
# 输出为空
```
**结论**: 当前没有realtime_signal_scanner在运行

### 问题B: 数据写入静默失败
1. write_complete_signal() 失败但被捕获
2. write_scan_report() 的历史文件写入失败
3. 没有异常日志输出

### 问题C: Prime判断逻辑不一致
- 统计模块认为是Prime信号
- 但详细数据中prime=False
- 导致数据混乱

---

## 💡 解决方案

### 立即操作

#### 1. 手动测试数据库写入（诊断）
```bash
cd ~/cryptosignal

# 测试从summary.json写入信号
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/cryptosignal')
from ats_core.data.trade_recorder import get_recorder
import json

with open('reports/latest/scan_summary.json') as f:
    data = json.load(f)

if data.get('signals'):
    recorder = get_recorder()

    for sig in data['signals']:
        # 模拟一个完整的信号数据结构
        signal_data = {
            'symbol': sig['symbol'],
            'timestamp': int(time.time() * 1000),
            'side': 'LONG',
            'weighted_score': sig['confidence'],
            'scores': {},
            'v72_enhancements': {
                'P_calibrated': sig.get('P_chosen', 0.5),
                'EV_net': sig.get('edge', 0),
                'all_gates_passed': True
            },
            'price': 0,
            'atr': 0
        }

        try:
            signal_id = recorder.record_signal_snapshot(signal_data)
            print(f"✅ {sig['symbol']}: {signal_id}")
        except Exception as e:
            print(f"❌ {sig['symbol']}: {e}")
EOF
```

#### 2. 重启扫描器
```bash
# 拉取最新修复
git pull

# 重启
bash setup.sh
```

#### 3. 检查Telegram配置
```bash
cat config/telegram.json
```

---

## 📋 待验证清单

- [ ] 扫描器正在运行
- [ ] trade_history.db有新记录
- [ ] analysis.db有新记录
- [ ] reports/history有新文件
- [ ] Telegram收到通知
- [ ] Git自动提交
- [ ] Prime判断逻辑统一

---

## 🚨 紧急修复建议

1. **修复write_complete_signal的异常处理**
   - 不要静默捕获，应该记录详细错误
   - 或者使用更宽松的数据验证

2. **统一Prime判断逻辑**
   - ScanStatistics和batch_scan应该使用相同的判断标准
   - 或者明确哪个是权威来源

3. **添加详细日志**
   - 记录每次write_complete_signal的成功/失败
   - 记录异常堆栈信息

---

**诊断完成时间**: 2025-11-08 04:48
**状态**:
- 报告文件: ✅ 正常
- 数据库: ❌ 完全失败
- 电报: ❌ 未发送
- 扫描器: ❌ 未运行
