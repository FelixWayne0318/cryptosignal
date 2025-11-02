# 规范子系统索引

**版本**: v6.4 Phase 2
**更新日期**: 2025-11-02

---

## 📋 规范文档列表

### 核心规范（按优先级）

#### 1. [FACTOR_SYSTEM.md](FACTOR_SYSTEM.md) ⭐⭐⭐
**10+1维因子系统完整规范**

涵盖内容：
- A层9因子定义与计算（T/M/C/S/V/O/L/B/Q）
- 统一标准化链
- 因子权重配置
- 输出规范（±100标准化）

适用对象：开发人员、因子调优人员

---

#### 2. [MODULATORS.md](MODULATORS.md) ⭐⭐⭐
**B层调制器规范（F/I因子）**

涵盖内容：
- F因子（资金领先）计算与作用机制
- I因子（独立性）计算与作用机制
- 温度/成本/阈值调节公式
- 极端值处理（tanh软化）

适用对象：开发人员、量化研究员

---

#### 3. [PUBLISHING.md](PUBLISHING.md) ⭐⭐
**Prime/Watch发布规范**

涵盖内容：
- Prime判定条件
- Watch降级规则
- 防抖动参数（入场/确认/冷却）
- 拒绝原因追踪

适用对象：开发人员、运维人员

---

#### 4. [NEWCOIN.md](NEWCOIN.md) ⭐⭐⭐
**新币通道完整规范（Phase 2-4）**

涵盖内容：
- 进入/回切判定标准
- 数据流规范（1m/5m/15m）
- 点火-成势-衰竭模型
- 新币专用因子（T_new/M_new/S_new）
- Phase 2实现进度
- Phase 3-4路线图

适用对象：开发人员、架构师

---

#### 5. [DATA_LAYER.md](DATA_LAYER.md) ⭐⭐
**数据层规范**

涵盖内容：
- Binance API端点映射
- REST vs WebSocket选择
- 数据质量监控
- 缓存策略
- 时钟同步要求

适用对象：开发人员、运维人员

---

#### 6. [GATES.md](GATES.md) ⭐⭐
**四门系统规范**

涵盖内容：
- DataQual门（数据质量检查）
- EV门（期望价值检查）
- Execution门（执行可行性检查）
- Probability门（概率阈值检查）
- 门槛参数配置
- 滞回机制

适用对象：开发人员、质量控制人员

---

## 🔗 规范间依赖关系

```
FACTOR_SYSTEM.md (基础)
    ↓
    ├─→ MODULATORS.md (调制器)
    │       ↓
    └─→ 加权评分 → 概率映射
                    ↓
            ┌───────┴───────┐
            ↓               ↓
        GATES.md        PUBLISHING.md
            ↓               ↓
            └───────┬───────┘
                    ↓
            最终信号输出

DATA_LAYER.md (支撑所有模块)

NEWCOIN.md (独立通道，部分复用上述规范)
```

---

## 📊 规范-代码追溯

| 规范文档 | 核心实现模块 | 配置文件 | 测试文件 |
|---------|-------------|---------|---------|
| FACTOR_SYSTEM.md | `ats_core/factors_v2/*.py` | `config/params.json` | - |
| MODULATORS.md | `ats_core/factors_v2/fund_leading.py`<br>`ats_core/factors_v2/independence.py` | `config/params.json` (weights) | - |
| PUBLISHING.md | `ats_core/publishing/anti_jitter.py` | `config/params.json` (publish) | - |
| NEWCOIN.md | `ats_core/data_feeds/newcoin_data.py`<br>`ats_core/data_feeds/ws_newcoin.py` | `config/params.json` (new_coin) | `test_phase2.py` |
| DATA_LAYER.md | `ats_core/sources/binance.py`<br>`ats_core/pipeline/batch_scan_optimized.py` | - | - |
| GATES.md | `ats_core/gates/integrated_gates.py` | `config/params.json` (gates) | - |

---

## 🎯 快速查找

### 我想了解...

#### 因子如何计算？
→ [FACTOR_SYSTEM.md](FACTOR_SYSTEM.md) § 2-10（各因子详细定义）

#### F/I因子如何影响概率？
→ [MODULATORS.md](MODULATORS.md) § 3（温度调节机制）

#### Prime信号如何判定？
→ [PUBLISHING.md](PUBLISHING.md) § 1（Prime判定条件）

#### 新币如何处理？
→ [NEWCOIN.md](NEWCOIN.md)（完整新币通道规范）

#### 数据从哪里来？
→ [DATA_LAYER.md](DATA_LAYER.md) § 2（Binance API映射）

#### 四门系统如何工作？
→ [GATES.md](GATES.md) § 1-4（四门详细说明）

---

## 📝 规范维护规则

### 修改流程
1. 确定修改涉及的规范文档
2. 在对应文档中添加版本注释
3. 同步更新本索引文件的"最后更新"日期
4. 在[03_VERSION_HISTORY.md](../03_VERSION_HISTORY.md)中记录变更
5. 检查"规范-代码追溯"表是否需要更新

### 新增规范
1. 在specifications/目录创建新文档
2. 在本文件添加索引条目
3. 更新"规范间依赖关系"图
4. 更新"规范-代码追溯"表
5. 在[00_INDEX.md](../00_INDEX.md)中添加链接

### 版本标注
每个规范文档开头必须标注：
```markdown
**规范版本**: vX.Y
**生效日期**: YYYY-MM-DD
**状态**: 生效中 / 草案 / 已废弃
```

---

## ⚠️ 重要提示

1. **唯一性原则**: 每个功能点只在一个规范文档中描述，避免冲突
2. **完整性要求**: 所有实现代码必须有对应的规范文档支撑
3. **一致性检查**: 修改规范后必须验证代码实现是否一致
4. **可追溯性**: 通过"规范-代码追溯"表确保文档-代码双向可查

---

**维护**: 技术文档团队
**审核**: 系统架构师
**版本**: v6.4-phase2
