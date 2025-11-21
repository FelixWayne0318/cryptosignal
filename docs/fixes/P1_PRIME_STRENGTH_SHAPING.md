# P1 Step1非线性强度整形 (prime_strength)

## 问题描述

基于BTC回测数据分析（202信号，26.24%胜率），发现：

1. **中等强度区间(7-10)胜率最高(45-50%)**
2. **极端强度(>15)胜率反而较低(21%)**
3. **T因子与胜率呈反向相关**

这表明原始direction_strength的极端值可能是噪声而非信号强度的真实反映。

## 修复方案

### 设计原则

- **温和压制**：不剔除高强度信号，只调整其"信任程度"
- **单一硬阈值**：仅min_final_strength控制通过/拒绝
- **全币种统一**：所有币（包括BTC）使用相同整形参数
- **分层压缩**：分段线性函数，避免引入非线性复杂度

### 1. 配置文件修改 (config/params.json)

在 `four_step_system.step1_direction` 中新增 `prime_strength` 配置：

```json
"prime_strength": {
  "_comment": "v7.4.5新增: Step1非线性强度整形（全币种统一，温和压制极端值）",
  "enabled": true,

  "mid_high": 12.0,
  "_mid_high_note": "中等强度上限，此值以内保持线性不变",

  "extreme_high": 20.0,
  "_extreme_high_note": "极端强度阈值，超过此值进一步压缩",

  "high_band_scale": 0.7,
  "_high_band_scale_note": "高强度区间(mid_high~extreme_high)的压缩系数",

  "extreme_band_scale": 0.5,
  "_extreme_band_scale_note": "极端强度区间(>extreme_high)的压缩系数"
}
```

### 2. 核心逻辑修改 (ats_core/decision/step1_direction.py)

1. **新增 `shape_direction_strength()` 函数**：

```python
def shape_direction_strength(raw_strength: float, params: Dict[str, Any]) -> float:
    """
    v7.4.5: Step1非线性强度整形

    分段线性公式:
        x <= mid_high: y = x (不变)
        mid_high < x <= extreme_high: y = mid_high + (x - mid_high) * 0.7
        x > extreme_high: y = mid_high + 5.6 + (x - extreme_high) * 0.5
    """
```

2. **修改主函数计算流程**：
   - 计算 `direction_strength` (原逻辑不变)
   - 应用 `prime_strength = shape_direction_strength(direction_strength, params)`
   - 计算 `final_strength = prime_strength × confidence × alignment`

3. **BTC特殊处理分支同样应用整形**：
   - BTC仍使用固定confidence=1.0, alignment=1.0
   - 但prime_strength使用相同整形函数

### 3. 返回值更新

返回结果增加 `prime_strength` 字段：

```python
return {
    "direction_strength": direction_strength,  # 原始强度
    "prime_strength": prime_strength,           # v7.4.5: 整形后强度
    "final_strength": final_strength,           # prime × conf × align
    # ... 其他字段
}
```

## 数学公式

### 整形函数

设 x = raw_strength，y = prime_strength

```
         ┌ x                                              , x ≤ 12
y(x) =   │ 12 + (x - 12) × 0.7                           , 12 < x ≤ 20
         └ 12 + 5.6 + (x - 20) × 0.5                     , x > 20
```

### 示例计算

| raw_strength | prime_strength | 压缩率 |
|--------------|----------------|--------|
| 10           | 10.0           | 0%     |
| 15           | 14.1           | 6%     |
| 20           | 17.6           | 12%    |
| 30           | 22.6           | 25%    |
| 50           | 32.6           | 35%    |

## 测试验证

运行测试：
```bash
python3 -m ats_core.decision.step1_direction
```

预期输出：
```
🔶 测试用例0：BTC特殊处理（I=100, alignment=1.0, confidence=1.0）
   通过: True
   prime_strength: 41.8
   最终强度: 41.8

📊 测试用例1：高独立性币(I=90) + 同向BTC(T_BTC=80)
   通过: True
   最终强度: 40.9
```

## 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| config/params.json | 配置 | 新增prime_strength配置节 |
| ats_core/decision/step1_direction.py | 核心 | 添加shape函数和集成逻辑 |

## 版本信息

- **版本**: v7.4.5
- **修复日期**: 2025-11-21
- **开发者**: Claude Code
- **专家设计**: 基于回测数据分析的非线性整形方案

## 影响分析

### 影响范围
- 影响所有币种的Step1方向确认结果
- Gate3使用final_strength（已验证正确）

### 预期效果
- 极端高强度信号的final_strength降低
- 中等强度信号保持不变
- 减少因高T因子产生的假阳性信号
- 提高整体胜率（预期从26%提升）

### 向后兼容
- 可通过 `prime_strength.enabled: false` 禁用整形
- 禁用后恢复原始v7.4.4行为
