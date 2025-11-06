# CryptoSignal v6.6 审查分支部署指南

## 分支信息

**当前分支**: `claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8`
**分支类型**: 系统合规性审查与仓库重构分支
**创建时间**: 2025-11-03
**主要内容**:
- v6.6 系统完整合规性审查报告
- 仓库全面重构分析方案
- 自动化修复和重构脚本
- 更新的 v6.6 规范文档

---

## 快速部署命令

### 方式一：一键部署（推荐）

```bash
cd ~/cryptosignal

# 拉取最新代码（审查分支）
git fetch origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git checkout claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git pull origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

# 运行完整部署脚本
./deploy_and_run.sh
```

### 方式二：首次部署（全新服务器）

```bash
cd ~

# 克隆仓库
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal

# 切换到审查分支
git checkout claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

# 运行部署脚本
./deploy_and_run.sh
```

---

## 部署脚本功能说明

`deploy_and_run.sh` 脚本已更新为当前审查分支，主要功能：

### ✅ 自动化功能
1. **Git 环境清理和代码同步**
   - 自动备份本地修改
   - 强制同步到远程最新版本
   - 自动处理冲突和未跟踪文件

2. **系统环境检测**
   - Python 3.8+ 检测
   - pip3 自动安装
   - git 版本检测
   - screen 可选检测

3. **依赖管理**
   - 自动检测缺失的 Python 包
   - 一键安装所有依赖
   - 网络失败自动重试（最多3次）

4. **配置验证**
   - v6.6 权重配置验证（6+4因子系统）
   - Binance API 配置检测
   - 首次部署引导

5. **生产环境启动**
   - 优先使用 Screen 会话（后台运行）
   - 回退到 nohup（如果 screen 未安装）
   - 自动创建日志目录

---

## 审查分支特性

### 📊 本分支包含以下审查报告

1. **COMPLIANCE_AUDIT_REPORT.md** (55页)
   - v6.6 系统完整合规性审查
   - 7个关键问题识别
   - 代码质量评分：85%
   - 文档合规评分：20%

2. **REPOSITORY_REFACTORING_PLAN.md** (100页)
   - 完整仓库重构策略
   - 识别14个冗余部署脚本
   - 识别3个重复归档目录
   - 组织评分：38% → 90%

3. **COMPREHENSIVE_AUDIT_SUMMARY.md**
   - 综合审查总结
   - 整体评分：54% → 84%（修复后）
   - 快速执行指南

4. **FACTOR_SYSTEM_v6.6_UPDATED.md**
   - 更新的 v6.6 因子系统规范
   - 完整的 6+4 架构定义
   - 从 v6.4 到 v6.6 的变更日志

### 🛠️ 自动化修复脚本

1. **fix_compliance_issues.sh**
   - 自动修复文档过时问题
   - 更新所有规范文档到 v6.6
   - 备份原有文档

2. **execute_refactoring.sh**
   - 4阶段仓库重构
   - Phase 1: 冗余脚本清理
   - Phase 2: 文档重组
   - Phase 3: 测试重组
   - Phase 4: 验证

3. **verify_refactoring.sh**
   - 8个验证检查点
   - 自动化通过/失败报告

---

## v6.6 系统架构（本分支验证通过）

### 核心因子系统（6+4架构）

**A层 - 6个方向因子**（权重总和100%）
- `T` (Trend 趋势): 24%
- `M` (Momentum 动量): 17%
- `C` (CVD 累积成交量差): 24%
- `V` (Volume 成交量): 12%
- `O` (Open Interest 持仓量): 17%
- `B` (Basis/Funding 基差/资金费率): 6%

**B层 - 4个调制器**（权重=0%，仅调制执行参数）
- `L` (Liquidity 流动性): 调制仓位大小
- `S` (Structure 结构): 调制置信度
- `F` (Funding Leading 资金领先): 调制有效期
- `I` (Independence 独立性): 调制成本

### 关键特性（已验证）

✅ **权重百分比系统**: 权重直接代表百分比，加权平均
✅ **软约束系统**: EV≤0 和 P<p_min 仅标记警告，不硬拒绝
✅ **防抖动系统**: K/N=1/2 确认，60s冷却，0.65阈值
✅ **标准化链**: 预平滑 → 鲁棒缩放 → 软winsor → ±100压缩
✅ **调制器链**: L→仓位，S→置信度，F→Teff，I→成本

---

## 部署后验证

### 1. 检查系统状态

```bash
# 查看运行的进程
ps aux | grep realtime_signal_scanner

# 如果使用 Screen
screen -r cryptosignal

# 如果使用 nohup
tail -f logs/scanner_*.log
```

### 2. 验证配置

```bash
# 验证权重配置
python3 -c "
import json
with open('config/params.json') as f:
    weights = json.load(f)['weights']
    core_sum = sum(weights[k] for k in ['T','M','C','V','O','B'])
    print(f'A层权重总和: {core_sum}%')
    print(f'B层调制器: L={weights[\"L\"]}, S={weights[\"S\"]}, F={weights[\"F\"]}, I={weights[\"I\"]}')
"
```

### 3. 执行审查建议（可选）

```bash
# 修复文档合规性问题
./fix_compliance_issues.sh

# 执行仓库重构
./execute_refactoring.sh

# 验证重构结果
./verify_refactoring.sh
```

---

## 与主分支的区别

| 特性 | 主分支 | 当前审查分支 |
|------|--------|--------------|
| **系统版本** | v6.6 | v6.6（已审查） |
| **文档状态** | 部分过时 | 已识别问题 |
| **仓库组织** | 混乱 | 已提供重构方案 |
| **部署脚本** | 14个冗余 | 已优化建议 |
| **审查报告** | 无 | 完整（155页+） |
| **修复脚本** | 无 | 3个自动化脚本 |

---

## 常见问题

### Q1: 这个分支可以直接用于生产吗？

**A**: 可以。本分支的**代码质量**与主分支一致（85%优秀），核心系统完全相同。额外包含的审查报告和脚本不会影响系统运行。

### Q2: 需要先执行修复脚本吗？

**A**: 不必须。修复脚本主要是：
- `fix_compliance_issues.sh`: 修复文档过时问题（不影响运行）
- `execute_refactoring.sh`: 清理冗余文件（优化仓库组织）
- 系统可以直接运行，修复脚本是可选的优化步骤

### Q3: 审查分支与之前的分支有何不同？

**A**:
- **之前分支** (`claude/understand-realtime-scanner-system-011CUjuCJDa9UX3sbxtR2HvA`): v6.6 系统实现
- **当前分支** (`claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8`): v6.6 审查和优化

两者核心代码相同，当前分支额外包含审查报告和改进方案。

### Q4: 如何在两个分支间切换？

```bash
# 切换到之前的实现分支
git checkout claude/understand-realtime-scanner-system-011CUjuCJDa9UX3sbxtR2HvA

# 切换回当前审查分支
git checkout claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
```

---

## 审查发现摘要

### 代码层面 ✅ (85% - 优秀)
- 因子计算逻辑正确
- 权重配置准确（A层100%, B层0%）
- v6.6 架构实现完整

### 文档层面 ⚠️ (20% - 需修复)
- 规范文档严重过时（v6.4 vs v6.6）
- 修复方案已提供

### 仓库组织 ⚠️ (38% - 需重构)
- 14个部署脚本严重冗余
- 3个归档目录分散
- 重构方案已提供

**整体评估**: 当前 54% → 修复后 84%

---

## 支持和反馈

如遇到问题：

1. 查看审查报告：`cat COMPREHENSIVE_AUDIT_SUMMARY.md`
2. 查看部署日志：`tail -f logs/scanner_*.log`
3. 检查进程状态：`ps aux | grep realtime_signal_scanner`
4. 查看 git 状态：`git status`

---

**最后更新**: 2025-11-03
**分支维护者**: Claude AI
**系统版本**: CryptoSignal v6.6 (审查验证版)
