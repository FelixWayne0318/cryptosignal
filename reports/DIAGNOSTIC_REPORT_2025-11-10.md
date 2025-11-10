# 系统诊断报告

**诊断日期**: 2025-11-10
**诊断工具**: `scripts/system_diagnostic.py`
**系统版本**: v7.2.7

---

## 📊 诊断结果概览

- **严重问题 (P0)**: 2个
- **次要问题 (P1)**: 7个
- **警告 (Warning)**: 2个
- **正常检查**: 13项

**总体状态**: ❌ 存在关键问题，需要立即修复

---

## 🚨 P0级问题（必须立即修复）

### 问题1: 配置文件冲突导致阈值混乱

**问题描述**:
```
params.json:            prime_prob_min = 0.68
signal_thresholds.json: prime_prob_min = 0.45
```

代码在不同位置混用这两个配置源，导致行为不可预测。

**影响**:
- 置信度计算和Prime判定使用不同的阈值
- 导致信号产生不稳定
- 违反§5.2配置文件层次结构标准

**根本原因**:
- v7.2.7虽然统一了`analyze_symbol.py`的配置源，但`params.json`中仍保留旧配置
- 代码某些部分可能仍在读取`params.json`

**修复方案**:
```json
# 方案1: 修改params.json，使其与signal_thresholds.json一致
{
  "publish": {
    "prime_prob_min": 0.45,  // 改为0.45
    "prime_dims_ok_min": 3,
    "prime_dim_threshold": 30,
    ...
  }
}

# 方案2（推荐）: 完全移除params.json中的publish配置
# 让所有阈值都从signal_thresholds.json读取
```

**文件位置**:
- `config/params.json`: 第1064-1070行左右

---

### 问题2: I因子数据不足导致所有值都是50

**问题描述**:
```
I因子分布: Min=0.0, P25=50.0, 中位=50.0, P75=50.0, Max=50.0
```

所有币种的I因子都是50.0（中性值），完全没有分布。

**根本原因**:
I因子计算需要48小时的数据（默认window），但当前数据不足：
```python
# ats_core/factors_v2/independence.py:149
if (len(alt_prices) < window + 1 or
    len(btc_prices) < window + 1 or
    len(eth_prices) < window + 1):
    return 50.0, 1.0, {'error': 'Insufficient data'}
```

从扫描输出看：
```
K线数量: Min=236, 中位=300, Max=300
币龄(小时): Min=235.0, 中位=299.0, Max=299.0
```

大部分币种只有300根1h K线（300小时 = 12.5天），无法满足48小时窗口的BTC/ETH价格需求。

**影响**:
- I因子无法正确评估币种独立性
- 置信度计算受影响（I因子固定为50会降低置信度）
- 无法识别Alpha机会（高独立性币种）

**修复方案**:

**方案1（快速）**: 降低I因子的数据窗口要求
```python
# ats_core/factors_v2/independence.py:139
# 修改前
window = params.get('window_hours', 48)

# 修改后（适应当前数据量）
window = params.get('window_hours', 24)  # 48→24小时
```

**方案2（推荐）**: 改进数据获取策略
```python
# 确保获取足够的历史数据
# ats_core/pipeline/analyze_symbol.py 数据获取部分

# 对于BTC/ETH，获取更长的历史数据
btc_klines_1h = await fetch_klines(
    symbol="BTCUSDT",
    interval="1h",
    limit=500  # 增加到500根，确保足够的历史数据
)
```

**方案3（长期）**: 使用自适应窗口
```python
# ats_core/factors_v2/independence.py
# 根据数据可用性自动调整窗口大小
available_data = min(len(alt_prices), len(btc_prices), len(eth_prices))
window = min(params.get('window_hours', 48), available_data - 10)
```

---

## ⚠️ P1级问题（应该修复）

### 问题3-9: 多处硬编码阈值

**问题列表**:

1. **watch_prob_min硬编码** (analyze_symbol.py:742)
   ```python
   watch_prob_min = 0.65  # 保持原值，watch信号不再发送
   ```

2. **watch_prob_min硬编码** (analyze_symbol.py:748)
   ```python
   watch_prob_min = 0.65
   ```

3. **prime_strength_threshold硬编码** (analyze_symbol.py:932)
   ```python
   prime_strength_threshold = 35  # 配置加载失败时的默认值
   ```

4. **prime_strength_threshold硬编码** (analyze_symbol.py:980)
   ```python
   prime_strength_threshold = 35  # 降低阈值，允许早期捕捉
   ```

5. **prime_strength_threshold硬编码** (analyze_symbol.py:985)
   ```python
   prime_strength_threshold = 38  # 稍微提高一点要求
   ```

6. **confidence_threshold硬编码** (analyze_symbol.py:1000)
   ```python
   confidence_threshold = 20  # 配置加载失败时的默认值
   ```

7. **base_strength_threshold硬编码** (analyze_symbol.py:1037)
   ```python
   base_strength_threshold = 30
   ```

**影响**:
- 违反配置驱动原则
- 难以调整阈值参数
- 可能导致配置文件失效

**修复方案**:
将所有硬编码改为从配置文件读取：

```python
# 修改前
watch_prob_min = 0.65

# 修改后
watch_prob_min = new_coin_cfg.get("ultra_new_watch_prob_min", 0.65)
```

具体修复将在后续版本中系统性清理。

---

## ⚠️ 警告

### 警告1: 置信度计算受I因子影响

由于I因子都是50（中性值），置信度计算可能受到影响，导致置信度偏低。

**当前数据**:
```
置信度: Min=0.00, P25=4.00, 中位=8.00, P75=14.00, Max=29.00
```

中位数只有8，非常低。

**解决方案**: 修复I因子问题后，置信度应该会有所改善。

### 警告2: I因子文件位置

诊断脚本原本查找 `ats_core/features/independence.py`，但实际位置是 `ats_core/factors_v2/independence.py`。

这不是问题，只是诊断脚本需要更新路径。

---

## ✅ 正常检查（13项）

以下检查正常：

1. ✅ signal_thresholds.json 存在且有效
2. ✅ p0_base=0.45 正确（FI调制器参数）
3. ✅ params.json 存在且有效
4. ✅ factors_unified.json 存在且有效
5. ✅ F因子使用tanh软化，避免硬截断
6. ✅ 存在置信度计算代码
7. ✅ Prime概率最小值: 0.45 (合理)
8. ✅ Prime强度最小值: 35 (合理)
9. ✅ 置信度最小值: 20 (合理)
10. ✅ Edge最小值: 0.15 (合理)
11. ✅ F因子计算 模块导入成功
12. ✅ FI调制器 模块导入成功
13. ✅ 阈值配置 模块导入成功

---

## 📋 修复优先级建议

### 立即修复（本次会话）

**P0-1: 配置文件冲突**
- 修改 `config/params.json`，将 `prime_prob_min` 从 0.68 改为 0.45
- 或删除 `params.json` 中的 `publish` 配置节

**P0-2: I因子数据窗口**
- 将I因子窗口从48小时降为24小时
- 或改进BTC/ETH数据获取策略

### 后续修复（下一个版本）

**P1: 硬编码清理**
- 系统性清理 `analyze_symbol.py` 中的7处硬编码
- 参考v7.2.6的清理方法

---

## 🔍 根因分析

### 为什么会出现这些问题？

1. **配置冲突**: 历史遗留问题，v7.2.7虽然统一了代码，但未清理旧配置文件

2. **I因子问题**: 数据获取策略与因子计算需求不匹配
   - I因子需要48小时窗口（合理设计）
   - 但数据获取只有300根1h K线（12.5天）
   - BTC/ETH可能没有获取足够历史数据

3. **硬编码**: 逐步清理过程中的遗漏，需要系统性扫描

### 扫描无结果的原因链

```
1. I因子都是50
   ↓
2. 置信度计算受影响，中位数只有8
   ↓
3. Prime强度中位数35.5，但很多币种无法满足多个维度
   ↓
4. 置信度不足，大部分信号被过滤
   ↓
5. 375个币种，0个信号
```

---

## 📊 预期修复效果

### 修复前（当前状态）

```
扫描币种: 375
候选信号: 187
高质量信号: 0

I因子分布: 全部50.0（无分布）
置信度中位数: 8
Prime强度中位数: 35.5
```

### 修复后（预期）

```
扫描币种: 375
候选信号: 187
高质量信号: 20-40（预期）

I因子分布: 有正常分布（0-100）
置信度中位数: 20-30（提升2-3倍）
Prime强度中位数: 40-45（提升）
```

---

## 🛠️ 修复脚本

为方便修复，建议执行以下脚本：

```bash
# 1. 备份配置文件
cp config/params.json config/params.json.bak.20251110
cp config/signal_thresholds.json config/signal_thresholds.json.bak.20251110

# 2. 修复P0-1: 配置冲突
# 编辑 config/params.json，将 prime_prob_min 从 0.68 改为 0.45

# 3. 修复P0-2: I因子窗口
# 编辑 ats_core/factors_v2/independence.py:139
# 将 window = params.get('window_hours', 48) 改为 24

# 4. 清理缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# 5. 测试扫描
python3 scripts/realtime_signal_scanner_v72.py --max-symbols 50 --once
```

---

## 📚 相关文档

- **硬编码清理案例**: `standards/SYSTEM_ENHANCEMENT_STANDARD.md` v3.2.0
- **配置文件层次结构**: `standards/CONFIGURATION_GUIDE.md`
- **版本历史**: `standards/03_VERSION_HISTORY.md` (v7.2.3-v7.2.7)

---

## 🎯 总结

1. **核心问题**: 配置冲突 + I因子数据不足
2. **影响**: 375个币种无法产生任何信号
3. **修复难度**: 简单（修改2个配置文件）
4. **预期效果**: 信号数量从0恢复到20-40个

**建议**: 立即修复P0级问题，P1级问题可在v7.2.8中系统性清理。

---

**报告生成时间**: 2025-11-10
**诊断工具**: scripts/system_diagnostic.py
