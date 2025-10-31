# CryptoSignal v6.0 规范文档

> **系统规范统一存放目录**
> 所有规范性文档均在此目录维护，修改规范时请只更新此目录下的文件。

---

## 📋 文档索引

### **核心规范**（必读）

1. **[SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)** - 系统总览
   - 新对话框必读文档
   - 系统架构、核心概念、主要功能
   - A/B/C/D 分层架构详解
   - 四门验证系统说明

2. **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速参考
   - 1分钟速查手册
   - 常见操作场景
   - 修改规范速查

3. **[MODIFICATION_RULES.md](./MODIFICATION_RULES.md)** - 修改规则
   - 代码修改规范
   - 场景化修改指南
   - 禁止修改的文件列表

---

### **详细规范**

4. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - 架构说明
   - 技术架构详解
   - 模块依赖关系
   - 数据流设计

5. **[CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md)** - 配置指南
   - config/params.json 详解
   - 权重配置规范
   - 参数调优指南

6. **[DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)** - 开发工作流
   - 7步修改流程
   - Git 提交规范
   - 测试验证要求

7. **[TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md)** - Telegram 设置
   - Bot 配置方法
   - 消息模板规范
   - 故障排查指南

8. **[STANDARDIZATION_REPORT.md](./STANDARDIZATION_REPORT.md)** - 标准化报告
   - newstandards 整合历史
   - 规范演进记录

---

## 📂 目录结构

```
standards/
├── README.md                      # 本文件（目录索引）
│
├── SYSTEM_OVERVIEW.md             # 系统总览（必读）
├── QUICK_REFERENCE.md             # 快速参考（必读）
├── MODIFICATION_RULES.md          # 修改规则（必读）
│
├── ARCHITECTURE.md                # 架构说明
├── CONFIGURATION_GUIDE.md         # 配置指南
├── DEVELOPMENT_WORKFLOW.md        # 开发工作流
├── TELEGRAM_SETUP.md              # Telegram 设置
│
└── STANDARDIZATION_REPORT.md      # 标准化报告
```

---

## 🔄 文档维护原则

### **单一信息源原则**
- ✅ 所有规范性内容只在 `standards/` 目录维护
- ✅ 其他位置的文档应引用此目录，而不是重复内容
- ❌ 不要在 `docs/` 或其他地方创建重复的规范文档

### **修改流程**
1. **发现需要修改规范**：先确定修改哪个文件
2. **修改 standards/ 下的对应文件**：直接编辑
3. **更新文档版本信息**：在文档末尾标注更新日期
4. **提交到 Git**：使用清晰的提交消息

### **文档分类**
- **规范文档**：放在 `standards/`（本目录）
- **临时文档**：放在 `docs/archive/`（如报告、清单）
- **代码文档**：放在代码旁边（如 README.md）

---

## 📖 快速导航

### 我想要...

**了解系统**
→ 读 [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)

**修改权重配置**
→ 读 [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) + [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 场景1

**修改 Telegram 消息格式**
→ 读 [TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md) + [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) 场景5

**修复 Bug**
→ 读 [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) + [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)

**添加新因子**
→ 读 [ARCHITECTURE.md](./ARCHITECTURE.md) + [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) 场景4

---

## 🎯 当前版本

- **系统版本**: v6.0 newstandards 整合版
- **文档版本**: 2025-10-31
- **主要特性**: A/B/C/D 分层架构 + 四门验证系统

---

**最后更新**: 2025-10-31
**维护者**: CryptoSignal Team
