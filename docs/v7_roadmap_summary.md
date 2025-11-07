# v7系统演进路线图 - 总结

## 三阶段演进策略

```
v7.0 理论版          v7.2 阶段1           v7.2 阶段2           v7.2 阶段3
(已废弃)    →      (规则增强)    →      (统计优化)    →      (ML增强)
                    ✅ 已完成           ⏳ 1-2个月          🔮 3-6个月
```

---

## 当前状态：v7.2 阶段1 ✅

### 已完成功能

| 组件 | 功能 | 文件 | 状态 |
|------|------|------|------|
| **F因子v2** | 精确资金领先性计算 | fund_leading.py:207-319 | ✅ |
| **因子分组** | TC/VOM/B三组减少共线性 | factor_groups.py | ✅ |
| **统计校准** | 分桶校准confidence→胜率 | empirical_calibration.py | ✅ |
| **四道闸门** | 数据/资金/市场/成本硬过滤 | gates.py | ✅ |
| **集成模块** | v7.2无侵入式增强 | analyze_symbol_v72.py | ✅ |
| **测试套件** | 端到端验证 | test_v72_stage1.py | ✅ |

### 核心改进

1. **F因子v2**
   - 公式：F = (资金动量 - 价格动量) / ATR归一化
   - CVD(60%) + OI名义化(40%)
   - 测试结果：F=94（资金强势领先）

2. **因子分组**
   - TC组(50%): 趋势70% + 资金流30%
   - VOM组(35%): 量能50% + 持仓30% + 动量20%
   - B组(15%): 基差独立

3. **统计校准**
   - Bootstrap：P = 0.40 + confidence/100 × 0.30
   - 分桶统计：10分位，50+样本启动

4. **四道闸门**
   - Gate1: K线数 >= 100
   - Gate2: F_directional >= -15
   - Gate3: 低独立性(I<30) + 逆势 → 拒绝
   - Gate4: EV > 0

### 部署就绪

```bash
# 当前系统可直接部署到生产环境
资源需求：50GB Vultr VPS（无需GPU）
运行成本：$30-50/月
```

---

## 下一步：v7.2 阶段2（1-2个月）

### 目标

将规则系统通过真实交易数据，优化为**数据驱动的统计系统**。

### 核心任务

#### 1. 真实交易数据积累 (Week 1-2)

**数据采集**：
```python
TradeRecorder:
  - 信号快照：因子、市场状态、预测值
  - 执行记录：实际成交价、滑点、成本分解
  - 交易结果：盈亏、持仓时长、退出原因
```

**存储设计**：
```sql
signal_snapshots   → 信号发布时的完整快照
execution_records  → 实际执行数据（价格、成本）
trade_results      → 最终结果（win/loss/pnl）
```

**存储估算**：< 10GB（50GB VPS充足）

#### 2. 校准表优化 (Week 3-4)

**AdaptiveCalibrator**：
- 从数据库统计真实胜率
- 10分位分桶（0-10, 10-20, ..., 90-100）
- 最小样本数：30/桶，启动校准需300+样本
- 计算Brier Score（目标 < 0.15）

**进化路径**：
| 阶段 | 方法 | 数据需求 | 精度 |
|------|------|----------|------|
| Week 1 | Bootstrap | 0样本 | ±10% |
| Week 4 | 10分位统计 | 300+样本 | ±5% |
| Month 2 | 5分位统计 | 1000+样本 | ±3% |

#### 3. 闸门阈值调整 (Week 5-6)

**GateOptimizer**：
- F闸门：扫描-30到+10，最大化Sharpe
- 市场闸门：优化独立性阈值（当前I<30）
- A/B测试：对比优化前后性能

#### 4. 成本模型精细化 (Week 7-8)

**CostAnalyzer**：
- 按币种统计：中位数、P95分位成本
- 按持仓时长统计：资金费率累计成本
- ExecutionCostEstimatorV2：查表获取真实成本

### 时间线（8周）

```
Week 1-2: 数据采集基础设施 → 里程碑：首批数据入库
Week 3-4: 校准表优化        → 里程碑：Bootstrap切换到真实数据
Week 5-6: 闸门阈值调整      → 里程碑：数据驱动阈值上线
Week 7-8: 成本模型精细化    → 里程碑：动态成本估算
Week 9+:  持续监控与迭代    → 稳定运行
```

### 成功指标

| 指标 | 目标值 | 衡量方法 |
|------|--------|----------|
| Brier Score | < 0.15 | 校准质量 |
| 胜率预测误差 | ±5% | 实际vs预测 |
| 成本估算误差 | ±2bps | 实际vs预测 |
| 信号样本数 | 500+ | 数据库 |

### 资源需求

- **存储**：< 10GB（现有50GB VPS充足）
- **GPU**：不需要
- **成本**：$35/月（VPS + S3备份）

---

## 未来：v7.2 阶段3（3-6个月）

### 目标

引入深度学习模型，提升**价格预测、因子优化、状态识别**能力。

### 核心模型

#### 1. Transformer价格预测 (Month 3-4)

**架构**：
```python
输入：168h价格序列 + 技术指标
模型：Transformer Encoder (6层, 8头, d_model=256)
输出：未来4h价格区间 [mean, std]
```

**目标**：方向准确率 > 60%

#### 2. XGBoost因子权重优化 (Month 4-5)

**功能**：
- 输入：T/M/C/V/O/B/F + 市场状态
- 输出：盈利概率
- 推导最优因子权重（从特征重要性）
- 在线学习：每周更新

**目标**：胜率提升 +3%

#### 3. LSTM市场Regime识别 (Month 5-6)

**Regime定义**：
- 0: 震荡（低波动）
- 1: 牛市（上升趋势）
- 2: 熊市（下降趋势）
- 3: 高波动（剧烈震荡）

**自适应策略**：
- 震荡：降低仓位，缩小TP
- 牛市：提高仓位，扩大TP
- 熊市：谨慎开多，快速止损
- 高波动：大幅降低仓位

**目标**：Regime识别准确率 > 70%

### 时间线（6个月）

```
Month 1-2: 数据基础设施    → 10TB存储 + GPU服务器
Month 3-4: Transformer训练  → 方向准确率 > 60%
Month 4-5: XGBoost优化      → 胜率提升 +3%
Month 5-6: LSTM Regime      → 识别准确率 > 70%
Month 6+:  集成与优化       → v7.3完整系统上线
```

### 成功指标

| 指标 | 目标值 |
|------|--------|
| Transformer方向准确率 | > 60% |
| XGBoost胜率提升 | +3% |
| LSTM Regime准确率 | > 70% |
| 整体Sharpe Ratio | > 2.0 |
| 年化收益率 | > 50% |
| 最大回撤 | < 15% |

### 资源需求

- **存储**：10TB（对象存储S3）
- **GPU**：AWS p3.2xlarge (V100)
- **成本**：$690/月（训练期），$200/月（推理期）

### 成本优化方案

- 训练：Spot实例（节省70%）→ $90/月
- 推理：模型蒸馏为小模型，CPU推理
- 存储：冷数据归档到Glacier（节省80%）
- **优化后总成本**：$200-300/月

---

## 决策建议

### 立即开始：阶段2（推荐 ✅）

**理由**：
1. **低成本高收益**：$35/月，显著提升系统性能
2. **快速见效**：8周即可完成，尽早验证效果
3. **必要基础**：阶段3依赖阶段2的数据积累
4. **风险可控**：无需GPU，基于现有基础设施

**Action Items**：
1. Week 1: 实现TradeRecorder（3天）
2. Week 1: 创建SQLite schema（1天）
3. Week 2: 集成到pipeline，部署生产（3天）
4. Week 3+: 每周检查数据积累，逐步启动优化

### 评估后决定：阶段3

**评估标准**（阶段2运行2个月后）：
- [ ] 阶段2 Sharpe > 1.5（已经很好）
- [ ] 信号样本数 > 1000（数据充足）
- [ ] 校准质量 Brier Score < 0.15（统计可靠）
- [ ] 预算允许：$300-700/月（成本可承受）

**如果满足以上条件** → 启动阶段3
**如果阶段2已满意** → 保持现状，持续优化

---

## 关键文件

### 阶段1（已完成）

```
ats_core/features/fund_leading.py          # F因子v2
ats_core/scoring/factor_groups.py          # 因子分组
ats_core/calibration/empirical_calibration.py  # 统计校准
ats_core/pipeline/gates.py                 # 四道闸门
ats_core/pipeline/analyze_symbol_v72.py    # 集成模块
test_v72_stage1.py                         # 测试套件
```

### 阶段2（待实现）

```
ats_core/data/trade_recorder.py            # 交易记录器
ats_core/calibration/adaptive_calibrator.py  # 自适应校准
ats_core/optimization/gate_optimizer.py    # 闸门优化
ats_core/analysis/cost_analyzer.py         # 成本分析
ats_core/features/execution_cost_v2.py     # 成本估算v2
ats_core/monitoring/calibration_monitor.py # 校准监控
```

### 阶段3（未来）

```
ats_core/ml/data_collector.py              # ML数据采集
ats_core/ml/feature_engineering.py         # 特征工程
ats_core/ml/models/price_transformer.py    # Transformer模型
ats_core/ml/models/factor_optimizer.py     # XGBoost优化
ats_core/ml/models/regime_detector.py      # LSTM Regime
ats_core/pipeline/analyze_symbol_v73.py    # v7.3集成
```

---

## 总结

### v7系统演进哲学

```
理论 → 规则 → 统计 → 机器学习
  ↓      ↓      ↓        ↓
 v7.0  v7.2S1  v7.2S2  v7.2S3
(废弃) (完成) (进行中) (未来)
```

### 核心原则

1. **渐进式演进**：每个阶段独立可用，不依赖下一阶段
2. **数据驱动**：从规则 → 统计 → ML，逐步增加数据依赖
3. **风险可控**：成本逐步递增，随时可停在满意的阶段
4. **理论基础**：每个决策都有清晰的数学/统计/ML理论支撑

### 当前建议

**立即行动**：
1. ✅ 部署v7.2阶段1到生产环境（已完成）
2. 🔥 **启动v7.2阶段2实施**（从Week 1开始）
3. ⏰ 2个月后评估是否进入阶段3

**成功路径**：
```
现在 → 8周后（阶段2完成）→ 评估 → 决定是否阶段3
     ↓
   如果阶段2已经满意（Sharpe > 1.5）
   → 保持现状，持续优化
   → 节省$690/月成本
```

---

**详细方案**：见 [v7.2_stage2_stage3_roadmap.md](./v7.2_stage2_stage3_roadmap.md)
