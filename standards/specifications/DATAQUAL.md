# DataQual 数据质量监控规范

**规范版本**: v6.4 Phase 2
**生效日期**: 2025-11-02
**状态**: 生效中

> ⚠️ **关键性**: DataQual是四门系统Gate 1，决定信号能否发布
> - **Prime阈值**: DataQual ≥ 0.90
> - **维持阈值**: DataQual ≥ 0.88 (滞回)
> - **降级策略**: DataQual < 0.90 → Watch-only

---

## 📋 目录

1. [总体原则](#1-总体原则)
2. [计算公式](#2-计算公式)
3. [各分量定义](#3-各分量定义)
4. [权重配置](#4-权重配置)
5. [阈值与降级](#5-阈值与降级)
6. [实施细节](#6-实施细节)

---

## 1. 总体原则

### 1.1 设计目标

**数据质量评分目的**:
- 量化数据流的可靠性
- 自动降级不可靠信号
- 保护系统免受数据异常影响

**核心思想**:
```
DataQual = 1 - (加权质量损失)
```
- 完美数据: DataQual = 1.0
- 可接受: DataQual ≥ 0.90
- 降级: 0.88 ≤ DataQual < 0.90 (维持已有仓位)
- 停止: DataQual < 0.88 (不允许交易)

### 1.2 质量维度

DataQual考虑4个维度:
1. **Miss** - 数据缺失率
2. **OO-Order** - 乱序率
3. **Drift** - 时钟漂移率
4. **Mismatch** - 数据不一致率

---

## 2. 计算公式

### 2.1 总公式

```python
DataQual = 1 - (w_miss * miss_rate +
                w_oo * oo_order_rate +
                w_drift * drift_rate +
                w_mismatch * mismatch_rate)
```

**约束**: `DataQual ∈ [0, 1]`

### 2.2 权重配置

| 分量 | 权重 | 符号 | 说明 |
|------|------|------|------|
| **Miss** (缺失) | 0.40 | w_miss | 最严重：影响计算正确性 |
| **OO-Order** (乱序) | 0.25 | w_oo | 严重：影响时序逻辑 |
| **Drift** (漂移) | 0.20 | w_drift | 中等：影响时间精度 |
| **Mismatch** (不一致) | 0.15 | w_mismatch | 较轻：可能是合理差异 |

**总和**: 1.0 ✅

**设计理念**:
- Miss最严重：缺失数据无法计算
- OO次严重：乱序导致逻辑错误
- Drift中等：漂移影响时效性
- Mismatch较轻：不同源可能有小差异

---

## 3. 各分量定义

### 3.1 Miss (数据缺失率)

**定义**: 预期收到但未收到的数据比例

**计算**:
```python
# 时间窗口: 最近N根K线 (N=60，约1小时1h K线)
expected_count = N  # 预期收到N根K线
received_count = len(klines_received)  # 实际收到

miss_count = expected_count - received_count
miss_rate = max(0, miss_count / expected_count)
```

**示例**:
```python
# 1小时内预期60根1m K线
expected = 60
received = 57  # 缺失3根
miss_rate = 3/60 = 0.05 (5%)
```

**阈值**:
- miss_rate < 0.05: 良好
- 0.05 ≤ miss_rate < 0.10: 可接受
- miss_rate ≥ 0.10: 严重 (DataQual必然<0.96)

---

### 3.2 OO-Order (乱序率)

**定义**: 时间戳顺序错误的数据比例

**计算**:
```python
# 检查最近N根K线的时间戳顺序
oo_count = 0
for i in range(1, len(klines)):
    if klines[i]['timestamp'] < klines[i-1]['timestamp']:
        oo_count += 1

oo_order_rate = oo_count / (len(klines) - 1)
```

**示例**:
```python
# 检查60根K线
klines = [
    {'t': 1000, 'close': 100},
    {'t': 1060, 'close': 101},
    {'t': 1050, 'close': 102},  # ❌ 乱序！1050 < 1060
    {'t': 1120, 'close': 103},
]
oo_count = 1
oo_order_rate = 1/59 = 0.017 (1.7%)
```

**阈值**:
- oo_order_rate < 0.01: 良好
- 0.01 ≤ oo_order_rate < 0.03: 可接受
- oo_order_rate ≥ 0.03: 严重

---

### 3.3 Drift (时钟漂移率)

**定义**: 数据时间戳与系统时钟的偏差比例

**计算**:
```python
# 检查最新K线的时间戳
latest_kline_time = klines[-1]['timestamp']
current_system_time = get_current_timestamp()

# 预期延迟: 1个K线周期 + 网络延迟 (例如1m K线 + 3秒)
expected_delay = kline_period + network_tolerance  # 60s + 3s = 63s

actual_delay = current_system_time - latest_kline_time
drift = abs(actual_delay - expected_delay)

# 漂移率: 超出容忍的比例
drift_rate = min(1.0, drift / drift_tolerance)  # drift_tolerance = 10s
```

**示例**:
```python
# 1m K线，3秒网络延迟，10秒漂移容忍
current_time = 1730000000  # 当前时间
latest_kline_time = 1729999920  # 最新K线时间

actual_delay = 80s  # 1730000000 - 1729999920
expected_delay = 63s  # 60s + 3s
drift = 17s  # |80 - 63|

drift_rate = 17/10 = 1.7 → clip to 1.0 (100% 严重漂移)
```

**阈值**:
- drift < 5s: 良好
- 5s ≤ drift < 10s: 可接受
- drift ≥ 10s: 严重 (drift_rate = 1.0)

**参数配置**:
```python
drift_params = {
    "1m": {"expected_delay": 63, "tolerance": 10},
    "5m": {"expected_delay": 303, "tolerance": 20},
    "15m": {"expected_delay": 903, "tolerance": 30},
    "1h": {"expected_delay": 3603, "tolerance": 60},
    "4h": {"expected_delay": 14403, "tolerance": 120},
}
```

---

### 3.4 Mismatch (数据不一致率)

**定义**: 不同数据源之间的差异比例

**计算**:
```python
# 比较REST API和WebSocket的同一根K线
rest_close = rest_kline['close']
ws_close = ws_kline['close']

# 相对误差
mismatch = abs(rest_close - ws_close) / rest_close

# 不一致率: 超出容忍的比例
mismatch_rate = min(1.0, mismatch / mismatch_tolerance)  # tolerance = 0.001 (0.1%)
```

**示例**:
```python
# REST和WebSocket的同一根K线
rest_close = 50000.00
ws_close = 50005.00

mismatch = |50005 - 50000| / 50000 = 0.0001 (0.01%)
mismatch_tolerance = 0.001 (0.1%)

mismatch_rate = 0.0001 / 0.001 = 0.1 (10%的容忍度被使用)
```

**阈值**:
- mismatch < 0.05%: 良好
- 0.05% ≤ mismatch < 0.1%: 可接受
- mismatch ≥ 0.1%: 严重

**检查项**:
1. REST vs WebSocket (同一K线的close价格)
2. 1h K线 vs 4*15m K线聚合 (volume一致性)
3. OI数据 vs K线数据时间戳对齐

---

## 4. 权重配置

### 4.1 标准权重 (生产环境)

```python
dataqual_weights = {
    "w_miss": 0.40,       # 缺失最严重
    "w_oo": 0.25,         # 乱序次严重
    "w_drift": 0.20,      # 漂移中等
    "w_mismatch": 0.15,   # 不一致较轻
}
```

**总和**: 1.0 ✅

### 4.2 权重调整策略

**场景1: 高频交易**
```python
# 对时钟漂移更敏感
dataqual_weights_hft = {
    "w_miss": 0.35,
    "w_oo": 0.30,
    "w_drift": 0.25,     # ⬆️ 提高
    "w_mismatch": 0.10,
}
```

**场景2: 低频交易**
```python
# 可容忍更多漂移
dataqual_weights_lft = {
    "w_miss": 0.45,      # ⬆️ 提高（缺失更重要）
    "w_oo": 0.25,
    "w_drift": 0.15,     # ⬇️ 降低
    "w_mismatch": 0.15,
}
```

**场景3: 新币通道**
```python
# 数据源不稳定，放宽mismatch
dataqual_weights_newcoin = {
    "w_miss": 0.40,
    "w_oo": 0.30,        # ⬆️ 提高（新币更易乱序）
    "w_drift": 0.20,
    "w_mismatch": 0.10,  # ⬇️ 降低（新币数据源差异大）
}
```

---

## 5. 阈值与降级

### 5.1 DataQual阈值

| 级别 | 阈值 | 行为 | 说明 |
|------|------|------|------|
| **优秀** | ≥ 0.95 | 正常Prime | 数据质量优秀 |
| **良好** | 0.90-0.95 | 正常Prime | 数据质量良好 |
| **可接受** | 0.88-0.90 | 维持仓位 | 不开新仓，保持已有仓位 |
| **警告** | 0.85-0.88 | Watch-only | 只发Watch信号，不交易 |
| **严重** | < 0.85 | 停止 | 停止所有操作 |

### 5.2 滞回机制 (防抖动)

**目的**: 避免DataQual在阈值附近频繁跳变

**开仓阈值** (更严格):
```python
can_open_position = (DataQual >= 0.90)
```

**维持阈值** (放宽):
```python
can_maintain_position = (DataQual >= 0.88)
```

**示例**:
```python
# 情况1: DataQual从0.92降到0.89
# 行为: 不开新仓，但保持已有仓位 ✅

# 情况2: DataQual从0.89降到0.87
# 行为: 关闭所有仓位，发Watch信号 ⚠️

# 情况3: DataQual从0.87升到0.89
# 行为: 仍然Watch-only，需升到0.90才能开仓 ✅
```

### 5.3 冷却期

**质量恢复冷却**: DataQual恢复到0.90后，等待N根K线再允许交易

```python
cooldown_bars = 3  # 等待3根K线（约3分钟）

if DataQual >= 0.90:
    if bars_since_recovery < cooldown_bars:
        signal_type = "Watch"  # 仍然Watch
    else:
        signal_type = "Prime"  # 恢复Prime
```

---

## 6. 实施细节

### 6.1 数据采集

**采集频率**: 每根K线更新一次

**数据窗口**: 最近60根K线（约1小时）

**数据源**:
```python
# REST API (对账基准)
rest_klines = binance.get_klines(symbol, interval="1h", limit=60)

# WebSocket (实时流)
ws_klines = ws_cache.get_klines(symbol, interval="1h", limit=60)
```

### 6.2 计算流程

```python
def calculate_dataqual(symbol: str, interval: str) -> Dict:
    """
    计算DataQual

    Returns:
        {
            "dataqual": float,  # 0-1
            "miss_rate": float,
            "oo_order_rate": float,
            "drift_rate": float,
            "mismatch_rate": float,
            "can_publish_prime": bool,
            "reason": str
        }
    """
    # 1. 获取最近60根K线
    klines = get_recent_klines(symbol, interval, limit=60)

    # 2. 计算各分量
    miss_rate = calculate_miss_rate(klines, expected_count=60)
    oo_order_rate = calculate_oo_order_rate(klines)
    drift_rate = calculate_drift_rate(klines, interval)
    mismatch_rate = calculate_mismatch_rate(symbol, interval)

    # 3. 加权聚合
    weights = get_dataqual_weights(interval)
    dataqual = 1 - (
        weights["w_miss"] * miss_rate +
        weights["w_oo"] * oo_order_rate +
        weights["w_drift"] * drift_rate +
        weights["w_mismatch"] * mismatch_rate
    )

    # 4. 判断是否可发布
    can_publish = (dataqual >= 0.90)
    reason = get_failure_reason(dataqual, miss_rate, oo_order_rate,
                                 drift_rate, mismatch_rate) if not can_publish else "OK"

    return {
        "dataqual": dataqual,
        "miss_rate": miss_rate,
        "oo_order_rate": oo_order_rate,
        "drift_rate": drift_rate,
        "mismatch_rate": mismatch_rate,
        "can_publish_prime": can_publish,
        "reason": reason
    }
```

### 6.3 失败原因诊断

```python
def get_failure_reason(dataqual, miss, oo, drift, mismatch):
    """诊断DataQual失败的主要原因"""
    reasons = []

    if miss > 0.10:
        reasons.append(f"数据缺失严重 ({miss:.1%})")
    elif miss > 0.05:
        reasons.append(f"数据缺失 ({miss:.1%})")

    if oo > 0.03:
        reasons.append(f"数据乱序严重 ({oo:.1%})")
    elif oo > 0.01:
        reasons.append(f"数据乱序 ({oo:.1%})")

    if drift > 10:
        reasons.append(f"时钟漂移严重 ({drift}s)")
    elif drift > 5:
        reasons.append(f"时钟漂移 ({drift}s)")

    if mismatch > 0.001:
        reasons.append(f"数据不一致严重 ({mismatch:.2%})")
    elif mismatch > 0.0005:
        reasons.append(f"数据不一致 ({mismatch:.2%})")

    if not reasons:
        return f"DataQual={dataqual:.3f} < 0.90"

    return " + ".join(reasons)
```

### 6.4 监控与告警

**监控指标**:
```python
metrics = {
    "dataqual_current": 0.92,           # 当前DataQual
    "dataqual_1h_avg": 0.94,            # 1小时平均
    "dataqual_24h_avg": 0.96,           # 24小时平均
    "degraded_symbols_count": 2,         # 降级币种数
    "miss_rate_p50": 0.02,              # Miss中位数
    "miss_rate_p95": 0.08,              # Miss 95分位
    "oo_order_rate_p95": 0.01,          # 乱序 95分位
    "drift_seconds_p95": 5.2,           # 漂移 95分位
}
```

**告警规则**:
```yaml
- alert: DataQualDegraded
  expr: dataqual < 0.90
  for: 5m
  severity: warning
  message: "DataQual降级 ({{ $value }}), 币种: {{ $labels.symbol }}"

- alert: DataQualCritical
  expr: dataqual < 0.85
  for: 1m
  severity: critical
  message: "DataQual严重 ({{ $value }}), 已停止交易"

- alert: HighMissRate
  expr: miss_rate > 0.10
  for: 3m
  severity: warning
  message: "数据缺失率过高 ({{ $value }})"
```

---

## 7. 配置示例

### 7.1 config/params.json

```json
{
  "dataqual": {
    "weights": {
      "w_miss": 0.40,
      "w_oo": 0.25,
      "w_drift": 0.20,
      "w_mismatch": 0.15
    },
    "thresholds": {
      "prime_min": 0.90,
      "maintain_min": 0.88,
      "warning_min": 0.85
    },
    "tolerances": {
      "miss_rate_max": 0.10,
      "oo_order_rate_max": 0.03,
      "drift_seconds_max": 10,
      "mismatch_rate_max": 0.001
    },
    "cooldown_bars": 3,
    "window_size": 60
  }
}
```

---

## 8. 实现模块

**代码位置**: `ats_core/data/quality.py`

**核心类**:
```python
class DataQualMonitor:
    def __init__(self, config: Dict):
        self.weights = config["dataqual"]["weights"]
        self.thresholds = config["dataqual"]["thresholds"]
        # ...

    def calculate_quality(self, symbol: str, interval: str) -> DataQualResult:
        """计算DataQual"""
        pass

    def can_publish_prime(self, symbol: str) -> Tuple[bool, float, str]:
        """判断是否可发布Prime信号"""
        pass

    def get_quality_report(self, symbol: str) -> Dict:
        """获取质量诊断报告"""
        pass
```

---

## 9. 测试与验证

### 9.1 单元测试

```python
def test_dataqual_perfect_data():
    """测试完美数据"""
    result = calculate_dataqual(
        miss_rate=0.0,
        oo_order_rate=0.0,
        drift_rate=0.0,
        mismatch_rate=0.0
    )
    assert result["dataqual"] == 1.0
    assert result["can_publish_prime"] == True

def test_dataqual_high_miss():
    """测试高缺失率"""
    result = calculate_dataqual(
        miss_rate=0.15,  # 15% 缺失
        oo_order_rate=0.0,
        drift_rate=0.0,
        mismatch_rate=0.0
    )
    # DataQual = 1 - (0.40 * 0.15) = 0.94
    assert result["dataqual"] == 0.94
    assert result["can_publish_prime"] == True  # 仍然 >= 0.90

def test_dataqual_threshold():
    """测试阈值边界"""
    result = calculate_dataqual(
        miss_rate=0.10,
        oo_order_rate=0.10,
        drift_rate=0.10,
        mismatch_rate=0.10
    )
    # DataQual = 1 - (0.40*0.10 + 0.25*0.10 + 0.20*0.10 + 0.15*0.10)
    #          = 1 - 0.10 = 0.90
    assert result["dataqual"] == 0.90
    assert result["can_publish_prime"] == True  # 刚好 >= 0.90
```

### 9.2 集成测试

```python
def test_dataqual_gate_integration():
    """测试与四门系统集成"""
    gates_checker = FourGatesChecker()

    # 模拟DataQual = 0.89 (低于阈值)
    result = gates_checker.check_gate1_dataqual(symbol="BTCUSDT")

    assert result.passed == False
    assert result.value == 0.89
    assert result.threshold == 0.90
```

---

## 10. 相关文档

- **四门系统**: [GATES.md](GATES.md)
- **发布规范**: [PUBLISHING.md](PUBLISHING.md)
- **数据层**: [DATA_LAYER.md](DATA_LAYER.md)
- **WebSocket管理**: [WEBSOCKET.md](WEBSOCKET.md) (待创建)

---

**规范版本**: v6.4-phase2-dataqual
**维护**: 数据质量团队
**审核**: 系统架构师
**最后更新**: 2025-11-02
