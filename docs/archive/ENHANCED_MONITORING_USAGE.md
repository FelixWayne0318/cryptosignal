# 增强型监控输出使用指南

## 概述

v6.0增强型监控输出系统提供了完整的因子权重、贡献度、调节器状态、Prime分解和四门验证显示，用于实时监控和深度分析。

## 核心功能

### 1. 详细模式 - `render_signal_detailed()`

完整显示所有指标和权重，适用于：
- 实时监控系统运行状态
- 调试信号质量问题
- 深度分析因子表现

**使用示例**:

```python
from ats_core.outputs.telegram_fmt import render_signal_detailed

# 从analyze_symbol获取结果
result = await analyze_symbol(symbol, data, params)

# 生成详细监控输出
detailed_output = render_signal_detailed(result, is_watch=False)
print(detailed_output)
```

**输出示例**:

```
🔹 BTCUSDT · 现价 42,530
🟩 做多 概率72% · 有效期8h

━━━━━ A层：方向因子 ━━━━━
🟢 趋势 +80 (13.9%) → +11.1  强势上行 [多头]
🟡 动量 +52 (8.3%) → +4.3  温和上行加速
🟡 结构 +45 (5.6%) → +2.5  结构尚可/回踩确认
🟢 量能 +60 (8.3%) → +5.0  放量明显/跟随积极
🟢 资金流 +75 (11.1%) → +8.3  偏强资金流入
🟢 持仓 +68 (11.1%) → +7.5  持仓显著增长/可能拥挤
✅ 资金领先 +45 (10.0%) → +4.5  资金领先价格
🟢 流动性 +72 (11.1%) → +8.0  流动性极佳/深度充足
🟡 基差 +38 (8.3%) → +3.2  偏多情绪/期货溢价
🔵 独立性 +25 (6.7%) → +1.7  中等相关/跟随市场

加权总分: +56

━━━━━ B层：调制器 ━━━━━
✅ F资金领先 +45: 资金领先价格
   └─ 概率调整因子: ×1.00

🔵 I独立性 +25: 中等相关/跟随市场
   └─ p_min: 62.00%（无调整）

━━━━━ D层：四门验证 ━━━━━
✅ Gate1 数据质量: 95.00% ≥ 90%
✅ Gate2 期望值: +2.30% > 0
✅ Gate3 执行成本: 点差8.5bps, 冲击15.0bps
✅ Gate4a 概率阈值: P=72.0% ≥ 62.0%
✅ Gate4b 偏离阈值: ΔP=22.0% ≥ 12.0%

🎉 全部通过

━━━━━ Prime分数分解 ━━━━━
置信度: 72.0
基础强度: 72.0 × 0.6 = 43.2
概率: 72.0%
概率加成: (0.720 - 0.5) × 200 = +44.0
Prime总分: 43.2 + +44.0 = 87.2
最终Prime: 85/100
Prime等级: 🟢 优秀（强势信号）
```

---

## 独立组件使用

### 2. 权重汇总 - `render_weights_summary()`

仅显示A层因子权重和贡献度：

```python
from ats_core.outputs.telegram_fmt import render_weights_summary

weights_output = render_weights_summary(result)
```

**输出**:
```
━━━━━ A层：方向因子 ━━━━━
🟢 趋势 +80 (13.9%) → +11.1  强势上行
🟡 动量 +52 (8.3%) → +4.3  温和上涨
...
加权总分: +56
```

**关键信息**:
- 分数：因子得分（-100到+100）
- 权重：该因子在总分中的权重百分比
- 贡献：该因子对总分的实际贡献值（分数×权重）

---

### 3. 调节器状态 - `render_modulators()`

显示F/I调节器详细信息：

```python
from ats_core.outputs.telegram_fmt import render_modulators

modulator_output = render_modulators(result)
```

**输出**:
```
━━━━━ B层：调制器 ━━━━━
✅ F资金领先 +45: 资金领先价格
   └─ 概率调整因子: ×1.00

🔵 I独立性 +25: 中等相关/跟随市场
   └─ p_min调整: 62.00% → 62.00% (+0.00%)
```

**作用**:
- F调节器：调整概率（资金领先=好信号，价格领先=风险）
- I调节器：调整p_min阈值（跟随大盘时提高准入门槛）

---

### 4. 四门验证 - `render_four_gates()`

显示所有验证门槛的通过状态：

```python
from ats_core.outputs.telegram_fmt import render_four_gates

gates_output = render_four_gates(result)
```

**输出**:
```
━━━━━ D层：四门验证 ━━━━━
✅ Gate1 数据质量: 95.00% ≥ 90%
✅ Gate2 期望值: +2.30% > 0
✅ Gate3 执行成本: 点差8.5bps, 冲击15.0bps
✅ Gate4a 概率阈值: P=72.0% ≥ 62.0%
✅ Gate4b 偏离阈值: ΔP=22.0% ≥ 12.0%

🎉 全部通过
```

**四门说明**:
- Gate1：数据质量（K线完整性、API可用性）≥90%
- Gate2：期望值（EV）>0（正期望才能交易）
- Gate3：执行成本（点差+冲击）在可接受范围
- Gate4：概率阈值（P≥p_min且ΔP≥Δp_min）

---

### 5. Prime分数分解 - `render_prime_breakdown()`

显示Prime分数的详细计算过程：

```python
from ats_core.outputs.telegram_fmt import render_prime_breakdown

prime_output = render_prime_breakdown(result)
```

**输出**:
```
━━━━━ Prime分数分解 ━━━━━
置信度: 72.0
基础强度: 72.0 × 0.6 = 43.2
概率: 72.0%
概率加成: (0.720 - 0.5) × 200 = +44.0
Prime总分: 43.2 + +44.0 = 87.2
最终Prime: 85/100
Prime等级: 🟢 优秀（强势信号）
```

**计算公式**:
```
Prime = confidence × 0.6 + (probability - 0.5) × 200

其中:
- confidence：加权总分的绝对值（0-100）
- probability：模型预测概率（0-1）
```

**等级标准**:
- 🟢 优秀（≥70）：强势信号，可靠性高
- 🟡 良好（≥50）：可靠信号，符合标准
- 🔵 合格（≥35）：基础信号，勉强通过
- 🔴 不合格（<35）：信号过弱，被过滤

---

## 集成到实时扫描器

### 方案A：替换默认输出

在 `scripts/realtime_signal_scanner.py` 中：

```python
from ats_core.outputs.telegram_fmt import render_signal_detailed

# 原来的代码
# msg = render_signal(result, is_watch=False)

# 改为详细模式
msg = render_signal_detailed(result, is_watch=False)

# 发送到Telegram
await telegram_bot.send_message(chat_id, msg)
```

### 方案B：配置化（推荐）

在 `config/params.json` 中添加配置：

```json
{
  "output": {
    "telegram_mode": "detailed",  // "simple" | "detailed"
    "console_mode": "detailed",
    "log_mode": "simple"
  }
}
```

在代码中根据配置选择：

```python
from ats_core.outputs.telegram_fmt import render_signal, render_signal_detailed

output_mode = params.get("output", {}).get("telegram_mode", "simple")

if output_mode == "detailed":
    msg = render_signal_detailed(result, is_watch=False)
else:
    msg = render_signal(result, is_watch=False)
```

---

## 调试和监控场景

### 场景1：分析为什么某个信号被过滤

```python
# 生成详细输出
output = render_signal_detailed(result)

# 检查四门验证部分
if "❌" in output:
    print("信号未通过四门验证:")
    print(render_four_gates(result))
```

### 场景2：监控因子贡献度

```python
# 只看权重汇总
output = render_weights_summary(result)

# 检查哪些因子贡献最大
# 例：如果C资金流贡献+8.3，说明CVD是主要看多因素
```

### 场景3：分析概率调整原因

```python
# 检查调节器状态
output = render_modulators(result)

# 如果F_adjustment < 1.0，说明价格领先资金（追涨风险）
# 如果p_min被调高，说明币种跟随大盘（需要更高确定性）
```

---

## 性能影响

所有增强型输出函数都是**纯展示逻辑**，不影响核心评分和交易决策：

- **计算开销**：微乎其微（<1ms per signal）
- **内存开销**：无额外缓存（实时计算）
- **API调用**：0（仅格式化已有数据）

可以放心在生产环境中使用。

---

## 完整示例

```python
#!/usr/bin/env python3
"""
完整示例：使用增强型监控输出
"""
import asyncio
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import (
    render_signal_detailed,
    render_weights_summary,
    render_four_gates
)

async def analyze_and_monitor(symbol: str):
    # 1. 分析币种
    result = await analyze_symbol(
        symbol=symbol,
        data=your_data_dict,
        params=your_params
    )

    # 2. 生成完整详细输出
    print("=" * 70)
    print("完整详细模式")
    print("=" * 70)
    print(render_signal_detailed(result))

    # 3. 或者只看特定部分
    print("\n" + "=" * 70)
    print("仅看权重贡献")
    print("=" * 70)
    print(render_weights_summary(result))

    # 4. 检查四门验证
    print("\n" + "=" * 70)
    print("四门验证状态")
    print("=" * 70)
    gates_output = render_four_gates(result)
    print(gates_output)

    # 5. 判断是否通过
    if "🎉 全部通过" in gates_output:
        print("\n✅ 信号通过所有验证，可以发送")
    else:
        print("\n❌ 信号未通过四门验证，已过滤")

if __name__ == "__main__":
    asyncio.run(analyze_and_monitor("BTCUSDT"))
```

---

## 总结

增强型监控输出系统提供了：

✅ **完整透明**：显示所有因子、权重、贡献度
✅ **深度分析**：Prime分解、四门验证、调节器状态
✅ **灵活使用**：可独立使用各组件，也可组合使用
✅ **零开销**：纯展示逻辑，不影响性能
✅ **易于集成**：简单替换render函数即可

适用于实时监控、调试分析、信号质量评估等多种场景。
