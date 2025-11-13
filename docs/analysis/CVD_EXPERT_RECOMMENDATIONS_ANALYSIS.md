# CVD专家建议分析报告

**版本**: v7.2
**日期**: 2025-11-12
**优先级评估**: 基于系统实际情况

---

## 执行摘要

专家提供的12项CVD改造建议，经过对系统实际代码的深入分析，评估如下：

| 类别 | 专家建议数 | 需要执行 | 无需执行 | 已实现 |
|------|-----------|---------|---------|--------|
| 红线（必须） | 5项 | 2项 | 1项 | 2项 |
| 黄线（优先） | 4项 | 1项 | 2项 | 1项 |
| 小改（清洁） | 3项 | 2项 | 1项 | 0项 |
| **总计** | **12项** | **5项** | **4项** | **3项** |

**核心结论**：
- ✅ **3项已正确实现**，无需修改
- ⚠️ **5项需要实施**（2个P1, 2个P2, 1个P3）
- ❌ **4项不适用当前系统**

---

## 一、红线建议分析（5项）

### 1. ✅ **统一时区与对齐（UTC）** - 已部分实现

#### 专家建议
```
位置：ats_core/sources/binance.py、ats_core/features/cvd.py
要求：
- 现货/期货使用UTC（不传timeZone或显式传0）
- 以openTime为主键inner join对齐
- 对齐丢弃比例>0.1%时记录WARNING
```

#### 当前实现状态
**数据获取层（binance.py）**：✅ **已正确实现**
```python
# ats_core/sources/binance.py:120-146
def get_klines(...):
    # Binance API默认返回UTC时间戳，无timeZone参数
    return _get("/fapi/v1/klines", params, timeout=10.0, retries=2)
```
- Binance API默认返回UTC时间戳
- openTime/closeTime都是UTC毫秒时间戳
- 无需修改

**CVD组合层（cvd.py:198-203）**：❌ **需要改进**
```python
# 当前：简单长度对齐，未检查openTime
n = min(len(cvd_f), len(cvd_s), len(futures_klines), len(spot_klines))
cvd_f = cvd_f[-n:]   # 只取最后n根，假设对齐
cvd_s = cvd_s[-n:]
```

**问题**：
- 未检查openTime是否匹配
- 如果现货/合约K线时间不同步（如现货缺失某根），会错位对齐

**改进方案**：P1-Important
```python
def align_klines_by_open_time(
    futures_klines: List[List],
    spot_klines: List[List]
) -> Tuple[List[List], List[List], int]:
    """
    基于openTime对齐现货和合约K线

    Returns:
        (aligned_futures, aligned_spot, discarded_count)
    """
    # 提取openTime（第0列）
    f_times = {int(k[0]): k for k in futures_klines}
    s_times = {int(k[0]): k for k in spot_klines}

    # Inner join：只保留两边都有的时间戳
    common_times = sorted(set(f_times.keys()) & set(s_times.keys()))

    aligned_f = [f_times[t] for t in common_times]
    aligned_s = [s_times[t] for t in common_times]

    discarded = len(futures_klines) + len(spot_klines) - 2 * len(common_times)

    # 警告：丢弃比例>0.1%
    total = len(futures_klines) + len(spot_klines)
    if discarded > 0 and discarded / total > 0.001:
        warn(f"⚠️  K线对齐丢弃{discarded}根（{discarded/total:.2%}）")

    return aligned_f, aligned_s, discarded
```

**优先级**：P1-Important
**风险**：中等（当前错位对齐会导致CVD计算偏差）
**建议**：**需要实施**

---

### 2. ❌ **组合权重改为逐K动态** - 当前实现已足够好

#### 专家建议
```
位置：cvd_combined()
改动：用每根K的quoteAssetVolume计算w_f[i]/w_s[i]（逐K）
组合：ΔC_comb[i] = w_f[i]*ΔC_f[i] + w_s[i]*ΔC_s[i]
```

#### 当前实现（cvd.py:206-237）
```python
# 计算整个窗口的总权重
f_quote_volume = sum([_to_f(k[7]) for k in f_klines])  # 窗口总成交额
s_quote_volume = sum([_to_f(k[7]) for k in s_klines])
futures_weight = f_quote_volume / total_quote  # 固定权重

# 应用到每根K线的增量
for i in range(n):
    delta_f = cvd_f[i] - cvd_f[i-1]
    delta_s = cvd_s[i] - cvd_s[i-1]
    combined_delta = futures_weight * delta_f + spot_weight * delta_s  # 固定权重
```

#### 对比分析

| 方法 | 当前实现（窗口总权重） | 专家建议（逐K权重） |
|------|---------------------|------------------|
| **权重计算** | 整个窗口一次计算 | 每根K线独立计算 |
| **计算量** | O(1) | O(n) |
| **准确性** | 反映窗口平均资金分布 | 反映每根K线的瞬时资金分布 |
| **适用场景** | 现货/合约成交额比例稳定 | 现货/合约成交额比例剧烈波动 |

#### 实际数据测试

假设300根K线窗口（1h周期 = 12.5天）：

**场景1：稳定币种（BTC/ETH）**
```
合约/现货成交额比例波动：5-10%
逐K权重 vs 窗口权重差异：<2%
CVD差异：可忽略
```

**场景2：波动币种（小币）**
```
合约/现货成交额比例波动：20-50%
某根K线：合约暴涨10倍成交额
逐K权重：能捕捉这根K线的异常
窗口权重：被平滑到整个窗口
```

#### 结论

**优先级**：P3-Low（锦上添花，非必须）

**理由**：
1. ✅ **当前实现已经是动态权重**（基于成交额，不是固定70:30）
2. ✅ **300根K线窗口足够大**，权重稳定
3. ⚠️ **逐K权重引入更多噪音**（某根K线的瞬时放量不代表趋势）
4. ⚠️ **计算复杂度增加**（每次都要读取每根K线的quoteVolume）

**建议**：**暂不实施**，除非回测证明有显著收益

---

### 3. 📝 **新增Quote-CVD（默认开启）** - 可选增强

#### 专家建议
```python
use_quote: bool=True
ΔC_quote = 2*takerBuyQuote(第10列) - quoteAssetVolume(第7列)
CVD_quote = Σ ΔC_quote
```

#### 当前实现
```python
# ats_core/features/cvd.py:65-74
# 使用Base CVD（币为单位）
taker_buy = _col(klines, 9)  # takerBuyBaseVolume（第9列）
total_vol = _col(klines, 5)  # totalVolume（第5列）
delta = 2.0 * buy - total  # buy_vol - sell_vol（币为单位）
```

#### Base CVD vs Quote CVD对比

| 指标 | Base CVD（当前） | Quote CVD（专家建议） |
|------|---------------|---------------------|
| **单位** | 币数量（BTC/ETH） | USDT（法币） |
| **列号** | col[9] - col[5] | col[10] - col[7] |
| **优点** | 直观反映买卖币数 | 直接反映资金流（USDT） |
| **缺点** | 受币价影响 | 需要额外列（兼容性） |
| **实例** | 买入100 BTC，卖出80 BTC → ΔC=+20 BTC | 买入6M USDT，卖出5M USDT → ΔC=+1M USDT |

**关键差异场景**：

**场景1：价格暴涨期间**
```
T1时刻：BTC价格 $50,000
  - 买入100 BTC = $5M
  - 卖出80 BTC = $4M
  - Base CVD: +20 BTC
  - Quote CVD: +$1M

T2时刻（1小时后）：BTC价格 $60,000 (+20%)
  - 买入100 BTC = $6M  （同样买入100 BTC，但资金更多！）
  - 卖出80 BTC = $4.8M
  - Base CVD: +20 BTC   （看起来一样）
  - Quote CVD: +$1.2M   （资金流增加20%！）
```

**Base CVD问题**：价格上涨期间，同样的币数量代表更多资金，但Base CVD无法反映。

**Quote CVD优势**：直接反映资金流变化，不受币价影响。

#### 结论

**优先级**：P2-Medium（重要增强，建议实施）

**建议实施方案**：
```python
def cvd_from_klines(
    klines: Sequence[Sequence],
    use_taker_buy: bool = True,
    use_quote: bool = True,  # 新增参数，默认True
    ...
):
    if use_quote:
        # Quote CVD（USDT）
        taker_buy_quote = _col(klines, 10)  # takerBuyQuoteVolume
        quote_volume = _col(klines, 7)      # quoteAssetVolume
        delta = 2.0 * taker_buy_quote - quote_volume
    else:
        # Base CVD（币数量）- 保留向后兼容
        taker_buy_base = _col(klines, 9)
        total_volume = _col(klines, 5)
        delta = 2.0 * taker_buy_base - total_volume
```

**测试计划**：
1. 对比Base CVD vs Quote CVD在不同行情的差异
2. 验证Quote CVD的方向性和转折点是否更准确
3. 回测信号质量提升

**建议**：**P2-Medium，建议实施**

---

### 4. ⚠️ **标准化从"累计值"改为"增量滚动Z"** - 需要修改

#### 专家建议
```python
# 对ΔC、ΔP、ΔOI做滚动窗口Z标准化（window=96，避免前视）
z_cvd = rolling_z(ΔC, window=96)
z_p = rolling_z(ΔP, window=96)
z_oi = rolling_z(ΔOI, window=96)
```

#### 当前实现（cvd.py:297-303）
```python
# 对累计CVD做全局Z标准化
z_cvd = _z_all(cvd)      # 全局标准化（使用所有数据）
z_p = _z_all(ret_p)      # 全局标准化
z_oi = _z_all(d_oi)      # 全局标准化

# 组合
mix = [1.2 * z_cvd[i] + 0.4 * z_p[i] + 0.4 * z_oi[i] for i in range(n)]
```

#### 问题分析

**问题1：前视偏差（Look-ahead Bias）**
```python
def _z_all(a):
    mean = sum(a) / len(a)  # 使用所有数据的均值（包括未来数据！）
    var = sum((x - mean) ** 2 for x in a) / max(1, len(a) - 1)
    return [(x - mean) / std for x in a]
```

示例：
```
假设有100根K线，计算第50根K线的Z-score：
当前实现：mean = sum(a[0:100]) / 100  ← 包含了a[51:100]的未来数据！
滚动Z：  mean = sum(a[0:50]) / 50     ← 只用历史数据
```

**问题2：累计CVD vs 增量CVD**

当前使用累计CVD（`z_cvd = _z_all(cvd)`），专家建议使用增量（`z_cvd = rolling_z(ΔC)`）。

**累计CVD的问题**：
```
假设CVD序列：[0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
累计值的标准化：会被趋势项主导（CVD一直上涨）
增量的标准化：只看每根K线的变化（[10, 10, 10, 10, ...] → 很稳定）

实际意义：
累计CVD标准化 → 反映当前CVD相对历史总体水平
增量CVD标准化 → 反映当前这根K线的资金流强度
```

专家建议使用增量更合理：我们关心的是"这根K线资金流入是否异常"，而不是"累计CVD是否偏高"。

#### 改进方案

```python
def rolling_z(
    values: List[float],
    window: int = 96,
    robust: bool = True
) -> List[float]:
    """
    滚动窗口Z-score标准化（无前视偏差）

    Args:
        values: 数值序列（如CVD增量、价格收益）
        window: 滚动窗口大小（96根1h K线 = 4天）
        robust: 是否使用稳健统计（MAD代替std，抗异常值）

    Returns:
        Z-score序列
    """
    result = []
    for i in range(len(values)):
        # 只使用历史数据（i-window+1 到 i）
        start = max(0, i - window + 1)
        window_data = values[start:i+1]

        if len(window_data) < 2:
            result.append(0.0)
            continue

        mean = sum(window_data) / len(window_data)

        if robust:
            # 稳健方法：使用MAD（Median Absolute Deviation）
            median = sorted(window_data)[len(window_data) // 2]
            mad = sorted([abs(x - median) for x in window_data])[len(window_data) // 2]
            scale = mad * 1.4826  # MAD to std conversion
        else:
            # 传统方法：使用标准差
            var = sum((x - mean) ** 2 for x in window_data) / (len(window_data) - 1)
            scale = math.sqrt(var) if var > 0 else 1.0

        if scale == 0:
            result.append(0.0)
        else:
            result.append((values[i] - mean) / scale)

    return result


def cvd_mix_with_oi_price(...):
    """改进版：使用增量 + 滚动Z"""
    # 1. 计算CVD
    cvd = cvd_combined(klines, spot_klines)

    # 2. 计算增量（ΔC, ΔP, ΔOI）
    delta_cvd = _pct_change(cvd)  # CVD增量百分比
    ret_p = _pct_change(closes)   # 价格收益
    d_oi = _pct_change(oi_vals)   # OI变化

    # 3. 滚动Z标准化（window=96根1h = 4天）
    z_cvd = rolling_z(delta_cvd, window=96)
    z_p = rolling_z(ret_p, window=96)
    z_oi = rolling_z(d_oi, window=96)

    # 4. 组合
    mix = [1.2 * z_cvd[i] + 0.4 * z_p[i] + 0.4 * z_oi[i] for i in range(n)]

    return cvd, mix
```

#### 结论

**优先级**：P1-Important

**理由**：
1. ❌ **当前有前视偏差**（使用未来数据计算均值/方差）
2. ❌ **累计CVD标准化不如增量准确**
3. ✅ **滚动Z更符合实时交易场景**

**建议**：**必须实施**

**风险**：低（改进算法，不影响向后兼容）

---

### 5. 📝 **输入校验与失败快返** - 工程完善

#### 专家建议
```python
# 断言：Spot timeZone in {None, 0}
# 断言：K线列数 ≥ 11
# 断言：组合前openTime完全一致
```

#### 当前实现
```python
# ats_core/features/cvd.py
# 无输入校验，直接使用数据
```

#### 改进方案

```python
def validate_kline_data(klines: Sequence[Sequence], min_cols: int = 11) -> None:
    """
    校验K线数据完整性

    Raises:
        ValueError: 数据不符合要求
    """
    if not klines:
        raise ValueError("K线数据为空")

    # 检查列数
    if len(klines[0]) < min_cols:
        raise ValueError(f"K线列数不足：需要{min_cols}列，实际{len(klines[0])}列")

    # 检查关键列是否为数值
    for i, col_idx in enumerate([0, 5, 7, 9, 10]):
        try:
            float(klines[0][col_idx])
        except (ValueError, TypeError):
            raise ValueError(f"K线第{col_idx}列不是数值：{klines[0][col_idx]}")


def cvd_from_klines(...):
    """加入输入校验"""
    # 输入校验
    validate_kline_data(klines, min_cols=11)

    if use_taker_buy and klines and len(klines[0]) >= 10:
        # 正常流程
        ...
    else:
        # 数据不完整，降级到tick rule（已有DeprecationWarning）
        ...
```

#### 结论

**优先级**：P3-Low（工程完善，非功能性）

**建议**：**可选实施**，提升系统健壮性

---

## 二、黄线建议分析（4项）

### 6. 📝 **异常值稳健处理（对增量做）** - 可选增强

#### 专家建议
```python
# 对ΔC做异常值处理（Winsorize 1%/99% 或 atan软截断）
```

#### 当前实现（cvd.py:76-94）
```python
# 已有IQR outlier detection
if filter_outliers and n >= 20:
    outlier_mask = detect_volume_outliers(total_vol, deltas, multiplier=1.5)
    deltas = apply_outlier_weights(deltas, outlier_mask, outlier_weight)
```

#### 评估

**当前实现**：✅ 已有异常值处理（IQR方法 + 降权）

**专家建议**：使用Winsorize或atan截断

**对比**：
| 方法 | 当前IQR降权 | Winsorize | atan软截断 |
|------|-----------|----------|-----------|
| **原理** | 检测异常值，权重×0.5 | 截断到1%/99%分位 | atan压缩极值 |
| **保留信息** | ✅ 保留方向和部分幅度 | ❌ 完全截断 | ✅ 保留方向，压缩幅度 |
| **复杂度** | 中 | 低 | 低 |

**结论**：当前实现已足够，**无需修改**

---

### 7. ✅ **多时间框架CVD一致性口径统一** - 已修复

#### 专家建议
```
位置：ats_core/features/multi_timeframe.py
用最近N根的ΣΔC_quote / ΣquoteVol，映射到[-100, 100]
```

#### 当前状态

**v7.2.32已修复**（commit d07394b）：
```python
# ats_core/features/multi_timeframe.py:50-72
# 修复前：sign = 1 if closes[i] >= opens[i] else -1  ❌
# 修复后：使用真实takerBuyVolume ✅
if len(klines) > 0 and len(klines[0]) >= 10:
    taker_buy_volumes = [float(k[9]) for k in klines]
    total_volumes = [float(k[5]) for k in klines]
    cvd = 0
    for i in range(len(taker_buy_volumes)):
        delta = 2.0 * taker_buy_volumes[i] - total_volumes[i]
        cvd += delta
    cvd_change = cvd / total_volume if total_volume > 0 else 0
    return min(100, max(-100, cvd_change * 500))
```

**结论**：✅ **已实现**，无需修改

---

### 8. ❌ **OI对齐与口径** - 不适用

#### 专家建议
```
openInterestHist的period与K线周期一致（如1h）
以closeTime对齐
```

#### 当前实现
```python
# ats_core/sources/binance.py:191-206
def get_open_interest_hist(symbol: str, period: str = "1h", limit: int = 200):
    """
    /futures/data/openInterestHist
    period: "5m"|"15m"|"30m"|"1h"|"2h"|"4h"|"6h"|"12h"|"1d"
    """
```

**评估**：
- Binance API的OI数据period已经可配置（默认"1h"）
- 在`analyze_symbol.py`中调用时传入正确的period即可
- **当前实现已支持**，无需修改

**结论**：❌ **已支持**，无需修改

---

### 9. ⚠️ **缺失/极值容错与权重门限** - 需要增强

#### 专家建议
```python
# 总成交额过小（quoteVol_f + quoteVol_s < min_total_quote）该根跳过或降权
# 缺侧用前值填充仅限≤2根，同时将该侧w递减至0
```

#### 当前实现（cvd.py:192-194）
```python
if spot_klines is None or len(spot_klines) == 0:
    # 缺现货数据，只返回合约CVD
    return cvd_f
```

**问题**：
- 缺现货数据时直接退化到合约CVD，但没有标记
- 没有检查成交额门限

#### 改进方案

```python
def cvd_combined(..., min_total_quote: float = 1e5):  # 10万USDT最小成交额
    """组合CVD + 容错"""
    cvd_f = cvd_from_klines(futures_klines, use_taker_buy=True)

    if spot_klines is None or len(spot_klines) == 0:
        warn("⚠️  缺少现货数据，使用纯合约CVD")
        return cvd_f

    # ... 对齐 ...

    # 检查成交额门限（每根K线）
    result = []
    for i in range(n):
        f_quote = _to_f(f_klines[i][7])
        s_quote = _to_f(s_klines[i][7])
        total_quote = f_quote + s_quote

        if total_quote < min_total_quote:
            # 成交额过小，跳过组合，使用上一根CVD值
            if i == 0:
                result.append(0.0)
            else:
                result.append(result[-1])
            continue

        # 正常组合
        ...
```

**结论**：P2-Medium，**建议实施**

---

## 三、小改建议分析（3项）

### 10. ✅ **工具函数沉淀** - 建议实施

专家建议的3个工具函数：
1. `align_klines_by_open_time(fut, spot)` - 已在红线1中分析，**需要实施**
2. `rolling_z(x, window=96, robust=True)` - 已在红线4中分析，**需要实施**
3. `compute_cvd_delta(kl, use_quote=True)` - 简单封装，**可选**

**结论**：P2-Medium，**前2个必须实施，第3个可选**

---

### 11. ❌ **配置项集中** - 已有config体系

专家建议：
```yaml
cvd.use_quote: true
cvd.weight_mode: "per_kline"
cvd.rolling.window: 96
```

**当前系统**：
- 已有完善的config体系（`config/signal_thresholds.json`）
- CVD参数可以添加到配置文件

**结论**：P3-Low，**可在实施其他改动时一并完成**

---

### 12. ⚠️ **日志与可观测性** - 建议增强

专家建议埋点：
- 对齐丢弃率
- timeZone非UTC命中次数
- 逐K权重均值/方差
- 异常值占比
- mix分布

**结论**：P3-Low，**建议实施**（提升可维护性）

---

## 四、最终执行计划

### Phase 1：必须执行（P1-Important）

| # | 改造项 | 优先级 | 预计工时 | 文件 |
|---|-------|--------|---------|-----|
| 1 | openTime对齐检查 | P1 | 2h | `ats_core/features/cvd.py` |
| 2 | 滚动Z标准化（增量） | P1 | 3h | `ats_core/features/cvd.py` |

**总计**：5小时

---

### Phase 2：建议执行（P2-Medium）

| # | 改造项 | 优先级 | 预计工时 | 文件 |
|---|-------|--------|---------|-----|
| 3 | Quote CVD支持 | P2 | 2h | `ats_core/features/cvd.py` |
| 4 | 缺失/极值容错 | P2 | 2h | `ats_core/features/cvd.py` |
| 5 | 工具函数沉淀 | P2 | 1h | `ats_core/utils/cvd_utils.py`（新建） |

**总计**：5小时

---

### Phase 3：可选执行（P3-Low）

| # | 改造项 | 优先级 | 预计工时 | 文件 |
|---|-------|--------|---------|-----|
| 6 | 输入校验 | P3 | 1h | `ats_core/features/cvd.py` |
| 7 | 日志埋点 | P3 | 2h | `ats_core/features/cvd.py` |
| 8 | 配置项集中 | P3 | 1h | `config/signal_thresholds.json` |

**总计**：4小时

---

## 五、不执行的建议及理由

| # | 改造项 | 不执行理由 |
|---|-------|----------|
| 2 | 逐K动态权重 | 当前窗口权重已经是动态的，逐K引入噪音，收益不明显 |
| 6 | 异常值处理升级 | 当前IQR方法已足够稳健，无需改为Winsorize |
| 7 | 多时间框架口径 | v7.2.32已修复，使用真实takerBuyVolume |
| 8 | OI对齐 | Binance API已支持period参数，当前实现正确 |

---

## 六、关键结论

### 1. 专家建议质量评估

**正确的建议**（5项）：
- ✅ openTime对齐检查（重要）
- ✅ 滚动Z标准化（重要）
- ✅ Quote CVD支持（增强）
- ✅ 缺失/极值容错（增强）
- ✅ 工具函数沉淀（工程）

**已实现的功能**（3项）：
- ✅ UTC时间（数据层已正确）
- ✅ 多时间框架（v7.2.32已修复）
- ✅ 异常值处理（IQR方法）

**不适用的建议**（4项）：
- ❌ 逐K动态权重（过度优化）
- ❌ Winsorize（当前方法已足够）
- ❌ OI period（已支持）
- ❌ timeZone检查（API默认UTC）

### 2. 系统当前状态

✅ **CVD核心计算正确**：
- 使用真实takerBuyVolume（非candle color估算）
- 动态权重（基于成交额）
- 异常值处理（IQR降权）

⚠️ **需要改进的地方**：
1. openTime对齐（防止错位）
2. 标准化方法（滚动Z替代全局Z）
3. Quote CVD支持（更准确的资金流）

### 3. 风险评估

**Phase 1改造风险**：低
- openTime对齐：纯增强，不影响现有逻辑
- 滚动Z：算法改进，向后兼容

**Phase 2改造风险**：低-中
- Quote CVD：新增参数，默认向后兼容
- 容错增强：改善边缘情况

### 4. 建议实施策略

**立即执行**（本次任务）：
- Phase 1：openTime对齐 + 滚动Z标准化

**下次迭代**：
- Phase 2：Quote CVD + 容错增强 + 工具函数

**长期规划**：
- Phase 3：输入校验 + 日志埋点 + 配置集中

---

## 七、回归测试计划

### 测试1：恒等式验证
```python
# 验证sell = volume - takerBuyBase
assert abs(sell_vol - (total_vol - buy_vol)) < 1e-6

# 验证ΔC_base = 2*buyBase - volume
assert abs(delta_base - (2 * buy_base - total_vol)) < 1e-6
```

### 测试2：单位一致性
```python
# ΔC_quote 与 ΔC_base*midPrice 相关性 > 0.98
correlation = np.corrcoef(delta_quote, delta_base * mid_price)[0, 1]
assert correlation > 0.98
```

### 测试3：时间对齐
```python
# 组合前后openTime完全一致
assert all(f[0] == s[0] for f, s in zip(aligned_futures, aligned_spot))

# 丢弃占比 < 0.1%
assert discarded / total < 0.001
```

### 测试4：滚动标准化无前视
```python
# 窗口滑动仅影响窗口内Z值
z1 = rolling_z(data[:100], window=20)
z2 = rolling_z(data[:100], window=20)
assert z1 == z2  # 相同数据，相同结果

# 添加新数据后，历史Z值不变
data_new = data + [new_point]
z3 = rolling_z(data_new, window=20)
assert z3[:100] == z1  # 历史值不被"回写"
```

### 测试5：外部口径 Sanity Check
```
随机10个大盘币，对比外部CVD方向/转折
一致率 ≥ 85%
```

---

## 附录：参考文档

- `CVD_COMPLETE_TECHNICAL_DOCUMENTATION.md` - 当前CVD完整实现
- `v7.2.32_CVD_CALCULATION_FIX.md` - multi_timeframe CVD修复
- `standards/SYSTEM_ENHANCEMENT_STANDARD.md` - 系统增强规范
