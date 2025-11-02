# 四门系统规范

**规范版本**: v6.4
**生效日期**: 2025-11-02

> 详细实现请参考: `ats_core/gates/integrated_gates.py`

## 四门概览

1. **DataQual门** - 数据质量 ≥ 0.90
2. **EV门** - 期望价值 > 0
3. **Execution门** - 流动性和滑点检查
4. **Probability门** - 概率阈值（Prime: 0.58, Watch: 0.50）

详见: ../01_SYSTEM_OVERVIEW.md § 四门系统
