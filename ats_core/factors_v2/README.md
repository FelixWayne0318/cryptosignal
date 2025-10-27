# factors_v2 - 实验性增强因子系统

⚠️ **警告：此模块为实验性代码，未在生产环境中使用**

## 状态

- **版本**: v2.0 (Experimental)
- **状态**: 🧪 实验性
- **生产使用**: ❌ 否
- **测试覆盖**: ✅ 有单元测试
- **最后更新**: 2025-10-27

## 概述

此目录包含增强版因子系统（10+1维度），旨在扩展基础的7+1维度系统。

### 增强因子列表

| 因子 | 文件 | 功能 | 状态 |
|------|------|------|------|
| **C+** | `cvd_enhanced.py` | 动态加权CVD（现货+期货混合） | 🧪 实验性 |
| **O+** | `oi_regime.py` | OI四象限状态识别 | 🧪 实验性 |
| **V+** | `volume_trigger.py` | 成交量+触发K模式检测 | 🧪 实验性 |
| **L** | `liquidity.py` | 订单簿流动性+价差分析 | 🧪 实验性 |
| **B** | `basis_funding.py` | 基差+资金费率情绪 | 🧪 实验性 |
| **Q** | `liquidation.py` | 清算密度倾斜分析 | 🧪 实验性 |
| **I** | `independence.py` | Beta独立性（vs BTC/ETH） | 🧪 实验性 |

## 使用情况

### 当前调用

```python
# 仅在实验性分析器中使用
ats_core/pipeline/analyze_symbol_v2.py  # use_v2=False (默认关闭)
```

### 测试覆盖

```python
tests/test_factors_v2.py  # 单元测试覆盖
```

## 与V1系统的区别

### V1系统 (生产环境)
- **位置**: `ats_core/features/`
- **因子**: 7+1维度 (T/M/C/V/S/O/E + F)
- **状态**: ✅ 生产稳定
- **使用**: 28个文件主动调用

### V2系统 (实验性)
- **位置**: `ats_core/factors_v2/`
- **因子**: 10+1维度 (V1 + C+/O+/V+/L/B/Q/I)
- **状态**: 🧪 实验性
- **使用**: 仅测试环境

## 迁移计划

如果V2系统经过充分测试和验证，未来可能：

1. 逐步将V2因子集成到V1系统
2. 提供V1/V2混合模式
3. 最终完全替换V1（需要大量回测验证）

## 开发指南

### 添加新因子

1. 在此目录创建新文件（如`new_factor.py`）
2. 实现因子计算函数
3. 在`tests/test_factors_v2.py`添加单元测试
4. 更新`analyze_symbol_v2.py`集成逻辑

### 测试

```bash
# 运行V2因子测试
pytest tests/test_factors_v2.py -v

# 运行V2分析器测试
python tests/integration/test_gold_integration.py
```

## 注意事项

⚠️ **不要在生产环境使用此模块**
- 代码未经充分验证
- 可能存在未发现的bug
- 性能影响未评估

⚠️ **不要删除此模块**
- 测试文件依赖此模块
- 未来可能投入生产
- 包含有价值的研究成果

## 相关文档

- [系统实际功能总结](../../SYSTEM_ACTUAL_FUNCTIONALITY.md)
- [V2分析器](../pipeline/analyze_symbol_v2.py)
- [V2概率计算](../scoring/probability_v2.py)

---

**维护者**: CryptoSignal Team
**联系**: 查看主README.md
