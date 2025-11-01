# 选币机制优化：多空对称 + 波动率优先

## 📋 版本信息

- **优化日期**: 2025-11-01
- **版本**: v6.2
- **修改文件**: `ats_core/pipeline/batch_scan_optimized.py`
- **影响范围**: 批量扫描器选币逻辑

---

## ❌ 旧版问题分析

### 问题1：做多偏向严重

**旧逻辑**（v6.1及之前）：
```python
# 仅按24h成交额排序
symbols = sorted(
    all_symbols,
    key=lambda s: volume_map.get(s, 0),  # quoteVolume
    reverse=True
)[:200]
```

**问题**：
- 成交额高的币种往往是**上涨的币种**（买盘推高成交额）
- 下跌币种因流动性流出，成交额排名靠后
- **结果**：200个币中，上涨币可能占70%+，严重忽视做空机会

### 问题2：忽略波动率

**现象**：
- BTC、ETH等主流币成交额大但波动小（日波动±2-5%）
- 某些中小币成交额中等但波动大（日波动±10-30%）
- **结果**：选中的币种信号稀疏，浪费算力

### 问题3：策略能力浪费

- 四门系统本身是**多空双向**策略
- 但选币池偏向做多，导致做空信号稀缺
- **结果**：浪费了50%的策略能力

---

## ✅ 新版解决方案

### 核心思路

**多空对称 + 波动率优先 + 流动性保障**

```python
# 综合评分公式
volatility_score = abs(priceChangePercent)  # 多空对称（绝对值）
liquidity_score = quoteVolume / max_volume  # 归一化流动性
final_score = volatility_score * 0.7 + liquidity_score * 0.3  # 波动率占70%
```

### 实现逻辑（v6.2）

```python
# 1. 获取24h行情（包含涨跌幅）
ticker_map = {}
for ticker in ticker_24h:
    ticker_map[symbol] = {
        'volume': float(ticker.get('quoteVolume', 0)),
        'change_pct': float(ticker.get('priceChangePercent', 0))  # ⬅️ 新增
    }

# 2. 流动性预过滤（保证能成交）
filtered_symbols = [
    s for s in all_symbols
    if ticker_map.get(s, {}).get('volume', 0) >= 3_000_000  # 3M USDT
]

# 3. 综合评分排序
def calc_score(symbol):
    data = ticker_map.get(symbol, {})
    volatility = abs(data.get('change_pct', 0))  # 多空对称（绝对值）
    liquidity = data.get('volume', 0) / max_volume  # 归一化
    return volatility * 0.7 + liquidity * 0.3 * 100  # 波动率主导

symbols = sorted(filtered_symbols, key=calc_score, reverse=True)[:200]
```

---

## 🎯 设计原理

### 1. 多空对称

**关键**：使用 `abs(priceChangePercent)`

| 币种 | 24h涨跌 | 旧评分（成交额） | 新评分（abs波动率） |
|------|---------|------------------|---------------------|
| BTCUSDT | +3% | 5000M → 高 | 3% → 中 |
| ETHUSDT | +2% | 3000M → 高 | 2% → 低 |
| PEPEUSDT | **-15%** | 500M → 低 | **15% → 高** ⬅️ 做空机会 |
| APEUSDT | **+12%** | 400M → 低 | **12% → 高** ⬅️ 做多机会 |

**结果**：
- 旧版：PEPE因成交额低被忽略（错失做空机会）
- 新版：PEPE和APE因高波动率被选中（多空均衡）

### 2. 波动率优先

**权重分配**：
- **波动率 70%**：决定交易机会的多少
- **流动性 30%**：保障订单能成交

**示例对比**：

| 币种 | 波动率 | 成交额 | 旧排名 | 新排名 | 说明 |
|------|--------|--------|--------|--------|------|
| BTCUSDT | 2% | 5000M | #1 | #50 | 主流币：高流动性但低波动 |
| ORDIUSDT | 18% | 800M | #15 | #3 | 高波动币：机会多但流动性中等 |
| XXXUSDT | 25% | 50M | #100 | #80 | 超高波动：但流动性太低（30%权重降低排名）|

**结论**：
- 既不会只选低波动的主流币（浪费算力）
- 也不会选到流动性极差的币（无法成交）

### 3. 流动性保障

**两层保障**：
1. **硬过滤**：成交额 < 3M USDT 的直接排除
2. **软权重**：成交额占30%评分权重

**防止极端情况**：
```python
# 场景：某币波动率100%，但成交额只有10K USDT
volatility_score = 100 * 0.7 = 70
liquidity_score = (10K / 5000M) * 0.3 * 100 = 0.006  # 几乎为0
final_score = 70.006  # 无法进入TOP 200
```

---

## 📊 预期效果对比

### 旧版（v6.1）：成交额排序

```
TOP 10 可能是：
1. BTCUSDT    (+2.1%)  5000M USDT  ⬅️ 波动小
2. ETHUSDT    (+1.8%)  3000M USDT  ⬅️ 波动小
3. SOLUSDT    (+3.5%)  1500M USDT
4. BNBUSDT    (+1.2%)  1200M USDT  ⬅️ 波动小
5. DOGEUSDT   (+4.2%)  1000M USDT
...

多空分布：上涨150个 / 下跌50个（3:1偏向做多）
```

### 新版（v6.2）：波动率优先

```
TOP 10 可能是：
1. PEPEUSDT   (-18.5%)  800M USDT  ⬅️ 做空机会
2. ORDIUSDT   (+15.2%)  600M USDT  ⬅️ 做多机会
3. APEUSDT    (-12.8%)  500M USDT  ⬅️ 做空机会
4. SOLUSDT    (+11.5%)  1500M USDT ⬅️ 做多机会
5. INJUSDT    (+10.1%)  450M USDT  ⬅️ 做多机会
...

多空分布：上涨100个 / 下跌100个（1:1均衡）
```

---

## 🚀 性能影响

### API调用次数：无增加

- 旧版：`get_ticker_24h()` 1次
- 新版：`get_ticker_24h()` 1次 ✅ 无变化

### 计算复杂度：O(n) → O(n)

- 旧版：构建字典 O(n) + 排序 O(n log n)
- 新版：构建字典 O(n) + 排序 O(n log n) ✅ 无变化

### 内存占用：轻微增加

- 旧版：`volume_map` 存储1个float/币种
- 新版：`ticker_map` 存储2个float/币种（volume + change_pct）
- 增加：~200币种 × 8字节 = 1.6KB ✅ 可忽略

**结论**：速度零影响 ✅

---

## 📈 日志输出优化

### 新增监控指标

```python
# 1. 多空分布统计
log(f"   多空分布: 上涨{up_count}个 / 下跌{down_count}个（做多做空机会均衡）")

# 2. 波动率范围
log(f"   波动率范围: 12.5% ~ 3.2%")

# 3. 成交额范围（保留）
log(f"   成交额范围: 1200.0M ~ 3.5M USDT")
```

**监控价值**：
- **多空分布**：监控选币是否均衡（理想值接近1:1）
- **波动率范围**：了解当前市场活跃度
- **成交额范围**：确认流动性充足

---

## 🔧 参数调优

### 可调参数

```python
# 1. 波动率权重（当前70%）
VOLATILITY_WEIGHT = 0.7  # 提高→更激进，降低→更保守

# 2. 流动性权重（当前30%）
LIQUIDITY_WEIGHT = 0.3  # 提高→偏向主流币，降低→偏向小币

# 3. 最低流动性（当前3M USDT）
MIN_VOLUME = 3_000_000  # 提高→更安全，降低→更多选择

# 4. 选币数量（当前200）
TOP_N = 200  # 提高→更多覆盖，降低→更精准
```

### 调优建议

**如果做空信号仍然太少**：
```python
# 方案1：增加选币数量
TOP_N = 250  # 200 → 250

# 方案2：降低流动性要求
MIN_VOLUME = 2_000_000  # 3M → 2M

# 方案3：进一步提高波动率权重
VOLATILITY_WEIGHT = 0.8  # 0.7 → 0.8
LIQUIDITY_WEIGHT = 0.2   # 0.3 → 0.2
```

**如果滑点太大（流动性不足）**：
```python
# 提高流动性要求和权重
MIN_VOLUME = 5_000_000    # 3M → 5M
LIQUIDITY_WEIGHT = 0.4    # 0.3 → 0.4
VOLATILITY_WEIGHT = 0.6   # 0.7 → 0.6
```

---

## ✅ 验证方法

### 部署后检查

```bash
# 1. 查看多空分布（应接近1:1）
grep "多空分布" logs/scanner_*.log | tail -5

# 示例输出：
# 多空分布: 上涨105个 / 下跌95个（做多做空机会均衡）✅

# 2. 查看波动率范围（应>5%）
grep "波动率范围" logs/scanner_*.log | tail -5

# 示例输出：
# 波动率范围: 18.5% ~ 3.2% ✅

# 3. 统计做空信号数量
grep "SHORT" logs/scanner_*.log | wc -l
```

### 24小时后统计

```bash
# 对比做多/做空信号比例
echo "做多信号:"
grep "LONG" logs/scanner_*.log | wc -l

echo "做空信号:"
grep "SHORT" logs/scanner_*.log | wc -l

# 理想比例：接近1:1或根据市场趋势略有偏差
```

---

## 📚 相关文档

- **实现文件**: `ats_core/pipeline/batch_scan_optimized.py` (lines 106-170)
- **系统规范**: `standards/SYSTEM_OVERVIEW.md` § 数据层
- **开发规范**: `standards/MODIFICATION_RULES.md`

---

## 🔄 版本历史

| 版本 | 日期 | 选币逻辑 | 多空比例 |
|------|------|----------|----------|
| v6.1及之前 | 2025-11-01前 | 成交额排序 | 约3:1（做多偏向）|
| **v6.2** | **2025-11-01** | **波动率70% + 流动性30%** | **约1:1（均衡）** |

---

**文档状态**: ✅ 生效中
**维护人员**: CryptoSignal 开发团队
**最后更新**: 2025-11-01
