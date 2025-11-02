# 规范文档管理制度

> **版本**: v1.0
> **生效日期**: 2025-11-02
> **强制执行**: ✅ 所有代码修改必须遵守本规范

---

## 🎯 核心原则

### ⚠️ 强制规定

**每次修改系统时，必须同步更新规范文档！**

- 修改代码 ➜ 必须更新相关规范文档
- 修改配置 ➜ 必须更新配置规范
- 修改架构 ➜ 必须更新架构文档
- 修改部署流程 ➜ 必须更新部署规范

---

## 📁 文档组织结构

### standards/ - 所有规范文档的唯一位置

```
standards/
├── README.md                      # 规范文档索引（必读）
├── DOCUMENTATION_RULES.md         # 本文档（规范文档管理制度）
│
├── ARCHITECTURE.md                # 系统架构规范
├── CONFIGURATION_GUIDE.md         # 配置规范
├── DEPLOYMENT_STANDARD.md         # 部署规范
├── DEPLOYMENT.md                  # 部署操作指南
├── DEVELOPMENT_WORKFLOW.md        # 开发工作流规范
├── MODIFICATION_RULES.md          # 代码修改规范
│
├── QUICK_DEPLOY.md                # 快速部署参考卡
├── QUICK_REFERENCE.md             # 快速参考手册
├── SERVER_OPERATIONS.md           # 服务器运维命令清单
│
├── SYSTEM_OVERVIEW.md             # 系统总览
├── TELEGRAM_SETUP.md              # Telegram 配置指南
├── VERSION_HISTORY.md             # 版本历史记录
│
└── STANDARDIZATION_REPORT.md      # 标准化报告
```

### docs/ - 技术文档和历史记录

```
docs/
├── README.md                      # 技术文档索引
├── COIN_SELECTION_OPTIMIZATION.md # 选币优化说明
├── DATA_LAYER_ARCHITECTURE.md     # 数据层架构
├── SPEC_DIGEST.md                 # 规格摘要
│
└── archive/                       # 历史文档归档
    └── SYSTEM_FIX_PLAN.md         # v6.0 修复计划（已完成）
```

### 根目录 - 仅保留核心入口文件

```
/
├── README.md                      # 项目入口文档（必须保留）
├── deploy.sh                      # 部署脚本符号链接（指向 deploy_v6.1.sh）
└── deploy_v6.1.sh                 # 实际部署脚本
```

---

## 📋 文档分类规则

### 1️⃣ 规范性文档（必须放在 standards/）

- **架构规范**: ARCHITECTURE.md
- **配置规范**: CONFIGURATION_GUIDE.md
- **开发规范**: DEVELOPMENT_WORKFLOW.md, MODIFICATION_RULES.md
- **部署规范**: DEPLOYMENT_STANDARD.md, DEPLOYMENT.md
- **操作规范**: SERVER_OPERATIONS.md, QUICK_DEPLOY.md

### 2️⃣ 技术文档（放在 docs/）

- 技术设计文档
- 优化说明文档
- 审计报告
- 实现计划

### 3️⃣ 历史文档（放在 docs/archive/）

- 已完成的修复计划
- 旧版本的设计文档
- 不再使用的规范

### 4️⃣ 入口文档（根目录）

- README.md - 项目总入口
- 快速启动脚本（deploy.sh 符号链接）

---

## 🔄 文档更新流程

### 标准流程（强制执行）

```
修改系统
   ↓
识别受影响的规范文档
   ↓
同步更新规范文档
   ↓
在 Git Commit Message 中注明文档更新
   ↓
提交代码和文档
```

### Commit Message 规范

```bash
# ✅ 正确示例
git commit -m "feat: 新增多空对称选币机制

- 实现波动率优先算法（70%权重）
- 更新 standards/ARCHITECTURE.md § 选币机制
- 更新 docs/COIN_SELECTION_OPTIMIZATION.md"

# ❌ 错误示例（只提交代码，未更新文档）
git commit -m "feat: 新增多空对称选币机制"
```

---

## 📝 文档更新检查清单

### 修改代码时，检查是否需要更新：

#### 架构变更
- [ ] `standards/ARCHITECTURE.md` - 系统架构
- [ ] `standards/SYSTEM_OVERVIEW.md` - 系统总览

#### 配置变更
- [ ] `standards/CONFIGURATION_GUIDE.md` - 配置规范
- [ ] `standards/QUICK_REFERENCE.md` - 快速参考

#### 部署流程变更
- [ ] `standards/DEPLOYMENT_STANDARD.md` - 部署规范
- [ ] `standards/DEPLOYMENT.md` - 部署指南
- [ ] `standards/QUICK_DEPLOY.md` - 快速部署参考
- [ ] `standards/SERVER_OPERATIONS.md` - 运维命令清单

#### 开发流程变更
- [ ] `standards/DEVELOPMENT_WORKFLOW.md` - 开发工作流
- [ ] `standards/MODIFICATION_RULES.md` - 修改规范

#### 版本更新
- [ ] `standards/VERSION_HISTORY.md` - 版本历史

---

## 🚫 禁止行为

### ❌ 严禁以下操作：

1. **在根目录创建新的规范文档**
   - 所有规范必须放在 `standards/`

2. **修改代码但不更新文档**
   - 代码和文档必须同步更新

3. **创建重复/冗余的文档**
   - 同一主题只能有一个权威文档
   - 删除旧文档前必须确保新文档已包含所有重要信息

4. **不遵守文档命名规范**
   - 使用大写字母和下划线: `DEPLOYMENT_STANDARD.md`
   - 不使用中文文件名

5. **在提交信息中不注明文档更新**
   - 必须在 commit message 中明确列出更新的文档

---

## 📊 文档维护责任

### 每次 Pull Request 必须包含：

1. **代码变更** - 功能实现/Bug修复
2. **文档更新** - 同步更新相关规范
3. **更新说明** - 在 PR 描述中列出更新的文档

### Code Review 检查项：

- [ ] 代码实现是否符合规范
- [ ] 规范文档是否已同步更新
- [ ] 文档更新是否完整准确
- [ ] Commit message 是否注明文档更新

---

## 🔍 文档质量标准

### 规范文档必须包含：

1. **版本信息**
   - 版本号
   - 更新日期
   - 适用系统版本

2. **目标和范围**
   - 规范的目的
   - 适用范围

3. **详细说明**
   - 清晰的规则定义
   - 正确/错误示例
   - 检查清单

4. **引用和关联**
   - 相关文档的链接
   - 依赖关系说明

---

## 🎓 文档更新示例

### 场景：修改选币算法

#### 1. 代码修改
```python
# ats_core/pipeline/batch_scan_optimized.py
def calc_score(symbol):
    volatility = abs(data.get('change_pct', 0))  # 多空对称
    liquidity = data.get('volume', 0) / max_volume
    return volatility * 0.7 + liquidity * 0.3 * 100
```

#### 2. 文档更新
- ✅ 更新 `standards/ARCHITECTURE.md` - 添加选币机制说明
- ✅ 创建 `docs/COIN_SELECTION_OPTIMIZATION.md` - 详细技术文档
- ✅ 更新 `standards/VERSION_HISTORY.md` - 记录 v6.2 变更

#### 3. 提交信息
```bash
git commit -m "feat: 选币机制优化 - 多空对称 + 波动率优先（v6.2）

变更内容：
- 实现多空对称选币算法（abs(波动率) * 70% + 流动性 * 30%）
- 扫描币种从 140 提升到 200
- 预期做空信号增加 2-3 倍

文档更新：
- 更新 standards/ARCHITECTURE.md § 选币机制
- 新增 docs/COIN_SELECTION_OPTIMIZATION.md
- 更新 standards/VERSION_HISTORY.md v6.2 章节"
```

---

## 🔗 相关规范

- [代码修改规范](MODIFICATION_RULES.md) - 代码修改流程和规则
- [开发工作流](DEVELOPMENT_WORKFLOW.md) - 开发标准流程
- [部署规范](DEPLOYMENT_STANDARD.md) - 部署流程规范

---

## 📞 问题反馈

如有关于文档管理的疑问：
1. 查阅本规范
2. 查看 `standards/README.md`
3. 参考历史 commit 中的文档更新示例

---

**记住：代码和文档必须同步更新！这是强制要求！**
