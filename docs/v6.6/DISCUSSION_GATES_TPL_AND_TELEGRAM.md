# v6.6 四门系统、止盈止损与电报消息讨论

**版本**: v6.6 Final
**日期**: 2025-11-03
**状态**: 待用户确认

---

## 第一部分：四门系统内化的影响分析

### 1.1 用户关切

**问题**：移除独立的四门系统，逻辑内化到analyze_symbol.py，会不会影响信号质量或者过滤高质量信号？

### 1.2 当前四门系统架构

**文件**: `ats_core/gates/integrated_gates.py`

```
FourGatesChecker.check_all_gates():
  ├─ Gate1: DataQual >= 0.90
  ├─ Gate2: EV > 0
  ├─ Gate3: Execution (spread/impact/OBI)
  └─ Gate4: Probability (P >= p_min, ΔP >= Δp_min)
```

**调用位置**: `scripts/realtime_signal_scanner.py`

```python
# 在analyze_symbol之后调用
checker = FourGatesChecker()
passes, gate_results = checker.check_all_gates(
    symbol, probability, exec_metrics, F_raw, I_raw, delta_p, is_newcoin
)

if not passes:
    # 拒绝发布
    logger.info(f"四门未通过: {gate_results}")
    continue
```

### 1.3 内化方案设计

**方案A：完全内化（激进）**

```python
# analyze_symbol.py
def _analyze_symbol_core(...):
    # Step 0: 数据质量检查（原Gate1）
    dataqual = dataqual_monitor.get_quality(symbol)
    if dataqual < 0.90:
        return {
            "success": False,
            "reject_reason": "DataQual < 0.90",
            "dataqual": dataqual
        }

    # ... 计算因子、edge、概率 ...

    # Step N-2: EV检查（原Gate2）
    EV = calculate_ev(P, cost_eff)
    if EV <= 0:
        return {
            "success": False,
            "reject_reason": "EV <= 0",
            "EV": EV
        }

    # Step N-1: 执行质量检查（原Gate3）
    if spread_bps > 25 or impact_bps > 7 or abs(OBI) > 0.3:
        return {
            "success": False,
            "reject_reason": f"Execution failed: spread={spread_bps:.1f}bps",
            "spread_bps": spread_bps,
            "impact_bps": impact_bps,
            "OBI": OBI
        }

    # Step N: 概率阈值检查（原Gate4）
    if P < p_min or abs(delta_P) < delta_p_min:
        return {
            "success": False,
            "reject_reason": f"P={P:.1%} < {p_min:.1%}",
            "P": P,
            "p_min": p_min
        }

    # 通过所有检查
    return {
        "success": True,
        "signal": {...},
        "gates_passed": {"gate1": True, "gate2": True, "gate3": True, "gate4": True}
    }
```

**方案B：保留独立模块但简化（保守）**

```python
# ats_core/gates/simple_gates.py
def check_publishing_gates(
    dataqual: float,
    EV: float,
    spread_bps: float,
    impact_bps: float,
    OBI: float,
    P: float,
    p_min: float,
    delta_P: float,
    delta_p_min: float
) -> Tuple[bool, Dict[str, bool], str]:
    """
    简化的四门检查（单函数）

    Returns:
        (all_passed, gates_dict, reject_reason)
    """
    gates = {
        "dataqual": dataqual >= 0.90,
        "ev": EV > 0,
        "execution": spread_bps <= 25 and impact_bps <= 7 and abs(OBI) <= 0.3,
        "probability": P >= p_min and abs(delta_P) >= delta_p_min
    }

    all_passed = all(gates.values())

    # 生成拒绝原因
    if not all_passed:
        failed = [k for k, v in gates.items() if not v]
        reject_reason = f"Gates failed: {', '.join(failed)}"
    else:
        reject_reason = ""

    return all_passed, gates, reject_reason
```

### 1.4 影响对比分析

| 维度 | 当前架构 | 方案A（完全内化） | 方案B（简化独立） |
|------|---------|-----------------|-----------------|
| **代码行数** | ~300行 | analyze_symbol.py +50行 | ~50行 |
| **调用开销** | 2次函数调用（checker + modulate） | 0次额外调用 | 1次函数调用 |
| **信号质量** | ✅ 保证 | ✅ **完全一致**（逻辑不变） | ✅ 保证 |
| **调试难度** | 🟡 中（需跨文件） | 🟢 低（单文件追踪） | 🟡 中 |
| **可扩展性** | 🟢 好（独立模块） | 🔴 差（耦合在analyze中） | 🟢 好 |
| **测试复杂度** | 🟢 低（独立测试） | 🔴 高（需模拟完整流程） | 🟢 低 |

### 1.5 信号质量不受影响的证明

**关键点**：内化只是**重新组织代码**，不改变**检查逻辑**

**当前逻辑**：
```
analyze_symbol() → 返回P, EV, spread等
↓
FourGatesChecker.check_all_gates(P, EV, spread, ...) → True/False
↓
if True: 发布
if False: 拒绝
```

**内化后逻辑**：
```
analyze_symbol() → 内部检查P, EV, spread
  if 不通过: return {"success": False, "reject_reason": ...}
  if 通过: return {"success": True, "signal": ...}
↓
if success: 发布
if not success: 拒绝
```

**数学等价性**：
- 检查条件完全相同：`dataqual >= 0.90`, `EV > 0`, `spread <= 25`, `P >= p_min`
- 检查顺序可调整（优化：早期退出）
- **拒绝率不变，信号质量不变**

### 1.6 推荐方案

**推荐：方案B（简化独立模块）**

**理由**：
1. **保留模块化**：四门检查作为独立模块，易于测试和扩展
2. **简化实现**：单函数替代复杂类，减少开销
3. **信号质量保证**：逻辑不变，拒绝率不变
4. **降低风险**：不改动analyze_symbol（核心计算逻辑），减少引入bug的风险

**实施**：
- 创建 `ats_core/gates/simple_gates.py`
- 实现 `check_publishing_gates()` 单函数
- realtime_signal_scanner.py 调用简化函数
- 移除 `integrated_gates.py` 的复杂类

**代码示例**（完整实现）：

```python
# ats_core/gates/simple_gates.py

from typing import Tuple, Dict

def check_publishing_gates(
    dataqual: float,
    EV: float,
    spread_bps: float,
    impact_bps: float,
    OBI: float,
    P: float,
    p_min: float,
    delta_P: float,
    delta_p_min: float,
    is_newcoin: bool = False
) -> Tuple[bool, Dict[str, bool], str]:
    """
    简化的四门发布检查

    Args:
        dataqual: 数据质量 [0, 1]
        EV: 期望值
        spread_bps: 点差（基点）
        impact_bps: 冲击成本（基点）
        OBI: 订单簿失衡度 [-1, 1]
        P: 概率
        p_min: 最小概率阈值
        delta_P: 概率变化
        delta_p_min: 最小概率变化阈值
        is_newcoin: 是否新币（使用更宽松的执行阈值）

    Returns:
        (all_passed, gates_dict, reject_reason)
    """
    # 执行阈值（新币vs标准）
    if is_newcoin:
        spread_threshold = 40.0
        impact_threshold = 15.0
        obi_threshold = 0.40
    else:
        spread_threshold = 25.0
        impact_threshold = 7.0
        obi_threshold = 0.30

    # 四门检查
    gates = {
        "gate1_dataqual": dataqual >= 0.90,
        "gate2_ev": EV > 0,
        "gate3_execution": (
            spread_bps <= spread_threshold and
            impact_bps <= impact_threshold and
            abs(OBI) <= obi_threshold
        ),
        "gate4_probability": P >= p_min and abs(delta_P) >= delta_p_min
    }

    all_passed = all(gates.values())

    # 生成详细的拒绝原因
    if not all_passed:
        failed_reasons = []
        if not gates["gate1_dataqual"]:
            failed_reasons.append(f"DataQual={dataqual:.2%} < 90%")
        if not gates["gate2_ev"]:
            failed_reasons.append(f"EV={EV:.2%} <= 0")
        if not gates["gate3_execution"]:
            exec_details = []
            if spread_bps > spread_threshold:
                exec_details.append(f"spread={spread_bps:.1f}>{spread_threshold}bps")
            if impact_bps > impact_threshold:
                exec_details.append(f"impact={impact_bps:.1f}>{impact_threshold}bps")
            if abs(OBI) > obi_threshold:
                exec_details.append(f"|OBI|={abs(OBI):.2f}>{obi_threshold}")
            failed_reasons.append(f"Execution({', '.join(exec_details)})")
        if not gates["gate4_probability"]:
            prob_details = []
            if P < p_min:
                prob_details.append(f"P={P:.1%}<{p_min:.1%}")
            if abs(delta_P) < delta_p_min:
                prob_details.append(f"|ΔP|={abs(delta_P):.1%}<{delta_p_min:.1%}")
            failed_reasons.append(f"Probability({', '.join(prob_details)})")

        reject_reason = " | ".join(failed_reasons)
    else:
        reject_reason = ""

    return all_passed, gates, reject_reason


# 使用示例（在realtime_signal_scanner.py中）
"""
from ats_core.gates.simple_gates import check_publishing_gates

passes, gates, reject_reason = check_publishing_gates(
    dataqual=signal_data["dataqual"],
    EV=signal_data["EV"],
    spread_bps=signal_data["spread_bps"],
    impact_bps=signal_data["impact_bps"],
    OBI=signal_data["OBI"],
    P=signal_data["probability"],
    p_min=signal_data["p_min"],
    delta_P=signal_data["delta_P"],
    delta_p_min=signal_data["delta_p_min"],
    is_newcoin=signal_data["is_newcoin"]
)

if not passes:
    logger.info(f"{symbol} 四门未通过: {reject_reason}")
    continue  # 拒绝发布
"""
```

---

## 第二部分：基于订单簿的止盈止损设计

### 2.1 用户需求

**原始建议**：
- ❌ 不能简单依靠ATR和结构
- ❌ 风险回报比过于简单
- ✅ 应该更多依赖订单簿
- ✅ 或者更好的止盈止损方法

### 2.2 订单簿止损原理

**核心思想**：利用订单簿的**支撑/阻力位**

**做多止损逻辑**：
1. 扫描buy side订单簿，找到**买单聚集区**（累计买单量突然增大的价位）
2. 买单聚集区 = 支撑位
3. 止损设在**支撑位下方** 0.5-1%（击穿支撑才止损）

**做空止损逻辑**：
1. 扫描sell side订单簿，找到**卖单聚集区**（累计卖单量突然增大的价位）
2. 卖单聚集区 = 阻力位
3. 止损设在**阻力位上方** 0.5-1%（突破阻力才止损）

### 2.3 订单簿止盈原理

**做多止盈逻辑**：
1. 扫描sell side订单簿，找到**卖压聚集区**（大量卖单等待成交）
2. 卖压聚集区 = 阻力位 = 价格难以突破的区域
3. 止盈设在**阻力位之前**（在卖压到来前获利离场）

**做空止盈逻辑**：
1. 扫描buy side订单簿，找到**买盘聚集区**
2. 买盘聚集区 = 支撑位 = 价格难以跌破的区域
3. 止盈设在**支撑位之前**（在买盘接盘前获利离场）

### 2.4 聚集区识别算法

**方法1：累计深度突变检测**

```python
def find_support_resistance_levels(
    orderbook: Dict,
    side: str,  # "buy" or "sell"
    depth_levels: int = 50,
    cluster_threshold: float = 2.0  # 累计量突然增加2倍视为聚集区
) -> List[Tuple[float, float]]:
    """
    识别订单簿中的支撑/阻力位

    Args:
        orderbook: 订单簿数据 {"bids": [[price, qty], ...], "asks": [...]}
        side: "buy" (买单=支撑) or "sell" (卖单=阻力)
        depth_levels: 扫描深度
        cluster_threshold: 聚集阈值

    Returns:
        [(price, cumulative_volume), ...] 聚集区列表
    """
    if side == "buy":
        levels = orderbook["bids"][:depth_levels]
    else:
        levels = orderbook["asks"][:depth_levels]

    if not levels:
        return []

    # 计算累计深度
    cumulative = []
    cum_vol = 0.0
    for price, qty in levels:
        cum_vol += float(qty)
        cumulative.append((float(price), cum_vol))

    # 识别突变点（累计量突然增大）
    clusters = []
    for i in range(1, len(cumulative)):
        price_prev, vol_prev = cumulative[i-1]
        price_curr, vol_curr = cumulative[i]

        # 检查累计量增速
        delta_vol = vol_curr - vol_prev
        avg_vol_per_level = vol_prev / i if i > 0 else 1.0

        if delta_vol > cluster_threshold * avg_vol_per_level:
            # 发现聚集区
            clusters.append((price_curr, vol_curr))

    return clusters
```

**方法2：密度聚类（更精确）**

```python
def find_density_clusters(
    orderbook: Dict,
    side: str,
    depth_levels: int = 50,
    min_cluster_size: float = 100.0  # 最小聚集量（USDT）
) -> List[Tuple[float, float, float]]:
    """
    基于密度聚类识别支撑/阻力位

    Returns:
        [(center_price, total_volume, price_range), ...] 聚集区中心、总量、范围
    """
    if side == "buy":
        levels = orderbook["bids"][:depth_levels]
    else:
        levels = orderbook["asks"][:depth_levels]

    if not levels:
        return []

    # 计算每个价位的USDT深度
    depth_usdt = []
    for price, qty in levels:
        price_f = float(price)
        qty_f = float(qty)
        usdt_vol = price_f * qty_f
        depth_usdt.append((price_f, usdt_vol))

    # 使用滑动窗口识别聚集区
    window_size = 5  # 5个价位为一组
    clusters = []

    for i in range(len(depth_usdt) - window_size + 1):
        window = depth_usdt[i:i+window_size]

        # 窗口内总量
        total_vol = sum(vol for _, vol in window)

        if total_vol >= min_cluster_size:
            # 计算加权中心价格
            price_center = sum(p * vol for p, vol in window) / total_vol
            price_min = window[0][0]
            price_max = window[-1][0]
            price_range = abs(price_max - price_min)

            clusters.append((price_center, total_vol, price_range))

    # 去重和合并相近的聚集区
    merged_clusters = []
    if clusters:
        clusters_sorted = sorted(clusters, key=lambda x: x[1], reverse=True)  # 按量排序
        merged_clusters.append(clusters_sorted[0])

        for cluster in clusters_sorted[1:]:
            center, vol, rng = cluster

            # 检查是否与已有聚集区重叠
            is_duplicate = False
            for existing in merged_clusters:
                ex_center, ex_vol, ex_rng = existing
                if abs(center - ex_center) < (rng + ex_rng):
                    # 重叠，跳过
                    is_duplicate = True
                    break

            if not is_duplicate:
                merged_clusters.append(cluster)

    return merged_clusters
```

### 2.5 止损止盈计算

```python
def calculate_stop_loss_take_profit_orderbook(
    side: str,  # "long" or "short"
    entry_price: float,
    orderbook: Dict,
    atr: float,
    params: Dict = None
) -> Dict:
    """
    基于订单簿的止损止盈计算

    Args:
        side: 方向
        entry_price: 入场价
        orderbook: 订单簿
        atr: ATR（用于安全边际）
        params: 参数

    Returns:
        {
            "stop_loss": float,
            "take_profit_1": float,
            "take_profit_2": float,
            "stop_loss_reason": str,
            "take_profit_reason": str,
            "rr_ratio": float
        }
    """
    params = params or {}
    safety_margin_pct = params.get("safety_margin_pct", 0.005)  # 0.5%安全边际
    min_rr_ratio = params.get("min_rr_ratio", 2.0)

    if side == "long":
        # 做多：止损在支撑位下方，止盈在阻力位下方

        # 1. 找支撑位（买单聚集区）
        supports = find_density_clusters(orderbook, "buy", depth_levels=50)

        # 筛选入场价下方的支撑位
        supports_below = [s for s in supports if s[0] < entry_price]

        if supports_below:
            # 选择最强支撑（量最大的）
            strongest_support = max(supports_below, key=lambda x: x[1])
            support_price = strongest_support[0]

            # 止损设在支撑下方（安全边际）
            stop_loss = support_price * (1 - safety_margin_pct)
            sl_reason = f"支撑位{support_price:.2f}下方{safety_margin_pct:.1%}"
        else:
            # 无支撑位，使用ATR止损
            stop_loss = entry_price - 1.5 * atr
            sl_reason = f"无订单簿支撑，使用1.5×ATR"

        # 2. 找阻力位（卖单聚集区）
        resistances = find_density_clusters(orderbook, "sell", depth_levels=50)

        # 筛选入场价上方的阻力位
        resistances_above = [r for r in resistances if r[0] > entry_price]

        if resistances_above:
            # 选择最近的阻力位作为TP1（快速获利）
            resistances_sorted = sorted(resistances_above, key=lambda x: x[0])
            resistance_1 = resistances_sorted[0][0]
            tp1 = resistance_1 * (1 - safety_margin_pct)  # 在阻力前获利
            tp_reason = f"阻力位{resistance_1:.2f}前{safety_margin_pct:.1%}"

            # TP2: 选择第二个阻力位（如果有）
            if len(resistances_sorted) > 1:
                resistance_2 = resistances_sorted[1][0]
                tp2 = resistance_2 * (1 - safety_margin_pct)
            else:
                # 无第二阻力，使用2×RR
                risk = entry_price - stop_loss
                tp2 = entry_price + 2 * risk
        else:
            # 无阻力位，使用固定RR比
            risk = entry_price - stop_loss
            tp1 = entry_price + min_rr_ratio * risk
            tp2 = entry_price + (min_rr_ratio * 1.5) * risk
            tp_reason = f"无订单簿阻力，使用RR={min_rr_ratio}"

    else:  # side == "short"
        # 做空：止损在阻力位上方，止盈在支撑位上方

        # 1. 找阻力位（卖单聚集区）
        resistances = find_density_clusters(orderbook, "sell", depth_levels=50)
        resistances_above = [r for r in resistances if r[0] > entry_price]

        if resistances_above:
            strongest_resistance = max(resistances_above, key=lambda x: x[1])
            resistance_price = strongest_resistance[0]
            stop_loss = resistance_price * (1 + safety_margin_pct)
            sl_reason = f"阻力位{resistance_price:.2f}上方{safety_margin_pct:.1%}"
        else:
            stop_loss = entry_price + 1.5 * atr
            sl_reason = f"无订单簿阻力，使用1.5×ATR"

        # 2. 找支撑位（买单聚集区）
        supports = find_density_clusters(orderbook, "buy", depth_levels=50)
        supports_below = [s for s in supports if s[0] < entry_price]

        if supports_below:
            supports_sorted = sorted(supports_below, key=lambda x: x[0], reverse=True)
            support_1 = supports_sorted[0][0]
            tp1 = support_1 * (1 + safety_margin_pct)
            tp_reason = f"支撑位{support_1:.2f}前{safety_margin_pct:.1%}"

            if len(supports_sorted) > 1:
                support_2 = supports_sorted[1][0]
                tp2 = support_2 * (1 + safety_margin_pct)
            else:
                risk = stop_loss - entry_price
                tp2 = entry_price - 2 * risk
        else:
            risk = stop_loss - entry_price
            tp1 = entry_price - min_rr_ratio * risk
            tp2 = entry_price - (min_rr_ratio * 1.5) * risk
            tp_reason = f"无订单簿支撑，使用RR={min_rr_ratio}"

    # 计算RR比
    risk = abs(entry_price - stop_loss)
    reward = abs(tp1 - entry_price)
    rr_ratio = reward / risk if risk > 0 else 0

    return {
        "stop_loss": round(stop_loss, 2),
        "take_profit_1": round(tp1, 2),
        "take_profit_2": round(tp2, 2),
        "stop_loss_reason": sl_reason,
        "take_profit_reason": tp_reason,
        "rr_ratio": round(rr_ratio, 2)
    }
```

### 2.6 订单簿止损的优势

| 方法 | ATR止损 | 订单簿止损 |
|------|---------|-----------|
| **依据** | 历史波动率 | 实时市场结构 |
| **准确性** | 🟡 中（统计平均） | 🟢 高（真实支撑/阻力） |
| **动态性** | 🔴 低（固定倍数） | 🟢 高（订单簿实时变化） |
| **假突破** | 🔴 易触发（波动大） | 🟢 不易触发（击穿支撑才止损） |
| **计算成本** | 🟢 低 | 🟡 中（需扫描订单簿） |

**实际案例**:

```
场景：BTCUSDT做多
- 入场价：50,000
- ATR: 800 (1.6%)
- ATR止损：50,000 - 1.5×800 = 48,800 (2.4%止损)

订单簿分析：
- 49,200价位：累计买单 500 BTC（强支撑）
- 49,000价位：累计买单 300 BTC（次强支撑）

订单簿止损：49,200 × (1-0.5%) = 48,954 (2.1%止损)

结果：
- ATR止损更保守（2.4%），可能在正常波动中被触发
- 订单簿止损更精确（2.1%），只在击穿强支撑时触发
```

### 2.7 混合方案（推荐）

**结合ATR和订单簿的优势**：

```python
def calculate_stop_loss_hybrid(
    side: str,
    entry_price: float,
    atr: float,
    orderbook: Dict,
    params: Dict = None
) -> Tuple[float, str]:
    """
    混合止损：订单簿优先，ATR兜底

    逻辑：
    1. 尝试使用订单簿识别支撑/阻力
    2. 如果订单簿支撑/阻力合理（在ATR范围内），使用订单簿止损
    3. 如果订单簿支撑/阻力过远（超过3×ATR），使用ATR止损
    4. 如果无订单簿数据，使用ATR止损
    """
    params = params or {}
    atr_mult = params.get("atr_mult", 1.5)
    max_atr_mult = params.get("max_atr_mult", 3.0)

    # 尝试订单簿止损
    ob_result = calculate_stop_loss_take_profit_orderbook(
        side, entry_price, orderbook, atr, params
    )

    ob_stop_loss = ob_result["stop_loss"]
    ob_distance = abs(entry_price - ob_stop_loss)

    # 计算ATR止损
    if side == "long":
        atr_stop_loss = entry_price - atr_mult * atr
    else:
        atr_stop_loss = entry_price + atr_mult * atr

    atr_distance = abs(entry_price - atr_stop_loss)

    # 验证订单簿止损是否合理
    if ob_distance <= max_atr_mult * atr:
        # 订单簿止损合理，使用订单簿
        return ob_stop_loss, f"订单簿支撑/阻力 ({ob_result['stop_loss_reason']})"
    elif ob_distance > 0:
        # 订单簿止损过远，使用较近的那个
        if ob_distance < atr_distance:
            return ob_stop_loss, f"订单簿止损（已限制在{max_atr_mult}×ATR内）"
        else:
            return atr_stop_loss, f"ATR止损（订单簿止损过远 {ob_distance/atr:.1f}×ATR）"
    else:
        # 无订单簿数据，使用ATR
        return atr_stop_loss, f"{atr_mult}×ATR止损（无订单簿数据）"
```

---

## 第三部分：电报消息模板优化

### 3.1 当前模板分析

**文件**: `ats_core/outputs/telegram_fmt.py` (1388行)

**主要函数**：
1. `render_signal()` - 标准10维信号（最常用）
2. `render_signal_detailed()` - 详细模式（调试用）
3. `render_five_piece_report()` - 五段式报告（完整审计）

**当前格式**（标准模式）：

```
🔹 BTCUSDT · 现价 50,125
🟩 做多 概率68% · 有效期8h

━━━━━ 10维因子分析 ━━━━━
• 趋势 🟢 +80 —— 强势上行
• 动量 🟢 +65 —— 强劲上行加速
• 结构 🟡 +45 —— 结构尚可/回踩确认
• 成交 🟢 +60 —— 放量明显/跟随积极
• 资金 🟢 +70 —— 偏强资金流入 (CVD+2.3%, 持续✓)
• 持仓 🟡 +40 —— 持仓温和上升/活跃 (OI+5.2%)
• 流动 🟢 +85 —— 流动性极佳/深度充足 (点差8.5bps, OBI+0.12)
• 情绪 🟡 +35 —— 偏多情绪/期货溢价 (基差+25bps, 费率+0.015%)
• 独立 🟢 +75 —— 高度独立/自主行情 (β=0.35)

📊 大盘环境 🟢 强势趋势 (市场+60)
   └─ BTC+55 · ETH+50

⚡ 资金动量 ✅ 资金领先价格 (F+25)
   └─ 概率调整 ×1.08

#trade #BTCUSDT
```

### 3.2 用户需求

1. ✅ 整体采用 `telegram_fmt.py` 现有模板
2. ✅ 加入"更方便用户的内容"
3. ✅ 修复电报消息模板的基础上优化

### 3.3 优化建议

#### 优化1：添加入场/止损/止盈（已部分实现）

**当前代码**（Line 1163-1195）：
```python
def _pricing_block(r: Dict[str, Any]) -> str:
    """生成价格信息块（入场、止损、止盈）"""
    pricing = _get(r, "pricing") or {}
    if not pricing:
        return ""

    lines = []

    # 入场区间
    entry_lo = pricing.get("entry_lo")
    entry_hi = pricing.get("entry_hi")
    ...
```

**问题**：当前只显示价格，缺少：
- 止损距离百分比
- 风险回报比
- 预期盈亏金额

**优化后**：

```python
def _pricing_block_enhanced(r: Dict[str, Any]) -> str:
    """增强的价格信息块"""
    pricing = _get(r, "pricing") or {}
    if not pricing:
        return ""

    lines = []
    current_price = _get(r, "price") or _get(r, "last")

    # 入场价
    entry = pricing.get("entry_price") or pricing.get("entry_lo")
    if entry:
        lines.append(f"📍 入场价: {_fmt_price(entry)}")
        if current_price:
            entry_slippage_pct = abs(entry - current_price) / current_price * 100
            lines.append(f"   └─ 滑点: {entry_slippage_pct:.2f}%")

    # 止损
    sl = pricing.get("stop_loss") or pricing.get("sl")
    if sl and entry:
        lines.append(f"🛑 止损: {_fmt_price(sl)}")
        sl_dist_pct = abs(sl - entry) / entry * 100
        lines.append(f"   └─ 止损距离: {sl_dist_pct:.2f}%")

        # 预期损失金额（假设1 BTC仓位）
        sl_loss = abs(sl - entry)
        lines.append(f"   └─ 最大损失: {sl_loss:.2f} USDT/BTC")

    # 止盈
    tp1 = pricing.get("take_profit_1") or pricing.get("tp1")
    if tp1 and entry:
        lines.append(f"🎯 止盈1: {_fmt_price(tp1)}")
        tp1_dist_pct = abs(tp1 - entry) / entry * 100
        lines.append(f"   └─ 盈利空间: {tp1_dist_pct:.2f}%")

        tp1_profit = abs(tp1 - entry)
        lines.append(f"   └─ 预期收益: {tp1_profit:.2f} USDT/BTC")

    tp2 = pricing.get("take_profit_2") or pricing.get("tp2")
    if tp2 and entry:
        lines.append(f"🎯 止盈2: {_fmt_price(tp2)}")
        tp2_dist_pct = abs(tp2 - entry) / entry * 100
        lines.append(f"   └─ 盈利空间: {tp2_dist_pct:.2f}%")

    # 风险回报比
    if sl and tp1 and entry:
        risk = abs(entry - sl)
        reward = abs(tp1 - entry)
        if risk > 0:
            rr = reward / risk
            lines.append(f"\n💎 风险回报比: 1:{rr:.2f}")

    # 订单簿止损原因（如果有）
    sl_reason = pricing.get("stop_loss_reason")
    if sl_reason:
        lines.append(f"   └─ {sl_reason}")

    if lines:
        return "\n" + "\n".join(lines)
    return ""
```

#### 优化2：添加仓位建议

```python
def _position_block(r: Dict[str, Any]) -> str:
    """仓位建议块（v6.6新增）"""
    lines = []

    # 仓位倍数（来自L调制器）
    position_mult = _get(r, "modulation.position_mult") or 1.0
    confidence = _get(r, "confidence") or 50

    # 基础仓位（基于置信度）
    # confidence 0-100 → position 0-10%
    base_position_pct = confidence / 10.0  # 例如confidence=70 → 7%

    # 应用L调制器
    final_position_pct = base_position_pct * position_mult

    lines.append(f"\n💼 仓位建议: {final_position_pct:.1f}%")

    if position_mult < 1.0:
        lines.append(f"   └─ 流动性调整: ×{position_mult:.2f} (流动性一般，降低仓位)")
    elif position_mult > 1.0:
        lines.append(f"   └─ 流动性调整: ×{position_mult:.2f} (流动性极佳，可适当加仓)")

    # 仓位分配建议
    lines.append(f"   └─ 入场: {final_position_pct * 0.6:.1f}% (60%仓位)")
    lines.append(f"   └─ 加仓预留: {final_position_pct * 0.4:.1f}% (40%仓位)")

    return "\n".join(lines)
```

#### 优化3：添加关键风险提示

```python
def _risk_alerts(r: Dict[str, Any]) -> str:
    """风险提示块（v6.6新增）"""
    alerts = []

    # 流动性风险
    L = _get(r, "L") or 0
    if L < 0:
        spread_bps = _get(r, "scores_meta.L.spread_bps") or 0
        alerts.append(f"⚠️ 流动性不足：点差{spread_bps:.1f}bps，注意滑点风险")

    # 拥挤度风险
    F = _get(r, "F") or 0
    if F > 60:
        alerts.append(f"⚠️ 市场拥挤：资金费率偏高，注意拥挤风险")

    # 跟随风险
    I = _get(r, "I") or 0
    if I < -30:
        alerts.append(f"⚠️ 高度跟随：与大盘强相关，注意系统性风险")

    # 数据质量风险
    dataqual = _get(r, "data_quality") or 1.0
    if dataqual < 0.95:
        alerts.append(f"⚠️ 数据质量：DataQual={dataqual:.1%}，数据可能不完整")

    # EV低风险
    ev = _get(r, "expected_value") or 0
    if 0 < ev < 0.01:
        alerts.append(f"⚠️ 低期望值：EV={ev:.2%}，收益空间有限")

    if alerts:
        return "\n\n🚨 风险提示\n" + "\n".join(alerts)
    return ""
```

### 3.4 v6.6 最终模板

**整合所有优化**：

```python
def render_signal_v66(r: Dict[str, Any], is_watch: bool = False) -> str:
    """
    v6.6 完整信号模板

    新增内容：
    1. 增强的入场/止损/止盈（带百分比、金额、RR比）
    2. 仓位建议（基于confidence和L调制器）
    3. 关键风险提示
    4. 订单簿止损原因
    """
    l1, l2 = _header_lines(r, is_watch)
    pricing = _pricing_block_enhanced(r)  # 增强版
    ten = _six_block(r)
    position = _position_block(r)  # 新增
    risks = _risk_alerts(r)  # 新增

    body = (
        f"{l1}\n{l2}"
        f"{pricing}"  # 入场/止损/止盈
        f"{position}"  # 仓位建议
        f"\n\n━━━━━ 10维因子分析 ━━━━━\n{ten}"
        f"{risks}"  # 风险提示
        f"\n\n{_note_and_tags(r, is_watch)}"
    )

    return body
```

**效果预览**：

```
🔹 BTCUSDT · 现价 50,125
🟩 做多 概率68% · 有效期8h

📍 入场价: 50,150
   └─ 滑点: 0.05%
🛑 止损: 49,200
   └─ 止损距离: 1.89%
   └─ 最大损失: 950 USDT/BTC
   └─ 订单簿支撑位49,200下方0.5%
🎯 止盈1: 52,100
   └─ 盈利空间: 3.89%
   └─ 预期收益: 1,950 USDT/BTC
🎯 止盈2: 53,500
   └─ 盈利空间: 6.68%

💎 风险回报比: 1:2.05

💼 仓位建议: 6.8%
   └─ 流动性调整: ×1.0 (流动性良好)
   └─ 入场: 4.1% (60%仓位)
   └─ 加仓预留: 2.7% (40%仓位)

━━━━━ 10维因子分析 ━━━━━
• 趋势 🟢 +80 —— 强势上行
...（10维因子）...

🚨 风险提示
⚠️ 市场拥挤：资金费率偏高，注意拥挤风险

#trade #BTCUSDT
```

---

## 第四部分：实施建议

### 4.1 优先级

| 功能 | 优先级 | 工时 | 收益 |
|------|--------|------|------|
| 四门系统简化（方案B） | 🔴 P0 | 2h | 代码简化，性能提升 |
| 订单簿止损算法 | 🔴 P0 | 4h | **核心功能**，提升止损精度 |
| 电报消息优化 | 🟡 P1 | 2h | 用户体验提升 |
| 仓位建议块 | 🟡 P1 | 1h | 实用功能 |
| 风险提示块 | 🟢 P2 | 1h | Nice to have |

### 4.2 实施路线

**Phase 1: 核心功能** (6小时)
1. 实现 `simple_gates.py`（2h）
2. 实现订单簿聚集区识别算法（2h）
3. 实现混合止损计算函数（2h）

**Phase 2: 集成与测试** (3小时)
1. 集成到 `analyze_symbol.py`（1h）
2. 单元测试（1h）
3. 回测验证（1h）

**Phase 3: 用户体验** (3小时)
1. 优化电报消息模板（1h）
2. 添加仓位建议块（1h）
3. 添加风险提示块（1h）

**总计**: 12小时

---

## 第五部分：待确认事项

### 5.1 四门系统

- [ ] 是否同意方案B（简化独立模块）？
- [ ] 是否保留 `integrated_gates.py` 作为备份？

### 5.2 订单簿止损

- [ ] 是否同意混合方案（订单簿优先，ATR兜底）？
- [ ] 订单簿深度扫描层数：50层 or 100层？
- [ ] 聚集区识别方法：累计突变 or 密度聚类？

### 5.3 电报消息

- [ ] 是否添加仓位建议块？
- [ ] 是否添加风险提示块？
- [ ] 是否显示订单簿止损原因？

### 5.4 参数设置

- [ ] 安全边际：0.5% or 1.0%？
- [ ] 最小RR比：2.0 or 2.5？
- [ ] ATR倍数：1.5 or 2.0？

---

**等待用户确认后执行实施计划**
