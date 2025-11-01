# 文档目录说明

> ⚠️ **重要**: 所有规范性文档已迁移至 `standards/` 目录

---

## 📂 目录结构

```
cryptosignal/
│
├── standards/              # ⭐ 规范文档目录（主要维护位置）
│   ├── README.md           # 规范文档索引
│   ├── SYSTEM_OVERVIEW.md  # 系统总览
│   ├── QUICK_REFERENCE.md  # 快速参考
│   ├── MODIFICATION_RULES.md # 修改规则
│   ├── ARCHITECTURE.md     # 架构说明
│   ├── CONFIGURATION_GUIDE.md # 配置指南
│   ├── DEVELOPMENT_WORKFLOW.md # 开发工作流
│   └── TELEGRAM_SETUP.md   # Telegram 设置
│
├── docs/                   # 文档目录（归档和临时文档）
│   ├── README.md           # 本文件
│   └── archive/            # 历史/临时文档归档
│       ├── ACCEPTANCE_CHECKLIST.md
│       ├── CHANGE_PROPOSAL_v2.md
│       ├── COMPLIANCE_REPORT.md
│       ├── IMPLEMENTATION_PLAN_v2.md
│       ├── SHADOW_RUN_REPORT.md
│       └── SPEC_DIGEST.md
│
└── ...
```

---

## 🎯 快速访问

### **查看系统规范**
→ 前往 [`../standards/README.md`](../standards/README.md)

### **查看核心文档**
- [系统总览](../standards/SYSTEM_OVERVIEW.md) - 新对话框必读
- [快速参考](../standards/QUICK_REFERENCE.md) - 1分钟速查
- [修改规则](../standards/MODIFICATION_RULES.md) - 代码修改规范

---

## 📝 文档分类说明

### **standards/** - 规范文档
- **用途**: 长期维护的系统规范
- **修改**: 需要更新系统规范时修改此目录
- **特点**: 单一信息源，避免重复

### **docs/archive/** - 归档文档
- **用途**: 历史报告、临时清单、实施计划
- **修改**: 一般不修改，仅作历史参考
- **特点**: 时间戳明确，记录演进过程

---

## 🔄 维护原则

### ✅ 正确做法
```bash
# 修改系统规范
vim standards/SYSTEM_OVERVIEW.md
git commit -m "docs: 更新系统总览"

# 查看规范
cat standards/QUICK_REFERENCE.md
```

### ❌ 错误做法
```bash
# 不要在 docs/ 创建新的规范文档
vim docs/NEW_STANDARD.md  # ❌

# 不要重复规范内容
# 应该引用 standards/，而不是复制内容
```

---

## 🗂️ archive/ 目录内容

临时/历史文档，仅供参考：

- **ACCEPTANCE_CHECKLIST.md** - 验收清单（2025-10-31）
- **CHANGE_PROPOSAL_v2.md** - 变更提案 v2.0
- **COMPLIANCE_REPORT.md** - 合规性报告
- **IMPLEMENTATION_PLAN_v2.md** - 实施计划 v2.0
- **SHADOW_RUN_REPORT.md** - 影子运行报告
- **SPEC_DIGEST.md** - 规范消化摘要

这些文档记录了系统演进历史，不建议修改。

---

## 💡 常见问题

**Q: 我要修改权重配置，应该看哪个文档？**
A: 查看 [`standards/CONFIGURATION_GUIDE.md`](../standards/CONFIGURATION_GUIDE.md) 和 [`standards/QUICK_REFERENCE.md`](../standards/QUICK_REFERENCE.md)

**Q: 我要修改 Telegram 消息格式？**
A: 查看 [`standards/TELEGRAM_SETUP.md`](../standards/TELEGRAM_SETUP.md)

**Q: 我要了解整个系统架构？**
A: 从 [`standards/SYSTEM_OVERVIEW.md`](../standards/SYSTEM_OVERVIEW.md) 开始

**Q: docs/archive/ 里的文档还有用吗？**
A: 仅供历史参考，反映系统演进过程，不影响当前规范

---

**最后更新**: 2025-10-31
