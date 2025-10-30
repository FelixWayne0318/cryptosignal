# CryptoSignal v6.0 文档中心

> **欢迎使用CryptoSignal！本文档帮助您快速了解和使用系统**

---

## 📚 文档导航

### 🚀 新手必读

**1. [系统总览 (SYSTEM_OVERVIEW.md)](./SYSTEM_OVERVIEW.md)**
- ⭐ **新对话框必读**
- 项目概述和核心功能
- 主文件入口和运行方式
- 目录结构和关键文件
- 10+1维因子系统介绍
- 常见问题解答

**推荐阅读顺序**: 第1个阅读

---

### 🔧 使用指南

**2. [修改规范 (MODIFICATION_RULES.md)](./MODIFICATION_RULES.md)**
- 不同修改场景对应的文件
- 调整因子权重
- 调整Prime阈值
- 修改Telegram配置
- 修改扫描参数
- 修改因子计算逻辑
- **禁止修改的文件列表**

**适合**: 需要调整参数或修改代码的用户

**推荐阅读顺序**: 第2个阅读

---

**3. [配置参数详解 (CONFIGURATION_GUIDE.md)](./CONFIGURATION_GUIDE.md)**
- `config/params.json` 完整配置指南
- 所有参数的含义和调整建议
- 常见配置场景（趋势市场、震荡市场、高质量信号）
- 配置验证方法

**适合**: 需要深入了解参数配置的用户

**推荐阅读顺序**: 第3个阅读（按需）

---

### 🏗️ 技术文档

**4. [系统架构 (ARCHITECTURE.md)](./ARCHITECTURE.md)**
- 系统架构图
- 数据流详解
- 核心模块详解
- 依赖关系图
- 性能优化方案
- 扩展性指南

**适合**: 开发者或需要深入理解系统的用户

**推荐阅读顺序**: 第4个阅读（技术深入）

---

## 🎯 快速开始

### 对于新用户

1. **读取系统总览** → [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
2. **读取主文件** → `scripts/realtime_signal_scanner.py`
3. **配置Telegram** → `config/telegram.json`
4. **运行测试**:
   ```bash
   python3 scripts/realtime_signal_scanner.py --max-symbols 10 --once
   ```

### 对于修改参数的用户

1. **查看修改规范** → [MODIFICATION_RULES.md](./MODIFICATION_RULES.md)
2. **查找对应场景** → 找到需要修改的文件
3. **参考配置指南** → [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md)
4. **修改并测试**

### 对于开发者

1. **读取系统总览** → [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
2. **理解架构** → [ARCHITECTURE.md](./ARCHITECTURE.md)
3. **查看修改规范** → [MODIFICATION_RULES.md](./MODIFICATION_RULES.md)
4. **查看依赖关系图** → 了解模块间关系

---

## 📖 文档概览

| 文档 | 页数估计 | 适合人群 | 必读性 |
|------|---------|---------|--------|
| [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) | ~15页 | 所有用户 | ⭐⭐⭐⭐⭐ 必读 |
| [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) | ~20页 | 调参用户、开发者 | ⭐⭐⭐⭐ 强烈推荐 |
| [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) | ~25页 | 调参用户 | ⭐⭐⭐ 推荐 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | ~18页 | 开发者 | ⭐⭐⭐ 推荐 |

---

## 🔍 常见问题速查

### Q: 如何调整信号数量？
**A**: 阅读 [MODIFICATION_RULES.md § 2. 调整Prime阈值](./MODIFICATION_RULES.md#2-调整prime阈值)

### Q: 如何修改因子权重？
**A**: 阅读 [MODIFICATION_RULES.md § 1. 调整因子权重](./MODIFICATION_RULES.md#1-调整因子权重)

### Q: 如何配置Telegram？
**A**: 阅读 [MODIFICATION_RULES.md § 3. 修改Telegram配置](./MODIFICATION_RULES.md#3-修改telegram配置)

### Q: config/params.json中某个参数是什么意思？
**A**: 阅读 [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md)，查找对应参数

### Q: 系统是如何工作的？
**A**: 阅读 [ARCHITECTURE.md § 数据流详解](./ARCHITECTURE.md#-数据流详解)

### Q: 如何添加新因子？
**A**: 阅读 [MODIFICATION_RULES.md § 8. 添加新因子](./MODIFICATION_RULES.md#8-添加新因子)

### Q: 主文件是哪个？
**A**: `scripts/realtime_signal_scanner.py` - 详见 [SYSTEM_OVERVIEW.md § 主文件入口](./SYSTEM_OVERVIEW.md#-主文件入口)

### Q: 有哪些文件不能修改？
**A**: 阅读 [MODIFICATION_RULES.md § 禁止修改的文件](./MODIFICATION_RULES.md#-禁止修改的文件)

---

## 🗂️ 文件结构

```
docs/
├── README.md                    # 本文档（文档索引）
├── SYSTEM_OVERVIEW.md           # ⭐ 系统总览（新对话框必读）
├── MODIFICATION_RULES.md        # 修改规范（什么场景改什么文件）
├── CONFIGURATION_GUIDE.md       # 配置参数详解（params.json说明）
└── ARCHITECTURE.md              # 技术架构（依赖关系、数据流）
```

---

## 💡 使用建议

### 新对话框开始时

**推荐读取顺序**:
1. `docs/SYSTEM_OVERVIEW.md` - 了解整体系统
2. `scripts/realtime_signal_scanner.py` - 主文件代码
3. `config/params.json` - 当前配置
4. （按需）其他专题文档

**优点**:
- 快速理解系统架构（5-10分钟）
- 了解关键文件和配置
- 避免重复性问题

### 修改代码/参数时

1. 先查 `MODIFICATION_RULES.md` 确定修改哪个文件
2. 再查 `CONFIGURATION_GUIDE.md` 了解参数含义
3. 修改后按文档中的验证流程测试

### 遇到问题时

1. 先查本文档的"常见问题速查"
2. 搜索对应文档的关键词
3. 查看代码注释
4. 查看Git提交历史

---

## 🔗 外部资源

- **项目仓库**: cryptosignal/
- **主文件**: `scripts/realtime_signal_scanner.py`
- **配置文件**: `config/params.json`
- **Telegram配置**: `config/telegram.json`

---

## 📝 文档维护

### 文档更新原则

1. **代码变更时同步更新文档**
2. **新增功能必须更新相关文档**
3. **参数变更必须更新CONFIGURATION_GUIDE.md**
4. **架构变更必须更新ARCHITECTURE.md**

### 文档版本

当前文档版本对应: **CryptoSignal v6.0**

---

## ✅ 检查清单

使用本文档系统前，请确认：

- [ ] 已阅读 `SYSTEM_OVERVIEW.md`
- [ ] 已了解主文件位置 `scripts/realtime_signal_scanner.py`
- [ ] 已了解配置文件位置 `config/params.json`
- [ ] 已了解如何查找修改规范
- [ ] 已知道遇到问题时查阅哪个文档

---

## 🎓 学习路径

### 初级用户（使用系统）
1. SYSTEM_OVERVIEW.md
2. 运行测试
3. MODIFICATION_RULES.md § 调整Prime阈值
4. MODIFICATION_RULES.md § 修改Telegram配置

### 中级用户（调整参数）
1. SYSTEM_OVERVIEW.md
2. MODIFICATION_RULES.md
3. CONFIGURATION_GUIDE.md
4. 实践：调整权重并观察效果

### 高级用户（修改代码）
1. SYSTEM_OVERVIEW.md
2. ARCHITECTURE.md
3. MODIFICATION_RULES.md
4. 阅读核心源码
5. 实践：添加新功能

---

**文档最后更新**: 2025-10-30

**欢迎使用CryptoSignal v6.0！**
