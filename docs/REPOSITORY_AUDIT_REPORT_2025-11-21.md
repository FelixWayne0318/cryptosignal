# CryptoSignal 仓库整理与因子审计报告

**日期**: 2025-11-21
**版本**: v7.6.0
**分支**: `claude/reorganize-audit-system-01BUG6SrCk68u3VFQspLpmhw`

---

## 一、仓库整理摘要

### 1.1 删除的文件

| 路径 | 删除原因 |
|------|----------|
| `docs/archived/v7.2/` (全部6个文件) | v7.2已过时，当前版本v7.6.0 |
| `docs/archived/versions/` | 废弃的版本草案 |
| `archive/` | 旧修复脚本，已无用 |
| `deploy/scripts/restart_and_verify.sh` | 与其他重启脚本功能重复 |

### 1.2 移动的文件

| 源路径 | 目标路径 | 原因 |
|--------|----------|------|
| `scripts/diagnose_step1_full.py` | `diagnose/` | 诊断脚本应放在diagnose/ |
| `scripts/debug_backtest_structure.py` | `tests/` | 测试/调试脚本应放在tests/ |
| `scripts/validate_p0_fix.py` | `tests/` | 验证脚本应放在tests/ |
| `docs/deploy_server_v740_TEMPLATE.sh` | `deploy/templates/` | 部署模板应放在deploy/ |

### 1.3 整理后的目录结构

```
cryptosignal/
├── ats_core/           # 核心代码（保持不变）
│   ├── decision/       # 四步决策系统
│   ├── features/       # 因子计算
│   ├── scoring/        # 评分系统
│   └── ...
├── config/             # 配置文件
├── diagnose/           # 诊断工具（整合完成）
├── deploy/             # 部署脚本
│   ├── scripts/
│   └── templates/      # 新增
├── docs/               # 文档（整合完成）
├── scripts/            # 运行脚本
├── standards/          # 规范文档
└── tests/              # 测试文件（整合完成）
```

---

## 二、因子系统审计结果

### 2.1 整体评分: A-

系统架构设计专业，分层清晰，配置管理完善。主要风险在于部分实现细节需要修复。

### 2.2 严重问题 (Critical Issues) - 需紧急修复

#### C1. Step2方向符号来源不一致

**文件**: `ats_core/decision/step2_timing.py:629-635`

**问题**: Step2的`direction_sign`从T因子判断，而Step1从加权合成分判断。当T因子与其他因子方向不一致时，会导致TrendStage调整应用到错误的方向。

**修复方案**: Step2应接收Step1的`direction_score`作为参数

#### C2. CVD组合权重使用全局成交额

**文件**: `ats_core/features/cvd.py:396-414`

**问题**: 使用整个区间的总成交额计算权重，无法捕捉短期权重变化

**修复方案**: 实现逐bar动态权重计算

#### C3. Enhanced F scale参数过小

**文件**: `ats_core/decision/step2_timing.py:531`

**问题**: scale=20.0，但输入范围约[-50, 50]，导致tanh快速饱和

**修复方案**: 将scale调整为50-100

### 2.3 重要问题 (Major Issues) - 建议本月修复

| 编号 | 问题 | 文件 | 影响 |
|------|------|------|------|
| M1 | ATR函数重复实现 | step2/step3 | 维护成本 |
| M2 | O因子价格对齐问题 | open_interest.py:286-295 | 数据准确性 |
| M3 | T-M因子信息重叠 | momentum.py | 多重共线性 |
| M4 | Gate4矛盾阈值过高 | step4_quality.py:186-203 | 漏检矛盾 |
| M5 | I因子置信度映射不平滑 | step1_direction.py:204-225 | 信号稳定性 |
| M6 | B因子潜在除零风险 | fund_leading.py:343 | 异常值 |

### 2.4 改进建议 (Suggestions)

1. **S1**: 添加JSON Schema配置验证
2. **S2**: 实现因子计算结果缓存
3. **S3**: 统一StandardizationChain工厂
4. **S4**: 添加因子相关性实时监控
5. **S5**: Step3入场价计算考虑滑点
6. **S6**: 统一因子降级事件追踪

### 2.5 设计亮点 (Highlights)

1. **H1**: 优秀的四步分层决策架构
2. **H2**: v7.6.0方向敏感强度映射设计精妙
3. **H3**: Enhanced F v2正确解决价格自相关
4. **H4**: 完善的配置化和零硬编码
5. **H5**: 异常值检测和处理机制
6. **H6**: 拥挤度检测防追高机制
7. **H7**: 名义OI解决跨币种比较问题
8. **H8**: Hard Veto规则防作死
9. **H9**: BTC特殊处理合理
10. **H10**: TrendStage模块防追高/追跌

---

## 三、修复优先级建议

### 紧急 (本周)
- C1: Step2方向符号来源统一

### 重要 (下周)
- C2: CVD动态权重
- C3: Enhanced F scale调优

### 中期 (本月)
- M1-M6: 所有Major问题

### 长期优化
- S1-S6: 改进建议

---

## 四、核心文件依赖链

```
setup.sh
  └── scripts/realtime_signal_scanner.py
        └── ats_core/pipeline/batch_scan_optimized.py
              └── ats_core/pipeline/analyze_symbol.py
                    └── ats_core/decision/four_step_system.py
                          ├── step1_direction.py
                          ├── step2_timing.py
                          ├── step3_risk.py
                          └── step4_quality.py
```

---

## 五、后续行动计划

1. **本次提交**: 仓库整理（删除/移动文件）
2. **下次开发**: 修复C1 Step2方向符号问题
3. **持续改进**: 按优先级修复M1-M6问题
4. **长期规划**: 实施S1-S6优化建议

---

**报告生成**: Claude Code
**审计标准**: 世界顶级量化交易系统标准
