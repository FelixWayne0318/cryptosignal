# CryptoSignal v6.4 Phase 2 规范文档地图

> **快速回答**:
> - 📍 **所有规范文档位置**: `standards/` (已完成整合)
> - ✅ **能否重建系统**: 核心算法可以（90%完整），完整生产系统需补充工程细节
> - 📖 **详细分析**: 见 `docs/SPEC_COMPLETENESS_ANALYSIS.md`

---

## 🚀 快速开始

### 我想了解系统
👉 从这里开始: **`standards/00_INDEX.md`** (总索引)

### 我想重建系统
👉 按此顺序阅读:
1. **`standards/CORE_STANDARDS.md`** - 完整技术规范（核心算法）⭐⭐⭐
2. **`standards/specifications/FACTOR_SYSTEM.md`** - 9+2因子系统 ⭐⭐⭐
3. **`standards/specifications/NEWCOIN.md`** - 新币通道规范 ⭐⭐⭐
4. **`standards/specifications/DATA_LAYER.md`** - 数据层架构 ⭐⭐
5. **`standards/specifications/PUBLISHING.md`** - 四门系统 ⭐⭐
6. **`config/params.json`** - 实际参数配置 ⭐⭐⭐

---

## 📚 规范文档结构

### 第一层：总入口
```
standards/00_INDEX.md          # 🎯 从这里开始
```

### 第二层：核心规范

#### A. 算法与模型（最重要，90%完整）
```
standards/CORE_STANDARDS.md                     # ⭐⭐⭐ 完整技术规范（A/B/C层）
standards/specifications/FACTOR_SYSTEM.md       # ⭐⭐⭐ 9+2因子系统
standards/specifications/NEWCOIN.md             # ⭐⭐⭐ 新币通道（22KB详细）
standards/specifications/MODULATORS.md          # ⭐⭐  F/I调制器
```

**包含**: 所有因子计算公式、标准化链、评分系统、权重配置

#### B. 数据与发布（80%完整）
```
standards/specifications/DATA_LAYER.md      # ⭐⭐  数据源、API、WebSocket
standards/specifications/PUBLISHING.md      # ⭐⭐  四门系统、防抖动
standards/specifications/SCHEMAS.md         # ⭐⭐  数据结构定义
standards/specifications/GATES.md           # ⭐⭐  四门规范
```

**包含**: 数据获取、质量监控、发布条件、信号格式

#### C. 配置与参数（90%完整）
```
config/params.json              # ⭐⭐⭐ 实际生效配置
```

**包含**: 权重、阈值、发布参数、新币参数

### 第三层：系统与运维

#### D. 部署与运维（60%完整）
```
standards/QUICK_DEPLOY.md          # 快速部署
standards/DEPLOYMENT_STANDARD.md   # 部署标准
standards/SERVER_OPERATIONS.md     # 服务器运维
standards/TELEGRAM_SETUP.md        # Telegram配置
```

#### E. 开发指南（50%完整）
```
standards/DEVELOPMENT_WORKFLOW.md  # 开发流程
standards/CONFIGURATION_GUIDE.md   # 配置指南
standards/MODIFICATION_RULES.md    # 修改规则
```

---

## 🎯 按需求查找规范

### 我想实现因子计算
1. **`standards/CORE_STANDARDS.md § 2`** - 查看完整公式
2. **`standards/specifications/FACTOR_SYSTEM.md`** - 查看因子定义
3. **`config/params.json`** - 查看权重配置

**完整度**: ✅ 95% - 可直接实现

---

### 我想实现新币通道
1. **`standards/specifications/NEWCOIN.md`** - 完整规范（22KB）
2. **代码参考**: `ats_core/data_feeds/newcoin_data.py`

**完整度**: ✅ 80% (Phase 2完整，Phase 3-4待实现)

---

### 我想实现四门系统
1. **`standards/specifications/PUBLISHING.md § 四门系统`**
2. **`standards/specifications/GATES.md`**
3. **代码参考**: `ats_core/gates/integrated_gates.py`

**完整度**: ⚠️ 90% - 需补充DataQual计算细节

---

### 我想配置权重
1. **`config/params.json`** - 直接修改
2. **`standards/specifications/FACTOR_SYSTEM.md`** - 理解权重含义
3. **验证**: 确保A层总和=100%

**完整度**: ✅ 100%

---

### 我想部署系统
1. **`standards/QUICK_DEPLOY.md`** - 快速部署
2. **`./deploy_and_run.sh`** - 自动化脚本
3. **`standards/SERVER_OPERATIONS.md`** - 运维指南

**完整度**: ✅ 70% - 基本可用

---

## 📊 规范完整度总览

| 模块 | 规范文档 | 完整度 | 可重建 | 说明 |
|------|---------|--------|--------|------|
| **9因子计算** | STANDARDS.md § 2 | 95% | ✅ 是 | 公式完整，可直接实现 |
| **标准化链** | STANDARDS.md § 2.0 | 100% | ✅ 是 | 完整规范 |
| **评分系统** | FACTOR_SYSTEM.md | 100% | ✅ 是 | 权重配置明确 |
| **F/I调制器** | MODULATORS.md | 95% | ✅ 是 | 公式完整 |
| **四门系统** | PUBLISHING.md | 90% | ⚠️ 需补充 | 缺DataQual细节 |
| **新币通道** | NEWCOIN.md | 80% | ⚠️ 部分 | Phase 2完整 |
| **数据获取** | DATA_LAYER.md | 60% | ⚠️ 需补充 | 需API实现细节 |
| **执行系统** | STANDARDS.md § 3 | 70% | ⚠️ 需补充 | 缺订单管理细节 |
| **部署运维** | DEPLOYMENT*.md | 60% | ⚠️ 需补充 | 基本流程完整 |

---

## 🔑 关键规范文档（必读）

### Top 5 核心规范 ⭐⭐⭐
1. **`standards/CORE_STANDARDS.md`** (5.4KB)
   - A层9因子完整公式
   - 统一标准化链
   - 执行系统基础规范

2. **`standards/specifications/FACTOR_SYSTEM.md`** (已修复)
   - 9+2因子系统概览
   - 权重配置: T18/M12/C18/S10/V10/O12/L12/B4/Q4
   - 架构分层说明

3. **`standards/specifications/NEWCOIN.md`** (22KB)
   - 新币通道完整规范
   - Phase 2-4实施路线图
   - AVWAP/ZLEMA计算公式

4. **`standards/specifications/PUBLISHING.md`** (8.3KB)
   - 四门系统完整规范
   - 防抖动机制
   - 信号发布条件

5. **`config/params.json`**
   - 所有实际生效参数
   - 权重、阈值、发布参数

---

## ⚠️ 规范缺失的部分

### 需要补充的规范（影响重建）
1. **DataQual计算细节** (缺失30%)
   - 各分量权重: w_h/w_o/w_d/w_m
   - 降级策略细节

2. **执行系统实现** (缺失30%)
   - 订单管理流程
   - 成交确认逻辑
   - 滑点控制算法

3. **WebSocket管理** (缺失40%)
   - 连接池管理
   - 重连策略细节
   - 数据对账机制

### 依赖代码/经验的部分（难以规范化）
- 异常处理策略
- 性能优化方法
- 生产环境调优
- 监控告警配置

---

## 🎓 重建系统指南

### 最小可行系统（6-8周）
**仅需规范文档即可重建**:
1. ✅ 9因子计算引擎
2. ✅ 统一标准化链
3. ✅ 评分与概率系统
4. ✅ 四门验证（需补充DataQual）
5. ✅ 新币通道（Phase 2）

### 完整生产系统（3-6个月）
**需补充工程细节**:
- 数据获取优化
- 执行系统完善
- 异常处理
- 性能优化
- 监控告警

---

## 📖 推荐阅读顺序

### 新用户（理解系统）
1. `standards/00_INDEX.md` - 总索引
2. `standards/01_SYSTEM_OVERVIEW.md` - 系统概览
3. `standards/specifications/FACTOR_SYSTEM.md` - 因子系统
4. `README.md` - 项目说明

### 开发者（重建系统）
1. `standards/CORE_STANDARDS.md` - 完整技术规范 ⭐
2. `standards/specifications/NEWCOIN.md` - 新币通道 ⭐
3. `standards/specifications/PUBLISHING.md` - 四门系统 ⭐
4. `standards/specifications/DATA_LAYER.md` - 数据层
5. `config/params.json` - 参数配置 ⭐

### 运维人员（部署系统）
1. `standards/QUICK_DEPLOY.md` - 快速部署
2. `./deploy_and_run.sh` - 部署脚本
3. `standards/SERVER_OPERATIONS.md` - 运维指南
4. `standards/TELEGRAM_SETUP.md` - Telegram配置

---

## 🔍 查找规范的方法

### 方法1: 从索引查找
```bash
# 查看总索引
cat standards/00_INDEX.md

# 查看规范索引
cat standards/specifications/INDEX.md
```

### 方法2: 关键词搜索
```bash
# 搜索"权重"相关规范
grep -r "权重" standards/

# 搜索"AVWAP"计算公式
grep -r "AVWAP" standards/specifications/

# 搜索特定因子"T趋势"
grep -r "T趋势" standards/
```

### 方法3: 按模块查找
- **因子计算**: `standards/CORE_STANDARDS.md § 2`
- **新币通道**: `standards/specifications/NEWCOIN.md`
- **四门系统**: `standards/specifications/PUBLISHING.md`
- **数据层**: `standards/specifications/DATA_LAYER.md`
- **配置**: `config/params.json`

---

## 📝 规范文档维护

### 最新状态（2025-11-02）
- ✅ 权重配置已统一（T18/M12/C18/S10/V10/O12/L12/B4/Q4）
- ✅ 版本号已统一（v6.4 Phase 2）
- ✅ 因子系统命名已统一（9+2因子体系）
- ⚠️ FACTOR_SYSTEM.md待完善（需合并CORE_STANDARDS.md详细内容）

### 待办事项
- [ ] 补充DataQual计算细节
- [ ] 补充执行系统实现规范
- [ ] 补充WebSocket管理规范
- [x] ~~合并newstandards到standards~~（已完成 2025-11-02）

---

## 🎯 结论

### 能否仅通过规范文档重建系统？

**✅ 核心算法层 (90%完整) - 可以重建**
- 9因子计算、标准化链、评分系统、新币通道Phase 2

**⚠️ 执行与数据层 (70%完整) - 可重建，需补充细节**
- 数据获取、四门系统、执行策略

**❌ 工程实现 (40%完整) - 需实践经验**
- 异常处理、性能优化、监控告警

**重建时间估算**:
- 核心功能: 6-8周
- 生产级系统: 3-6个月

---

**文档位置**: `/home/user/cryptosignal/SPEC_MAP.md`
**详细分析**: `/home/user/cryptosignal/docs/SPEC_COMPLETENESS_ANALYSIS.md`
**验证报告**: `/home/user/cryptosignal/docs/VALIDATION_REPORT_2025-11-02.md`
