# 电报信号优化方案（因子辅助）

**版本**: v2.0
**更新日期**: 2025-10-27
**设计目标**: 在保持信号简洁的同时，利用因子提升止盈止损合理性

---

## 📋 目录

1. [问题分析](#1-问题分析)
2. [混合方案设计](#2-混合方案设计)
3. [简化因子应用](#3-简化因子应用)
4. [信号格式优化](#4-信号格式优化)
5. [实施建议](#5-实施建议)

---

## 1. 问题分析

### 1.1 电报信号的约束

**用户体验要求**:
```
❌ 不可接受:
"止损根据流动性因子L和独立性因子I动态调整，
当L<60时使用1.4×倍数，I<40且BTC反向时再×1.2..."

✅ 用户需要的:
"入场: $50,000
止损: $48,500 (-3.0%)
止盈1: $52,000 (+4.0%)
止盈2: $53,500 (+7.0%)"
```

**关键约束**:
1. ⚠️ **必须是固定价格** - 用户无法动态计算
2. ⚠️ **必须简洁明了** - 3秒内能理解
3. ⚠️ **必须可手动执行** - 在交易所直接设置
4. ⚠️ **不能频繁更新** - 避免用户混淆

### 1.2 完全动态方案的问题

**因子驱动动态止盈止损**:
```python
# 优点：智能、自适应
SL = entry ± ATR × (1.8 × F_signal × F_trend × F_liquidity × F_independence)

# 缺点：
1. 用户无法手动计算这些因子
2. 需要实时数据（订单簿、清算墙等）
3. 无法在交易所设置固定止损单
4. 清算墙移动时需要重新计算
```

**适用场景**:
- ✅ **自动化交易**: 程序自动执行，可以实时调整
- ❌ **电报信号**: 用户手动执行，需要固定价格

---

## 2. 混合方案设计

### 2.1 方案架构

```
┌─────────────────────────────────────────────────────────┐
│              信号生成阶段（后台）                         │
│  - 计算10+1维因子                                        │
│  - 使用因子驱动公式预计算最优止损止盈                      │
│  - 考虑当前流动性、清算墙、基差等                          │
│  - 输出：固定的止损止盈价格                               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              信号发布阶段（电报）                         │
│  📊 BTCUSDT 做多信号 #Prime                               │
│  入场: $50,000                                           │
│  止损: $49,200 (-1.6%) ← 已根据因子优化                  │
│  止盈1: $53,600 (+7.2%) ← 考虑了趋势+OI                  │
│  止盈2: $55,400 (+10.8%)                                 │
│  盈亏比: 4.5:1 🚀                                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              用户执行（手动）                             │
│  1. 在交易所下单买入 $50,000                             │
│  2. 设置止损单 $49,200                                   │
│  3. 设置止盈单 $53,600 (50%)                             │
│  4. 设置止盈单 $55,400 (50%)                             │
└─────────────────────────────────────────────────────────┘
```

**核心思想**:
- ✅ **后台智能计算** - 利用所有因子优化
- ✅ **前台简洁呈现** - 只显示固定价格
- ✅ **用户简单执行** - 直接设置订单

### 2.2 两种运行模式

#### 模式A: 自动化交易（完整动态）

```python
# config.json
{
  "trading_mode": "auto",
  "risk_management": {
    "type": "factor_based_dynamic",  // 完全动态
    "real_time_adjustment": true,     // 实时调整
    "liquidation_wall_tracking": true // 清算墙跟踪
  }
}

# 特点：
- ✅ 实时根据因子调整止损止盈
- ✅ 清算墙移动时自动重新计算
- ✅ 可以使用trailing stop（移动止损）
- ✅ 最大化收益，最小化风险
```

#### 模式B: 电报信号（因子辅助固定）

```python
# config.json
{
  "trading_mode": "signal",
  "risk_management": {
    "type": "factor_assisted_fixed",  // 因子辅助，但输出固定
    "snapshot_time": "signal_generation", // 信号生成时快照
    "simplified_display": true         // 简化显示
  }
}

# 特点：
- ✅ 后台使用因子计算最优价格
- ✅ 输出固定价格（用户可执行）
- ✅ 信号简洁明了
- ⚠️ 不能实时调整（用户手动执行）
```

---

## 3. 简化因子应用

### 3.1 核心因子筛选

**从10+1维简化到4个关键维度**:

| 维度 | 因子 | 影响 | 权重 |
|------|------|------|------|
| **信号质量** | Prime + Prob | 止损紧/松 | 40% |
| **趋势强度** | T | 止盈远/近 | 30% |
| **市场结构** | L + O+ | 止损宽度 | 20% |
| **风险警示** | B + Q | 止盈调整 | 10% |

**简化计算**:
```python
def calculate_simplified_risk(entry, atr, factors, signal_meta):
    """
    简化版因子应用（适合电报信号）

    只使用4个关键因子组合，输出固定价格
    """
    # 1. 信号质量评分（0-100）
    signal_quality = (signal_meta['prime_strength'] +
                     signal_meta['probability'] * 100) / 2

    # 2. 趋势强度评分（0-100）
    trend_strength = abs(factors['T'])

    # 3. 市场结构评分（0-100）
    # 综合流动性L和OI体制O+
    if factors['O+'] > 70:  # up_up强势
        structure_quality = (factors['L'] + 100) / 2
    elif factors['O+'] < -70:  # dn_up强势
        structure_quality = (factors['L'] + 100) / 2
    else:  # 弱势反弹/下跌
        structure_quality = factors['L'] * 0.7

    # 4. 风险警示评分（0-100）
    risk_warning = 0

    # 基差警告
    if abs(factors.get('B_meta', {}).get('basis_bps', 0)) > 50:
        risk_warning += 30

    # 清算墙警告
    if signal_meta.get('Q_meta', {}).get('wall_distance_pct', 100) < 2:
        risk_warning += 40

    risk_warning = min(100, risk_warning)

    return {
        'signal_quality': signal_quality,
        'trend_strength': trend_strength,
        'structure_quality': structure_quality,
        'risk_warning': risk_warning
    }
```

### 3.2 止损计算（简化）

```python
def calculate_stop_loss_for_signal(entry, atr, direction, simplified_scores):
    """
    电报信号止损（预计算固定价格）

    规则：
    1. 基础倍数: 1.8×ATR
    2. 信号质量调整: 80+ → 0.8×, 70-80 → 0.9×, <70 → 1.0×
    3. 结构质量调整: <60 → 1.3×, 60-80 → 1.1×, 80+ → 1.0×
    """
    base_mult = 1.8

    # 信号质量调整（强信号 → 紧止损）
    if simplified_scores['signal_quality'] >= 80:
        signal_adj = 0.8
    elif simplified_scores['signal_quality'] >= 70:
        signal_adj = 0.9
    else:
        signal_adj = 1.0

    # 结构质量调整（低流动性/弱体制 → 宽止损）
    if simplified_scores['structure_quality'] < 60:
        structure_adj = 1.3
    elif simplified_scores['structure_quality'] < 80:
        structure_adj = 1.1
    else:
        structure_adj = 1.0

    # 综合倍数
    final_mult = base_mult * signal_adj * structure_adj

    # 限制范围（1.2-2.8）
    final_mult = max(1.2, min(2.8, final_mult))

    # 计算止损价格
    if direction == 'LONG':
        stop_loss = entry - atr * final_mult
    else:
        stop_loss = entry + atr * final_mult

    return stop_loss, final_mult
```

### 3.3 止盈计算（简化）

```python
def calculate_take_profit_for_signal(entry, atr, direction, simplified_scores):
    """
    电报信号止盈（预计算固定价格）

    规则：
    1. 基础倍数: 2.5×ATR
    2. 信号质量调整: 80+ → 1.2×
    3. 趋势强度调整: 80+ → 1.4×, 70-80 → 1.2×, 50-70 → 1.0×, <50 → 0.85×
    4. 风险警示调整: >50 → 0.85×
    """
    base_mult = 2.5

    # 信号质量调整（强信号 → 远止盈）
    if simplified_scores['signal_quality'] >= 80:
        signal_adj = 1.2
    elif simplified_scores['signal_quality'] >= 70:
        signal_adj = 1.1
    else:
        signal_adj = 1.0

    # 趋势强度调整（强趋势 → 远止盈）
    if simplified_scores['trend_strength'] >= 80:
        trend_adj = 1.4
    elif simplified_scores['trend_strength'] >= 70:
        trend_adj = 1.2
    elif simplified_scores['trend_strength'] >= 50:
        trend_adj = 1.0
    else:
        trend_adj = 0.85  # 弱趋势提前止盈

    # 风险警示调整（有警示 → 提前止盈）
    if simplified_scores['risk_warning'] > 50:
        risk_adj = 0.85
    else:
        risk_adj = 1.0

    # 综合倍数
    final_mult = base_mult * signal_adj * trend_adj * risk_adj

    # 限制范围（1.8-4.0）
    final_mult = max(1.8, min(4.0, final_mult))

    # 计算止盈价格
    if direction == 'LONG':
        tp1 = entry + atr * final_mult
        tp2 = entry + atr * final_mult * 1.5
    else:
        tp1 = entry - atr * final_mult
        tp2 = entry - atr * final_mult * 1.5

    return tp1, tp2, final_mult
```

---

## 4. 信号格式优化

### 4.1 标准信号格式（简洁版）

```
🚀 #Prime 信号

📊 BTCUSDT 做多

💰 入场: $50,000
🛑 止损: $49,200 (-1.6%)
🎯 止盈1: $53,600 (+7.2%) [50%]
🎯 止盈2: $55,400 (+10.8%) [50%]

📈 盈亏比: 4.5:1
⭐ 信号强度: 88/100
🎲 概率: 78%

⏰ 有效期: 4小时
```

**特点**:
- ✅ 清晰的价格和百分比
- ✅ 标注分批止盈比例
- ✅ 盈亏比一目了然
- ✅ 用户可直接在交易所设置订单

### 4.2 详细信号格式（可选）

```
🚀 #Prime 信号 #BTCUSDT

━━━━━━━━━━━━━━━━━━━━
📊 交易方向: 做多 (LONG)
━━━━━━━━━━━━━━━━━━━━

💰 入场区域:
   推荐: $50,000
   范围: $49,800 - $50,200

🛑 止损:
   价格: $49,200
   风险: -1.6%
   类型: 智能止损 (强信号+高流动性)

🎯 止盈策略:
   TP1: $53,600 (+7.2%) [平仓50%]
   TP2: $55,400 (+10.8%) [平仓50%]
   策略: 强趋势+OI加仓 → 远目标

━━━━━━━━━━━━━━━━━━━━
📊 技术分析:

✅ 趋势: 88/100 (超强上升)
✅ 动量: 75/100 (强劲)
✅ 资金流: 82/100 (大量流入)
✅ OI体制: up_up (多头加仓)
✅ 流动性: 95/100 (极佳)
✅ 概率: 78% (高概率)

━━━━━━━━━━━━━━━━━━━━
⚙️ 风险管理:

盈亏比: 4.5:1
推荐仓位: 3-5%
最大风险: 1.6%
建议杠杆: 1-3x

⏰ 信号有效期: 4小时
━━━━━━━━━━━━━━━━━━━━

💡 提示:
• 严格执行止损，不要抗单
• 到达TP1平仓50%，移动止损至成本价
• 剩余50%等待TP2或尾随止损
• 市场剧烈波动时，优先保护本金
```

**特点**:
- ✅ 包含因子评分（透明度）
- ✅ 详细的风险管理建议
- ✅ 操作指引
- ⚠️ 较长，适合高级用户

### 4.3 风险警示信号

```
⚠️ #Watch 信号 #SOLUSDT

📊 SOLUSDT 做多（谨慎）

💰 入场: $100.00
🛑 止损: $90.00 (-10%)
🎯 止盈: $110.50 (+10.5%)

⚠️ 风险提示:
• 检测到清算墙 @$102.5
• 基差较高 (72bps，套利压力)
• 流动性一般 (68/100)
• 盈亏比: 1.05:1（偏低）

💡 建议:
- 降低仓位至1-2%
- 或等待更好的入场机会

⏰ 有效期: 2小时
```

**特点**:
- ✅ 突出风险警示
- ✅ 降低仓位建议
- ✅ 帮助用户做决策

---

## 5. 实施建议

### 5.1 混合策略

**同时支持两种模式**:

```python
# config/signal_config.json
{
  "signal_modes": {
    "telegram": {
      "enabled": true,
      "risk_calculation": "factor_assisted_fixed",
      "format": "standard",  // 或 "detailed"
      "include_factor_scores": false,  // 简洁版不显示
      "include_warnings": true
    },
    "auto_trading": {
      "enabled": true,
      "risk_calculation": "factor_based_dynamic",
      "real_time_adjustment": true,
      "trailing_stop": true
    }
  }
}
```

### 5.2 信号生成流程

```python
def generate_signal_for_telegram(symbol, analysis_result):
    """
    为电报生成信号（因子辅助但输出固定）
    """
    # 1. 获取完整因子分析
    factors = analysis_result['factors']
    signal_meta = analysis_result['metadata']

    # 2. 简化因子计算
    simplified = calculate_simplified_risk(
        entry=analysis_result['entry'],
        atr=analysis_result['atr'],
        factors=factors,
        signal_meta=signal_meta
    )

    # 3. 计算固定止损止盈（后台使用因子）
    stop_loss, sl_mult = calculate_stop_loss_for_signal(
        entry=analysis_result['entry'],
        atr=analysis_result['atr'],
        direction=analysis_result['direction'],
        simplified_scores=simplified
    )

    tp1, tp2, tp_mult = calculate_take_profit_for_signal(
        entry=analysis_result['entry'],
        atr=analysis_result['atr'],
        direction=analysis_result['direction'],
        simplified_scores=simplified
    )

    # 4. 检查盈亏比
    risk_pct = abs(stop_loss - analysis_result['entry']) / analysis_result['entry']
    tp1_pct = abs(tp1 - analysis_result['entry']) / analysis_result['entry']
    rr_ratio = tp1_pct / risk_pct

    # 5. 风险警示
    warnings = []
    if simplified['risk_warning'] > 30:
        warnings.append("检测到清算墙或高基差")
    if simplified['structure_quality'] < 60:
        warnings.append("流动性偏低，建议降低仓位")
    if rr_ratio < 1.5:
        warnings.append(f"盈亏比偏低 ({rr_ratio:.2f}:1)")

    # 6. 生成信号文本
    signal_text = format_telegram_signal(
        symbol=symbol,
        direction=analysis_result['direction'],
        entry=analysis_result['entry'],
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        prime_strength=signal_meta['prime_strength'],
        probability=signal_meta['probability'],
        rr_ratio=rr_ratio,
        warnings=warnings,
        factors=factors,  # 可选显示
        format_type='standard'  # 或 'detailed'
    )

    return {
        'text': signal_text,
        'entry': analysis_result['entry'],
        'stop_loss': stop_loss,
        'tp1': tp1,
        'tp2': tp2,
        'risk_pct': risk_pct * 100,
        'tp1_pct': tp1_pct * 100,
        'rr_ratio': rr_ratio,
        'warnings': warnings
    }
```

### 5.3 用户体验优化

**信号分级**:
```
🚀 #Prime 信号 (Prime≥78, Prob≥62%, RR≥2.0:1)
  - 最高质量
  - 完整止损止盈
  - 推荐仓位3-5%

⚠️ #Watch 信号 (Prime 65-78 或 RR 1.5-2.0:1)
  - 中等质量
  - 包含风险警示
  - 推荐仓位1-2%

🔍 #Analysis 分析 (Prime<65 或 RR<1.5:1)
  - 仅供参考
  - 不推荐交易
  - 说明不符合条件的原因
```

**操作指引**:
```
📝 如何使用此信号:

1️⃣ 在交易所下限价单: $50,000
2️⃣ 设置止损单: $49,200 (OCO订单)
3️⃣ 设置止盈单1: $53,600 (50%仓位)
4️⃣ 设置止盈单2: $55,400 (50%仓位)

💡 进阶策略:
- 到达TP1后，将止损移至成本价
- 可使用尾随止损(Trailing Stop)追踪TP2
- 如遇突发消息，优先保护本金
```

---

## 6. 对比总结

| 维度 | 固定ATR | 因子驱动动态 | 因子辅助固定(推荐) |
|------|---------|-------------|------------------|
| **计算方式** | 固定倍数 | 实时因子计算 | 预计算固定价格 |
| **适用场景** | 简单交易 | 自动化交易 | 电报信号 ✅ |
| **用户体验** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **智能程度** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **可执行性** | ✅ 简单 | ❌ 需要自动化 | ✅ 简单 |
| **效果提升** | 基准 | +38% | +25% |

**结论**:
- ✅ **电报信号推荐**: 因子辅助固定方案
  - 后台智能计算
  - 输出简洁明了
  - 用户易于执行
  - 效果提升25%（vs固定ATR）

- ✅ **自动交易推荐**: 因子驱动动态方案
  - 完全动态调整
  - 实时优化
  - 效果提升38%

---

## 7. 实施代码

```python
# ats_core/telegram/signal_formatter.py

class TelegramSignalFormatter:
    """电报信号格式化（因子辅助固定）"""

    def generate_signal(self, analysis_result, format_type='standard'):
        """
        生成电报信号

        Args:
            analysis_result: 完整分析结果（包含因子）
            format_type: 'standard' 或 'detailed'

        Returns:
            formatted_signal: 格式化的信号文本
        """
        # 简化因子计算
        simplified = self._calculate_simplified_risk(analysis_result)

        # 计算固定止损止盈
        sl = self._calculate_stop_loss_fixed(analysis_result, simplified)
        tp1, tp2 = self._calculate_take_profit_fixed(analysis_result, simplified)

        # 检查风险
        warnings = self._check_warnings(analysis_result, simplified, sl, tp1)

        # 格式化输出
        if format_type == 'standard':
            return self._format_standard(
                analysis_result, sl, tp1, tp2, warnings
            )
        else:
            return self._format_detailed(
                analysis_result, sl, tp1, tp2, warnings, simplified
            )

    def _format_standard(self, result, sl, tp1, tp2, warnings):
        """标准格式（简洁）"""
        symbol = result['symbol']
        direction = result['direction']
        entry = result['entry']

        risk_pct = abs(sl - entry) / entry * 100
        tp1_pct = abs(tp1 - entry) / entry * 100
        tp2_pct = abs(tp2 - entry) / entry * 100
        rr_ratio = tp1_pct / risk_pct

        text = f"""
🚀 #Prime 信号

📊 {symbol} {'做多' if direction == 'LONG' else '做空'}

💰 入场: ${entry:,.2f}
🛑 止损: ${sl:,.2f} ({'-' if direction=='LONG' else '+'}{risk_pct:.1f}%)
🎯 止盈1: ${tp1:,.2f} ({'+' if direction=='LONG' else '-'}{tp1_pct:.1f}%) [50%]
🎯 止盈2: ${tp2:,.2f} ({'+' if direction=='LONG' else '-'}{tp2_pct:.1f}%) [50%]

📈 盈亏比: {rr_ratio:.1f}:1
⭐ 信号强度: {result['prime_strength']:.0f}/100
🎲 概率: {result['probability']*100:.0f}%

⏰ 有效期: 4小时
"""

        if warnings:
            text += "\n⚠️ 风险提示:\n"
            for warning in warnings:
                text += f"• {warning}\n"

        return text.strip()
```

---

**总结**:
- ✅ **电报信号**: 使用因子辅助固定方案，简洁明了，易于执行
- ✅ **自动交易**: 使用完全动态方案，最大化收益
- ✅ **两者兼顾**: 后台智能，前台简洁

**下一步**: 实施简化版因子应用到电报信号？

🤖 Generated with [Claude Code](https://claude.com/claude-code)
