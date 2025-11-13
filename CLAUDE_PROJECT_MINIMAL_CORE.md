# Claude Project 极简核心导入方案（推荐）

**创建时间**: 2025-11-13
**原因**: standards/和docs/即使精简后还是太大
**策略**: 只导入10-12个最核心文件
**目标**: <1M，绝对不超限

---

## 🎯 极简核心文件清单（共约10个文件）

### 📄 系统说明（1个）
```
✅ CLAUDE_PROJECT_CONTEXT.md    - 系统完整状态说明（必读）
```

### ⚙️ 配置文件（1个）
```
✅ config/signal_thresholds.json    - 所有阈值配置
```

### 📖 核心规范（2个）
```
✅ standards/00_INDEX.md                   - 规范索引
✅ standards/SYSTEM_ENHANCEMENT_STANDARD.md - 开发规范
```

### 🔧 运行脚本（1个）
```
✅ scripts/realtime_signal_scanner.py    - 实时扫描器
```

### 💻 核心算法（5个）
```
✅ ats_core/pipeline/analyze_symbol_v72.py      - v7.2分析引擎
✅ ats_core/features/fund_leading.py            - F因子v2
✅ ats_core/scoring/factor_groups.py            - 因子分组
✅ ats_core/gates/integrated_gates.py           - 四道闸门
✅ ats_core/calibration/empirical_calibration.py - 统计校准
```

### 📋 其他（2个）
```
✅ README.md    - 项目说明
✅ setup.sh     - 启动脚本
```

---

## 🚀 快速导入步骤

### 步骤1：应用极简配置（10秒）

```bash
cd /home/user/cryptosignal

# 应用极简核心配置
cp .claudeignore.minimal .claudeignore

# 提交
git add .claudeignore
git commit -m "feat: 应用Claude Project极简核心导入配置（<1M）"
git push
```

### 步骤2：Claude.ai导入（3分钟）

1. **打开** https://claude.ai
2. **创建** Project：
   - 名称：`CryptoSignal v7.2.36 Core`
   - 描述：`核心算法和配置`

3. **导入** GitHub仓库：
   - 点击 "Add content"
   - 选择 "Add from GitHub"
   - 仓库：`FelixWayne0318/cryptosignal`
   - 分支：`claude/reorganize-repo-structure-011CV4wShXjHEW61P1kc18W9`

4. **选择文件**：
   - ⚠️ **不要手动选择目录**
   - 让GitHub根据.claudeignore自动过滤
   - 或者只勾选以下目录：
     - ☑ config/ (只会导入signal_thresholds.json)
     - ☑ standards/ (只会导入2个核心文件)
     - ☑ ats_core/pipeline/ (只会导入analyze_symbol_v72.py)
     - ☑ ats_core/features/ (只会导入fund_leading.py)
     - ☑ ats_core/scoring/ (只会导入factor_groups.py)
     - ☑ ats_core/gates/ (只会导入integrated_gates.py)
     - ☑ ats_core/calibration/ (只会导入empirical_calibration.py)
     - ☑ scripts/ (只会导入realtime_signal_scanner.py)
     - ☑ CLAUDE_PROJECT_CONTEXT.md
     - ☑ README.md
     - ☑ setup.sh

5. **确认导入**：
   - 容量进度条应该在 **10-20%** 左右
   - 远低于100%限制

### 步骤3：验证导入（30秒）

在Project中发送第一条消息：

```
Hi Claude！

我已经从GitHub导入了CryptoSignal v7.2.36的核心文件。

请确认你能看到这些文件：
1. CLAUDE_PROJECT_CONTEXT.md
2. config/signal_thresholds.json
3. standards/SYSTEM_ENHANCEMENT_STANDARD.md
4. ats_core/pipeline/analyze_symbol_v72.py
5. ats_core/features/fund_leading.py

请先阅读 CLAUDE_PROJECT_CONTEXT.md 了解系统状态。
```

---

## ✅ 这10个文件足够做什么？

### 1. 理解系统架构 ✅
- **CLAUDE_PROJECT_CONTEXT.md** 包含完整的系统架构说明
- **analyze_symbol_v72.py** 展示完整的数据流程
- **setup.sh** 说明启动流程

### 2. 理解核心算法 ✅
- **fund_leading.py** - F因子v2（资金流领先）
- **factor_groups.py** - 因子分组（TC/VOM/B）
- **integrated_gates.py** - 四道闸门过滤
- **empirical_calibration.py** - 统计校准

### 3. 修改配置 ✅
- **signal_thresholds.json** - 所有阈值配置
- **SYSTEM_ENHANCEMENT_STANDARD.md** - 修改规范

### 4. 代码审查 ✅
- 5个核心算法文件都在
- 可以审查最重要的逻辑

### 5. 功能开发 ✅
- 理解现有实现
- 规划新功能
- 遵循开发规范

---

## ❌ 这10个文件不能做什么？

### 暂时无法直接查看的

**其他因子计算**：
- ❌ trend.py, momentum.py, cvd.py 等
- 💡 需要时在对话中粘贴

**完整规范文档**：
- ❌ standards/specifications/（8个技术规范）
- ❌ standards/deployment/（5个部署文档）
- 💡 需要时单独Upload到Project

**测试和诊断**：
- ❌ tests/, diagnose/
- 💡 本地运行即可

**输出格式化**：
- ❌ ats_core/outputs/telegram_fmt.py
- 💡 需要时在对话中粘贴

---

## 💡 需要查看其他文件时怎么办？

### 方案1：临时粘贴到对话中（推荐）

```
"我需要查看 ats_core/features/trend.py 的实现，
这是文件内容：
[粘贴代码]

请结合Project中的factor_groups.py分析..."
```

### 方案2：Upload单个文件到Project

1. 在Project中点击 "Add content"
2. 选择 "Upload a file"
3. 上传需要的单个文件
4. 查看完后可以删除

### 方案3：暂时调整.claudeignore

```bash
# 编辑.claudeignore，注释掉某行
vim .claudeignore
# 例如注释掉：# ats_core/features/trend.py

# 提交并同步
git add .claudeignore
git commit -m "temp: 临时添加trend.py"
git push

# 在Project中点击 "Sync"
# 查看完后改回来
```

---

## 🔄 完整规范文档怎么办？

如果需要经常查阅standards/中的详细规范：

### 方案A：创建第二个Project（推荐）

**Project 1: Core (10个文件)**
- 核心代码和配置
- 日常开发使用

**Project 2: Docs (20-30个文件)**
- standards/所有规范
- docs/所有文档
- 查阅参考使用

### 方案B：本地保存关键规范

```bash
# 将关键规范复制到一个markdown文件
cat standards/00_INDEX.md \
    standards/SYSTEM_ENHANCEMENT_STANDARD.md \
    standards/CORE_STANDARDS.md \
    > KEY_STANDARDS.md

# 只导入这一个文件
```

### 方案C：使用本地Claude Code

- 继续使用当前的Claude Code环境
- 可以直接读取所有本地文件
- Project只作为快速参考

---

## 📊 配置对比

| 配置版本 | 文件数 | 大小 | 容量占用 | 推荐 |
|---------|-------|------|---------|------|
| `.claudeignore.full` | ~300 | 17M | 956% ❌ | ❌ |
| `.claudeignore.github` | ~100 | ~4M | ~400%? ❌ | ❌ |
| `.claudeignore.minimal` | **~10** | **<1M** | **10-20%** ✅ | **✅** |

---

## ✅ 导入后验证清单

### Project中应该能看到：
- [x] CLAUDE_PROJECT_CONTEXT.md
- [x] config/signal_thresholds.json
- [x] standards/00_INDEX.md
- [x] standards/SYSTEM_ENHANCEMENT_STANDARD.md
- [x] ats_core/pipeline/analyze_symbol_v72.py
- [x] ats_core/features/fund_leading.py
- [x] ats_core/scoring/factor_groups.py
- [x] ats_core/gates/integrated_gates.py
- [x] ats_core/calibration/empirical_calibration.py

### Project中应该看不到：
- [ ] docs/（任何文件）
- [ ] tests/（任何文件）
- [ ] standards/specifications/
- [ ] standards/deployment/
- [ ] ats_core/features/trend.py
- [ ] ats_core/outputs/

### 容量占用：
- [ ] 进度条 < 50%（通常在10-20%）

---

## 💬 第一次对话模板

导入成功后，在Project中发送：

```
Hi Claude！

我已经导入了CryptoSignal v7.2.36的核心文件（10个最重要的）。

请先阅读 CLAUDE_PROJECT_CONTEXT.md 了解系统整体状态。

然后帮我：
1. 确认你理解了v7.2.36的核心架构
2. 解释 analyze_symbol_v72.py 中的完整数据流
3. 说明 F因子v2、因子分组、四道闸门 是如何协同工作的

需要查看其他文件时，我会粘贴内容到对话中。
```

---

## 🔧 后续维护

### 代码更新后同步

```bash
# 本地修改核心文件后
git add .
git commit -m "feat: 优化F因子计算"
git push

# 在Project中点击 "Sync"
# 只会同步这10个核心文件
```

### 需要添加新文件

```bash
# 编辑.claudeignore，移除对应的排除行
vim .claudeignore

# 例如要添加trend.py：
# 删除或注释这行：ats_core/features/trend.py

# 提交
git add .claudeignore
git commit -m "feat: 添加trend.py到Project"
git push

# Project中同步
```

---

## 📞 常见问题

**Q: 只有10个文件够用吗？**

A: 对于日常开发完全够用：
- ✅ 系统架构（CLAUDE_PROJECT_CONTEXT.md）
- ✅ 核心算法（5个关键.py文件）
- ✅ 配置规范（signal_thresholds.json + 开发规范）
- 其他文件需要时粘贴到对话中即可

**Q: 如果需要查看其他代码怎么办？**

A: 三种方式：
1. 复制粘贴到对话中（推荐）
2. Upload单个文件到Project
3. 临时调整.claudeignore并Sync

**Q: 完整规范文档看不到了？**

A:
- CLAUDE_PROJECT_CONTEXT.md 已包含核心信息
- 需要详细规范时创建第二个Docs Project
- 或使用本地Claude Code环境

**Q: 这个配置会漏掉重要文件吗？**

A: 不会。10个文件是精心挑选的最核心文件：
- 1个系统说明
- 1个配置文件
- 2个核心规范
- 5个核心算法
- 其他都是支撑文件，需要时再看

**Q: 容量会占多少？**

A: 预计10-20%，远低于100%限制

---

## 🎉 总结

### 极简核心方案的优势

1. **绝对不超限** - <1M，容量占用10-20%
2. **包含核心** - 10个最关键文件全都有
3. **易于维护** - 文件少，同步快
4. **灵活扩展** - 需要时随时添加

### 适用场景

✅ **日常开发** - 查看核心逻辑，修改配置
✅ **代码审查** - 审查最重要的算法
✅ **功能规划** - 理解架构，规划新功能
✅ **快速参考** - 随时查阅关键文件

### 立即开始

```bash
# 1. 应用配置
cp .claudeignore.minimal .claudeignore
git add .claudeignore
git commit -m "feat: 应用Claude Project极简核心配置"
git push

# 2. Claude.ai导入
# 按照上面步骤2操作

# 3. 验证导入
# 发送验证消息
```

**预计耗时**: 5分钟
**成功率**: 99.9%（<1M几乎不可能超限）

---

**创建时间**: 2025-11-13
**维护者**: CryptoSignal开发团队
**系统版本**: v7.2.36
**推荐程度**: ⭐⭐⭐⭐⭐（强烈推荐）

**立即试试吧！** 🚀
