# CryptoSignal v6.2 规范文档

> **系统规范统一存放目录**
> ⚠️ **强制要求**：所有规范性文档必须在此目录维护，修改系统时必须同步更新规范文档！

---

## 📋 文档索引

### **核心规范**（必读）⭐

1. **[DOCUMENTATION_RULES.md](./DOCUMENTATION_RULES.md)** - 🆕 规范文档管理制度
   - ⚠️ **强制执行** - 每次修改系统必须同步更新规范文档
   - 文档组织结构规则
   - 文档更新流程和检查清单
   - Commit Message 规范

2. **[SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)** - 系统总览
   - 新对话框必读文档
   - 系统架构、核心概念、主要功能
   - A/B/C/D 分层架构详解
   - 四门验证系统说明

3. **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速参考
   - 1分钟速查手册
   - 常见操作场景
   - 修改规范速查

4. **[MODIFICATION_RULES.md](./MODIFICATION_RULES.md)** - 修改规则
   - 代码修改规范
   - 场景化修改指南
   - 禁止修改的文件列表

---

### **架构与配置规范**

5. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - 架构说明
   - 技术架构详解
   - 模块依赖关系
   - 数据流设计

6. **[CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md)** - 配置指南
   - config/params.json 详解
   - 权重配置规范
   - 参数调优指南

---

### **开发与部署规范**

7. **[DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)** - 开发工作流
   - 7步修改流程
   - Git 提交规范
   - 测试验证要求

8. **[DEPLOYMENT_STANDARD.md](./DEPLOYMENT_STANDARD.md)** - 部署规范
   - 标准部署流程定义
   - 部署一致性要求
   - 版本追溯和回滚规范

9. **[DEPLOYMENT.md](./DEPLOYMENT.md)** - 部署操作指南
   - 标准部署流程（3步）
   - 凭证配置规范
   - Screen 启动说明
   - 分支管理规范

---

### **快速参考和运维**

10. **[QUICK_DEPLOY.md](./QUICK_DEPLOY.md)** - 快速部署参考卡
    - 一页纸部署参考
    - 复制粘贴即用的命令
    - 首次部署和更新部署

11. **[SERVER_OPERATIONS.md](./SERVER_OPERATIONS.md)** - 服务器运维命令清单
    - 一键部署命令（更新/首次）
    - 日常运维命令
    - 监控和故障排查
    - v6.2 更新内容
    - 常见问题解答

12. **[TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md)** - Telegram 设置
    - Bot 配置方法
    - 消息模板规范
    - 故障排查指南

---

### **版本与历史**

13. **[VERSION_HISTORY.md](./VERSION_HISTORY.md)** - 版本历史记录
    - v6.1 更新内容（I因子架构修正、降低阈值）
    - v6.2 更新内容（多空对称选币、类型错误修复）
    - 版本间差异对比

14. **[STANDARDIZATION_REPORT.md](./STANDARDIZATION_REPORT.md)** - 标准化报告
    - newstandards 整合历史
    - 规范演进记录

---

## 📂 目录结构

```
standards/
├── README.md                      # 本文件（文档索引）
│
├── DOCUMENTATION_RULES.md         # 🆕 规范文档管理制度（强制执行）
│
├── SYSTEM_OVERVIEW.md             # 系统总览（必读）
├── QUICK_REFERENCE.md             # 快速参考（必读）
├── MODIFICATION_RULES.md          # 修改规则（必读）
│
├── ARCHITECTURE.md                # 架构说明
├── CONFIGURATION_GUIDE.md         # 配置指南
│
├── DEVELOPMENT_WORKFLOW.md        # 开发工作流
├── DEPLOYMENT_STANDARD.md         # 部署规范
├── DEPLOYMENT.md                  # 部署操作指南
│
├── QUICK_DEPLOY.md                # 快速部署参考卡
├── SERVER_OPERATIONS.md           # 服务器运维命令清单
├── TELEGRAM_SETUP.md              # Telegram 设置
│
├── VERSION_HISTORY.md             # 版本历史记录
└── STANDARDIZATION_REPORT.md      # 标准化报告
```

---

## 🔄 文档维护原则

### ⚠️ **强制要求：代码和文档必须同步更新！**

详细规则请阅读 **[DOCUMENTATION_RULES.md](./DOCUMENTATION_RULES.md)**

### **单一信息源原则**
- ✅ 所有规范性内容只在 `standards/` 目录维护
- ✅ 其他位置的文档应引用此目录，而不是重复内容
- ❌ 严禁在 `docs/` 或根目录创建重复的规范文档

### **修改流程（强制执行）**
1. **修改系统** - 功能/配置/架构变更
2. **同步更新规范文档** - 更新 standards/ 下的相关文档
3. **更新版本信息** - 在文档中标注更新日期
4. **提交到 Git** - Commit message 中明确列出更新的文档

### **文档分类**
- **规范文档** → `standards/`（本目录，所有规范性文档）
- **技术文档** → `docs/`（技术设计、优化说明）
- **历史文档** → `docs/archive/`（已完成的计划、旧版本文档）
- **入口文档** → `/`（仅 README.md）

---

## 📖 快速导航

### 我想要...

**📚 了解文档管理规则**
→ 读 [DOCUMENTATION_RULES.md](./DOCUMENTATION_RULES.md) ⚠️ 强制执行

**🔍 了解系统**
→ 读 [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)

**🚀 快速部署到服务器**
→ 读 [QUICK_DEPLOY.md](./QUICK_DEPLOY.md) 或 [SERVER_OPERATIONS.md](./SERVER_OPERATIONS.md)

**📋 完整部署规范**
→ 读 [DEPLOYMENT_STANDARD.md](./DEPLOYMENT_STANDARD.md) + [DEPLOYMENT.md](./DEPLOYMENT.md)

**⚙️ 修改权重配置**
→ 读 [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) + [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 场景1

**📱 修改 Telegram 消息格式**
→ 读 [TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md) + [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) 场景5

**🐛 修复 Bug**
→ 读 [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) + [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)

**➕ 添加新因子**
→ 读 [ARCHITECTURE.md](./ARCHITECTURE.md) + [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) 场景4

**📜 查看版本历史**
→ 读 [VERSION_HISTORY.md](./VERSION_HISTORY.md)

---

## 🎯 当前版本

- **系统版本**: v6.2
- **文档版本**: 2025-11-02
- **主要特性**:
  - A/B/C/D 分层架构 + 四门验证系统
  - 多空对称选币机制（波动率优先）
  - 全面类型安全防护
  - 标准化部署流程（deploy.sh 一键部署）

---

**最后更新**: 2025-11-02
**维护者**: CryptoSignal Team
