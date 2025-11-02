# 规范文档整理计划

**目标**: 统一所有规范文档到standards目录，删除冗余，补充缺失

---

## 1️⃣ 当前状况分析

### README.md文件（6个）
```
✅ /README.md                              保留（项目入口）
❌ /deprecated/README.md                   删除（deprecated目录）
❌ /docs/README.md                         删除（重定向说明，不需要）
⚠️ /docs/archive/README.md                保留（归档说明）
⚠️ /docs/archive_2025-11-02/README.md     保留（归档说明）
❌ /standards/README.md                    删除（规范目录说明，用00_INDEX.md替代）
```

### newstandards目录（7个文件）
```
📄 DATA_LAYER.md (11.9KB)      → 移动到 standards/specifications/DATA_LAYER.md
📄 MODULATORS.md (1.6KB)       → 移动到 standards/specifications/MODULATORS.md
📄 PUBLISHING.md (8.3KB)       → 移动到 standards/specifications/PUBLISHING.md
📄 SCHEMAS.md (14.4KB)         → 移动到 standards/specifications/SCHEMAS.md
📄 STANDARDS.md (5.4KB)        → 移动到 standards/CORE_STANDARDS.md（核心技术规范）
❌ NEWCOIN_SPEC.md (2.7KB)     → 删除（简化版，已有完整版NEWCOIN.md）
❌ PROJECT_INDEX.md (3.8KB)    → 删除（旧索引，已有00_INDEX.md）
```

### standards/specifications/符号链接（4个）
```
❌ DATA_LAYER.md → ../../newstandards/DATA_LAYER.md    删除符号链接
❌ MODULATORS.md → ../../newstandards/MODULATORS.md    删除符号链接
❌ PUBLISHING.md → ../../newstandards/PUBLISHING.md    删除符号链接
❌ SCHEMAS.md → ../../newstandards/SCHEMAS.md          删除符号链接
```

---

## 2️⃣ 整理后的目录结构

```
cryptosignal/
├── README.md                                    ✅ 项目入口（唯一）
├── SPEC_MAP.md                                  ✅ 规范地图
│
├── standards/                                   📁 所有规范文档（唯一位置）
│   ├── 00_INDEX.md                             ⭐ 总索引
│   ├── 01_SYSTEM_OVERVIEW.md                   ⭐ 系统概览
│   ├── 02_ARCHITECTURE.md                      系统架构
│   ├── 03_VERSION_HISTORY.md                   版本历史
│   ├── CORE_STANDARDS.md                       ⭐⭐⭐ 核心技术规范（从newstandards/STANDARDS.md移动）
│   │
│   ├── specifications/                          📁 详细规范
│   │   ├── INDEX.md                            规范索引
│   │   ├── FACTOR_SYSTEM.md                    ⭐⭐⭐ 9+2因子系统
│   │   ├── NEWCOIN.md                          ⭐⭐⭐ 新币通道（22KB完整版）
│   │   ├── GATES.md                            四门系统
│   │   ├── DATA_LAYER.md                       ⭐⭐ 数据层架构（从newstandards移动）
│   │   ├── MODULATORS.md                       ⭐⭐ F/I调制器（从newstandards移动）
│   │   ├── PUBLISHING.md                       ⭐⭐ 发布系统（从newstandards移动）
│   │   ├── SCHEMAS.md                          ⭐⭐ 数据模式（从newstandards移动）
│   │   ├── DATAQUAL.md                         🆕 DataQual规范（新增）
│   │   └── EXECUTION.md                        🆕 执行系统规范（新增）
│   │
│   ├── deployment/                              📁 部署运维
│   │   ├── INDEX.md
│   │   ├── QUICK_START.md → ../QUICK_DEPLOY.md
│   │   ├── DEPLOYMENT_GUIDE.md → ../DEPLOYMENT_STANDARD.md
│   │   └── ...
│   │
│   └── configuration/                           📁 配置管理
│       └── PARAMS_SPEC.md
│
├── config/                                      📁 配置文件
│   └── params.json                             ⭐⭐⭐ 实际参数
│
├── docs/                                        📁 文档与分析
│   ├── VALIDATION_REPORT_2025-11-02.md         验证报告
│   ├── SPEC_COMPLETENESS_ANALYSIS.md           完整性分析
│   ├── archive/                                 归档
│   │   └── README.md                           （保留）
│   └── archive_2025-11-02/                      归档
│       └── README.md                           （保留）
│
└── deprecated/                                  📁 废弃代码
    └── README.md                               ❌ 删除
```

---

## 3️⃣ 需要补充的规范文档

### 🆕 standards/specifications/DATAQUAL.md
**内容**: DataQual计算详细规范
- 各分量计算公式 (miss/oo_order/drift/mismatch)
- 权重配置 (w_h/w_o/w_d/w_m)
- 降级策略
- 阈值设定 (0.90/0.88)

**依据**: VALIDATION_REPORT Issue #1 - 缺失30%

---

### 🆕 standards/specifications/EXECUTION.md
**内容**: 执行系统详细规范
- 订单管理流程（开仓/平仓/撤单）
- 成交确认机制
- 滑点控制算法
- 订单分片策略
- 厚区检测算法
- 止损止盈执行

**依据**: VALIDATION_REPORT Issue #2 - 缺失30%

---

### 📝 standards/specifications/WEBSOCKET.md
**内容**: WebSocket管理规范
- 连接池管理
- 重连策略详细实现
- 心跳监控机制
- 数据对账流程
- 组合流订阅策略

**依据**: SPEC_COMPLETENESS_ANALYSIS - 缺失40%

---

## 4️⃣ 需要修改完善的文档

### standards/CORE_STANDARDS.md (从newstandards/STANDARDS.md)
**修改内容**:
1. 补充L因子权重 (12.0%)
2. 补充B因子权重 (4.0%)
3. 权重基线更新: `T18/M12/C18/S10/V10/O12/L12/B4/Q4` ✅
4. 添加数据源完整映射（Binance API端点详细说明）

---

### standards/specifications/DATA_LAYER.md (从newstandards)
**修改内容**:
1. 补充REST API频率限制处理策略
2. 补充WebSocket重连具体实现（指向WEBSOCKET.md）
3. 补充数据缓存机制详细说明
4. 添加异常处理策略

---

### standards/specifications/MODULATORS.md (从newstandards)
**修改内容**:
1. 扩展F因子计算详细公式
2. 扩展I因子计算详细公式
3. 添加调制器参数表
4. 添加新币专用调制器参数

---

### standards/specifications/GATES.md
**修改内容**:
1. 扩展为完整规范（当前只有394字节）
2. 详细描述四门检查逻辑
3. 添加阈值参数表
4. 添加开仓/维持滞回机制

---

### standards/00_INDEX.md
**修改内容**:
1. 更新文档路径（移除newstandards引用）
2. 添加新增文档索引（DATAQUAL.md, EXECUTION.md等）
3. 更新追溯矩阵

---

### standards/01_SYSTEM_OVERVIEW.md
**修改内容**:
1. 更新架构图（反映v6.4 Phase 2）
2. 更新文档路径引用

---

## 5️⃣ 需要删除的文件

```bash
# README.md（3个）
rm /home/user/cryptosignal/deprecated/README.md
rm /home/user/cryptosignal/docs/README.md
rm /home/user/cryptosignal/standards/README.md

# newstandards简化/旧文件（2个）
rm /home/user/cryptosignal/newstandards/NEWCOIN_SPEC.md
rm /home/user/cryptosignal/newstandards/PROJECT_INDEX.md

# 符号链接（4个）
rm /home/user/cryptosignal/standards/specifications/DATA_LAYER.md
rm /home/user/cryptosignal/standards/specifications/MODULATORS.md
rm /home/user/cryptosignal/standards/specifications/PUBLISHING.md
rm /home/user/cryptosignal/standards/specifications/SCHEMAS.md
```

---

## 6️⃣ 文件移动操作

```bash
# 移动newstandards核心文件到standards/specifications/
mv /home/user/cryptosignal/newstandards/DATA_LAYER.md \
   /home/user/cryptosignal/standards/specifications/DATA_LAYER.md

mv /home/user/cryptosignal/newstandards/MODULATORS.md \
   /home/user/cryptosignal/standards/specifications/MODULATORS.md

mv /home/user/cryptosignal/newstandards/PUBLISHING.md \
   /home/user/cryptosignal/standards/specifications/PUBLISHING.md

mv /home/user/cryptosignal/newstandards/SCHEMAS.md \
   /home/user/cryptosignal/standards/specifications/SCHEMAS.md

# 移动核心技术规范到standards/
mv /home/user/cryptosignal/newstandards/STANDARDS.md \
   /home/user/cryptosignal/standards/CORE_STANDARDS.md

# 删除newstandards目录（清空后）
rmdir /home/user/cryptosignal/newstandards
```

---

## 7️⃣ 逻辑一致性检查清单

### A. 权重配置一致性
- [ ] CORE_STANDARDS.md权重: T18/M12/C18/S10/V10/O12/L12/B4/Q4
- [ ] FACTOR_SYSTEM.md权重: T18/M12/C18/S10/V10/O12/L12/B4/Q4
- [ ] README.md权重: T18/M12/C18/S10/V10/O12/L12/B4/Q4
- [ ] config/params.json权重: T18/M12/C18/S10/V10/O12/L12/B4/Q4
- [ ] 总和: 100.0% ✅

### B. 版本号一致性
- [ ] 所有文档版本: v6.4 Phase 2
- [ ] 系统描述: 9+2因子体系

### C. 文档引用路径
- [ ] 所有指向newstandards/的路径更新为standards/specifications/
- [ ] 所有指向../newstandards/的路径更新
- [ ] 00_INDEX.md追溯矩阵更新

### D. 因子系统命名
- [ ] 统一使用"9+2因子系统"
- [ ] A层9因子: T/M/C/S/V/O/L/B/Q
- [ ] B层2调制器: F/I

### E. 新币通道一致性
- [ ] Phase 2实现范围一致
- [ ] 数据流架构描述一致
- [ ] Phase 3-4待实现内容一致

### F. 四门系统一致性
- [ ] Gate 1-4定义一致
- [ ] 阈值参数一致
- [ ] DataQual计算一致（补充后）

### G. 公式一致性
- [ ] AVWAP公式: Σ(P_typical * V) / ΣV
- [ ] ZLEMA公式: ZLEMA_t = α(2P_t - P_{t-lag}) + (1-α)ZLEMA_{t-1}
- [ ] 标准化链: 预平滑 → 稳健缩放 → 软winsor → tanh压缩

---

## 8️⃣ 执行顺序

1. **创建新文档**（避免引用丢失）
   - DATAQUAL.md
   - EXECUTION.md
   - WEBSOCKET.md

2. **移动文件**（保持引用完整）
   - newstandards/*.md → standards/
   - 重命名STANDARDS.md → CORE_STANDARDS.md

3. **删除符号链接和冗余文件**
   - 删除specifications/中的4个符号链接
   - 删除3个多余README.md
   - 删除newstandards/简化文件

4. **修改完善现有文档**
   - 更新权重、路径、引用
   - 补充缺失内容

5. **删除空目录**
   - rmdir newstandards/

6. **更新索引和地图**
   - 00_INDEX.md
   - SPEC_MAP.md

7. **逻辑一致性检查**
   - 运行检查清单
   - 验证所有引用

8. **创建整理报告**
   - 记录所有变更
   - 更新SPEC_MAP.md

---

## 9️⃣ 完成后的验证

```bash
# 验证目录结构
tree standards/

# 验证没有指向newstandards的引用
grep -r "newstandards" standards/

# 验证权重配置一致性
grep -r "T.*18" standards/ config/

# 验证README.md数量（应该只有1个+2个归档）
find . -name "README.md" -type f | wc -l  # 应该=3

# 验证newstandards目录已删除
ls -la newstandards/  # 应该不存在
```

---

## 🎯 预期成果

### 文档数量
- 核心规范: 13个（增加3个）
- 部署文档: 保持不变
- 配置文档: 保持不变
- README.md: 1个（根目录）+ 2个归档

### 完整度提升
- 因子系统: 95% → 100% ✅
- 四门系统: 90% → 100% ✅
- 执行系统: 70% → 95% ✅
- 数据获取: 60% → 85% ✅

### 可重建性
- 核心算法: 90% → 100% ✅
- 完整系统: 70% → 90% ✅

---

**创建时间**: 2025-11-02
**执行人**: 待执行
**预计时间**: 2-3小时（文档整理 + 内容补充）
