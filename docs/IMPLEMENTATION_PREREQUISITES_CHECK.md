# 四步系统实施前置条件检查报告
# Implementation Prerequisites Check Report

**检查日期**: 2025-11-16
**检查范围**: 10个因子 + 数据依赖 + 专家方案需求

---

## 📊 核心结论

### ✅ 已完成部分

1. **10个因子全部实现** ✅
2. **主流程存在** ✅
3. **配置系统完善** ✅

### ⚠️ 需要补充的部分

1. **factor_scores_series** (7小时因子序列) ⚠️ **未实现**
2. **S因子ZigZag元数据导出** ⚠️ **缺失zigzag_points**
3. **订单薄分析** ⚠️ **未实现** (符合专家"占位"策略)

---

## 1. 十因子实现状态详查

### ✅ A层因子 (6个) - 全部已实现

| 因子 | 文件路径 | 状态 | 返回格式 | 备注 |
|------|---------|------|---------|------|
| **T** (趋势) | `ats_core/features/trend.py` | ✅ 已实现 | `(T_score, meta)` | 10KB, score_trend() |
| **M** (动量) | `ats_core/features/momentum.py` | ✅ 已实现 | `(M_score, meta)` | 11KB, score_momentum() |
| **C** (CVD流) | `ats_core/features/cvd_flow.py` | ✅ 已实现 | `(C_score, meta)` | 16KB, score_cvd_flow() |
| **V** (量能) | `ats_core/features/volume.py` | ✅ 已实现 | `(V_score, meta)` | 12KB, score_volume() |
| **O** (持仓) | `ats_core/features/open_interest.py` | ✅ 已实现 | `(O_score, meta)` | 21KB, score_open_interest() |
| **B** (基差) | `ats_core/factors_v2/basis_funding.py` | ✅ 已实现 | `(B_score, meta)` | 19KB, score_basis_funding() |

### ✅ B层调制器 (4个) - 全部已实现

| 因子 | 文件路径 | 状态 | 返回格式 | 备注 |
|------|---------|------|---------|------|
| **F** (资金领先) | `ats_core/features/fund_leading.py` | ✅ 已实现 | `(F_score, meta)` | 16KB, score_fund_leading_v2() |
| **S** (结构) | `ats_core/features/structure_sq.py` | ✅ 已实现 | `(S_score, meta)` | 8KB, score_structure() |
| **L** (流动性) | `ats_core/features/liquidity_priceband.py` | ✅ 已实现 | `(L_score, meta)` | 16KB, score_liquidity_priceband() |
| **I** (独立性) | `ats_core/factors_v2/independence.py` | ✅ 已实现 | `(I_score, meta)` | 26KB, score_independence() |

**总结**: 10/10因子已实现 ✅

---

## 2. S因子ZigZag元数据检查

### ⚠️ 问题: zigzag_points未导出

**当前实现** (`structure_sq.py:248-257`):
```python
return S, {
    "theta": th,
    "icr": icr,
    "retr": retr,
    "timing": timing,
    "not_over": (over<=0.8),
    "m15_ok": bool(ctx.get("m15_ok",False)),
    "penalty": penalty,
    "interpretation": interpretation
    # ⚠️ 缺少: "zigzag_points": [...]
}
```

**专家方案需要的格式**:
```python
{
    "zigzag_points": [
        {"type": "L", "price": 98.5, "dt": 5},
        {"type": "H", "price": 103.2, "dt": 4},
        {"type": "L", "price": 99.8, "dt": 2},
        {"type": "H", "price": 104.5, "dt": 1},
    ],
    ...
}
```

**ZigZag已计算但未导出**:
- `_zigzag_last()` 函数已实现 (lines 67-110) ✅
- ZigZag结果存储在变量`zz`中 (line 187) ✅
- **但meta中未包含zigzag_points** ⚠️

**修复方法**:
```python
# 在返回语句前添加ZigZag点转换
zigzag_points = []
for i, (kind, price, dt) in enumerate(zz):
    zigzag_points.append({
        "type": kind,      # "H" or "L"
        "price": price,
        "dt": len(c) - dt  # 转换为距当前的K线数
    })

return S, {
    "theta": th,
    ...
    "zigzag_points": zigzag_points,  # ✅ 新增
    ...
}
```

---

## 3. factor_scores_series (历史因子序列)

### ⚠️ 问题: 未实现历史因子序列保存

**专家方案需要**:
```python
factor_scores_series: List[Dict[str, float]]
# 示例: 过去7小时的因子得分
[
    {"T": 25, "M": 10, "C": 80, "V": 35, "O": 60, "B": 15},  # 6小时前
    {"T": 28, "M": 12, "C": 82, "V": 38, "O": 62, "B": 18},  # 5小时前
    ...
    {"T": 35, "M": 20, "C": 90, "V": 45, "O": 70, "B": 25}   # 当前
]
```

**用途**: Step2计算Enhanced F Factor需要
```python
flow_momentum = calculate_flow_momentum(
    factor_scores_series,  # ← 需要这个7小时序列
    flow_weights
)
```

**当前状态**:
- `analyze_symbol.py`只计算当前时刻的factor_scores ⚠️
- 没有保存历史因子序列 ⚠️

**实现方案**:

方案A: **实时计算** (推荐)
```python
def get_factor_scores_series(symbol, klines_1h):
    """
    实时计算过去7小时的因子得分序列

    参数:
        klines_1h: 至少24根1h K线 (为计算因子提供足够数据)

    返回:
        factor_scores_series: List[Dict[str, float]], 长度=7
    """
    series = []

    # 对过去7小时，每小时计算一次因子
    for i in range(-7, 0):
        # 取该时刻之前的所有K线作为输入
        klines_window = klines_1h[:i] if i < -1 else klines_1h

        # 计算该时刻的因子 (复用现有函数)
        factor_scores = {
            "T": calculate_T(klines_window),
            "M": calculate_M(klines_window),
            "C": calculate_C(klines_window),
            "V": calculate_V(klines_window),
            "O": calculate_O(klines_window),
            "B": calculate_B(klines_window),
        }
        series.append(factor_scores)

    return series
```

方案B: **缓存保存** (更高效但复杂)
```python
# 将每小时的factor_scores保存到数据库/缓存
# 读取时直接获取最近7条
# 优点: 避免重复计算
# 缺点: 需要额外存储和维护
```

**建议**: 先用方案A实时计算，后续优化可改为方案B

---

## 4. 订单薄分析

### ✅ 符合专家"占位"策略

**专家方案原文**:
> "本版只放占位...将真实实现推迟到以后一个版本。"

**占位函数** (专家方案已提供):
```python
def analyze_orderbook_placeholder(symbol: str, exchange: str) -> dict:
    """占位版本 - 后续替换为真实实现"""
    return {
        "buy_wall_price": None,
        "sell_wall_price": None,
        "buy_depth_score": 50.0,
        "sell_depth_score": 50.0,
        "imbalance": 0.0,
    }
```

**Step3中的降级处理** (专家方案已考虑):
```python
buy_wall = (orderbook or {}).get("buy_wall_price")
if buy_wall and entry < buy_wall:
    entry = buy_wall * 1.001  # 只在有数据时调整
```

**结论**:
- ✅ 订单薄未实现是预期内的
- ✅ 专家方案已有占位和降级逻辑
- ⏸️ 可在后续版本实现真实订单薄分析

---

## 5. BTC因子数据

### ⚠️ 需要确认: BTC因子计算

**专家方案需要**:
```python
btc_factor_scores: Dict[str, float]
# 至少需要:
{
    "T": float  # BTC趋势因子
}
```

**用途**: Step1方向确认
```python
btc_direction_score = btc_factor_scores.get("T", 0.0)
btc_trend_strength = abs(btc_direction_score)
```

**需要确认**:
1. 当前系统是否已计算BTC的因子？
2. 如果没有，需要在主流程中添加BTC因子计算

**实现方法**:
```python
# 在analyze_symbol()中添加
btc_klines = get_klines("BTCUSDT", "1h", limit=168)
btc_factor_scores = {
    "T": calculate_T(btc_klines)[0],  # 只需要T因子
}
```

---

## 6. 主流程集成点检查

### ✅ 主流程文件存在

**文件**: `ats_core/pipeline/analyze_symbol.py`
- ✅ 1755行: `def analyze_symbol(symbol: str)`
- ✅ 计算所有10个因子
- ✅ 返回完整结果字典

**集成方式** (按专家方案):
```python
def analyze_symbol(symbol: str) -> Dict[str, Any]:
    # ... 现有逻辑 ...

    # 计算所有因子 (现有)
    factor_scores = {...}

    # ✅ 新增: 检查是否启用四步系统
    if params.get("four_step_system", {}).get("enabled", False):
        # 准备数据
        factor_scores_series = get_factor_scores_series(symbol, k1h)
        btc_factor_scores = get_btc_factors()

        # 调用四步系统
        from ats_core.decision.four_step_system import run_four_step_decision
        result = run_four_step_decision(
            symbol=symbol,
            exchange="binance",
            klines=k1h,
            factor_scores=factor_scores,
            factor_scores_series=factor_scores_series,
            btc_factor_scores=btc_factor_scores,
            s_factor_meta=s_meta,
            prime_strength=prime_strength,
            params=params,
        )

        # 处理结果
        if result["decision"] == "ACCEPT":
            # 生成信号 (包含具体价格)
            ...
    else:
        # 旧系统逻辑 (保持不变)
        ...
```

---

## 7. 配置系统检查

### ✅ 配置文件存在

**文件**: `config/params.json`
- ✅ 现有因子权重配置
- ⚠️ 需要添加`four_step_system`配置块

**需要添加** (专家方案第7节):
```json
{
  "four_step_system": {
    "enabled": false,  // ← 默认关闭，先测试
    "step1": {...},
    "step2": {...},
    "step3": {...},
    "step4": {...}
  }
}
```

---

## 8. 实施前准备工作清单

### 🔧 必须完成的工作 (P0)

1. **补充S因子ZigZag导出** (预计: 0.5小时)
   ```python
   # 修改 ats_core/features/structure_sq.py
   # 在返回meta中添加 "zigzag_points": zigzag_points
   ```

2. **实现factor_scores_series计算** (预计: 2小时)
   ```python
   # 新文件: ats_core/utils/factor_history.py
   # 函数: get_factor_scores_series(symbol, klines, window=7)
   ```

3. **添加BTC因子计算** (预计: 1小时)
   ```python
   # 在 analyze_symbol.py 中添加
   # btc_factor_scores = calculate_btc_factors()
   ```

4. **添加配置块** (预计: 0.5小时)
   ```bash
   # 编辑 config/params.json
   # 添加 four_step_system 配置
   ```

**小计**: ~4小时准备工作

### ✅ 可选的工作 (P1-P2)

1. **订单薄真实实现** (预计: 20-30小时)
   - 暂时使用占位函数
   - 后续版本再实现 ✅

2. **factor_scores_series缓存优化** (预计: 8小时)
   - 先用实时计算
   - 性能有问题再优化 ✅

---

## 9. 实施路径建议

### 阶段0: 准备工作 (4小时) ← **当前阶段**

1. ✅ 补充S因子ZigZag导出
2. ✅ 实现factor_scores_series计算
3. ✅ 添加BTC因子计算
4. ✅ 添加配置块

### 阶段1: Step1+2实现 (24小时)

按照专家方案`FOUR_STEP_IMPLEMENTATION_GUIDE.md`执行

### 阶段2: Step3+4实现 (16小时)

### 阶段3: 集成测试 (8小时)

**总计**: 4 + 24 + 16 + 8 = **52小时**

---

## 10. 风险提示

### 🔴 高风险项

1. **factor_scores_series计算成本**
   - 每次都计算7小时历史可能很慢
   - 建议: 先实现，性能测试后再优化

2. **BTC数据依赖**
   - 如果BTC数据获取失败怎么办？
   - 建议: 加降级处理 (使用默认值)

### 🟡 中风险项

1. **S因子meta格式变更**
   - 添加zigzag_points可能影响现有逻辑
   - 建议: 保持向后兼容，只是新增字段

2. **配置块冲突**
   - four_step_system配置可能和现有配置冲突
   - 建议: 独立命名空间

### 🟢 低风险项

1. **订单薄占位**
   - 专家方案已有降级逻辑 ✅

2. **向后兼容**
   - 通过enabled开关控制 ✅

---

## ✅ 最终结论

### 可以开始实施吗？

**答案**: ✅ **可以，但需要先完成4小时准备工作**

### 准备工作优先级

**P0 (必须)**:
1. S因子ZigZag导出 (0.5h)
2. factor_scores_series实现 (2h)
3. BTC因子计算 (1h)
4. 配置块添加 (0.5h)

**总计**: 4小时

### 完成准备工作后

✅ 所有前置条件满足
✅ 可以按专家方案8步checklist执行
✅ 预计52小时完成全部实施

---

**建议**:
1. 先完成4小时准备工作
2. 提交一个commit "feat(P0): 四步系统前置条件准备"
3. 然后开始阶段1 (Step1+2实现)
