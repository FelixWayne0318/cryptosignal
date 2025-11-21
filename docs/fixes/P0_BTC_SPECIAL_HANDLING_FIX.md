# P0 BTC特殊处理修复

## 问题描述

在Step1方向确认层中，BTC作为参考资产，其I_score和btc_alignment计算存在错误：

1. **BTC I_score = 57（常数）**
   - 问题：BTC被当作普通山寨币计算独立性
   - 正确值：100（BTC是所有币独立性计算的参考资产，自身应完全独立）

2. **BTC btc_alignment = 0.84（常数）**
   - 问题：BTC与自身比较计算对齐度
   - 正确值：1.0（BTC与自身应完美对齐）

3. **BTC direction_confidence = 0.96（常数）**
   - 问题：由错误的I_score（57）计算得出
   - 正确值：1.0（BTC作为市场领导者，方向确定性最高）

## 修复方案

### 1. 配置文件修改 (config/params.json)

在 `four_step_system.step1_direction` 中新增 `btc_special_handling` 配置：

```json
"btc_special_handling": {
  "_comment": "v7.4.4新增: BTC特殊处理（BTC是参考资产，不应与自己比较）",
  "enabled": true,
  "reference_symbol": "BTCUSDT",
  "fixed_I_score": 100,
  "_I_score_note": "BTC是所有币独立性计算的参考资产，自身独立性应为100（完全独立）",
  "fixed_btc_alignment": 1.0,
  "_alignment_note": "BTC与自身的方向对齐应为1.0（完美对齐）",
  "fixed_direction_confidence": 1.0,
  "_confidence_note": "BTC作为市场领导者，方向确定性最高"
}
```

### 2. 核心逻辑修改 (ats_core/decision/step1_direction.py)

1. **函数签名更新**：
   - `step1_direction_confirmation()` 添加 `symbol: Optional[str] = None` 参数

2. **BTC特殊处理逻辑**：
   ```python
   # v7.4.4新增: BTC特殊处理
   btc_special_cfg = step1_cfg.get("btc_special_handling", {})
   is_btc_special = (
       btc_special_cfg.get("enabled", False) and
       symbol is not None and
       symbol.upper() == btc_special_cfg.get("reference_symbol", "BTCUSDT").upper()
   )

   if is_btc_special:
       # BTC是参考资产，使用固定值
       fixed_I_score = btc_special_cfg.get("fixed_I_score", 100)
       fixed_alignment = btc_special_cfg.get("fixed_btc_alignment", 1.0)
       fixed_confidence = btc_special_cfg.get("fixed_direction_confidence", 1.0)
       # ... 直接返回固定值结果
   ```

3. **元数据标记**：
   - 返回结果的 `metadata` 中包含 `is_btc_special: True`

### 3. 调用点更新 (ats_core/decision/four_step_system.py)

两处调用 `step1_direction_confirmation` 均添加 `symbol=symbol` 参数：

```python
step1_result = step1_direction_confirmation(
    factor_scores=factor_scores,
    btc_factor_scores=btc_factor_scores,
    params=params,
    symbol=symbol  # v7.4.4: 传递symbol用于BTC特殊处理
)
```

## 测试验证

运行测试：
```bash
python3 -m ats_core.decision.step1_direction
```

预期输出：
```
🔶 测试用例0：BTC特殊处理（I=100, alignment=1.0, confidence=1.0）
   通过: True
   方向得分: 68.3
   置信度: 1.00 (应为1.0)
   BTC对齐: 1.00 (应为1.0)
   最终强度: 68.3
   is_btc_special: True
```

## 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| config/params.json | 配置 | 新增btc_special_handling配置节 |
| ats_core/decision/step1_direction.py | 核心 | 添加BTC特殊处理逻辑和测试用例 |
| ats_core/decision/four_step_system.py | 核心 | 传递symbol参数到step1_direction_confirmation |

## 版本信息

- **版本**: v7.4.4
- **修复日期**: 2025-11-21
- **开发者**: Claude Code

## 影响分析

### 影响范围
- 仅影响BTC (BTCUSDT) 的Step1方向确认结果
- 其他币种的计算逻辑不变

### 预期效果
- BTC的 `final_strength` 将提高（因为confidence和alignment从约0.84/0.96提高到1.0）
- BTC信号更容易通过Step1
- 有助于将BTC作为市场方向的参考基准
