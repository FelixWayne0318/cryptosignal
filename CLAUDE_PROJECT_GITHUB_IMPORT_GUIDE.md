# Claude Project GitHub导入完整指南

**创建时间**: 2025-11-13
**目标**: 将956%压缩到100%以内，成功导入CryptoSignal v7.2.36
**策略**: 精选核心代码，排除数据/测试/日志

---

## 🎯 核心认知

### 三种导入方式的本质

| 方式 | 容量来源 | 适用场景 | CryptoSignal使用 |
|------|---------|---------|-----------------|
| **GitHub** | 共用配额 | 代码仓库（主力） | ✅ 主力方案 |
| **Upload** | 共用配额 | 单个文档/脚本 | 偶尔用 |
| **Google Drive** | 共用配额 | 外部资料 | 基本不用 |

**关键点**：
- ✅ 所有方式共用**同一个容量配额**
- ✅ GitHub导入是**索引式阅读**，不是Git客户端
- ✅ 容量用完就是100%，超了就导入失败

---

## 📊 当前问题分析

### 您遇到的956%超限原因

```
CryptoSignal仓库完整大小：17M（304个文件）

占容量最大的部分：
1. ats_core/        1.7M (103个文件) → 部分需要
2. tests/           225K (21个文件)  → 可排除
3. diagnose/        90K  (9个文件)   → 可排除
4. data/            ???  (运行时数据) → 必须排除
5. reports/         ???  (扫描报告)   → 必须排除
6. 大文件：
   - telegram_fmt.py         89K → 可排除
   - analyze_symbol.py       88K → 可排除（旧版）
   - batch_scan_optimized.py 54K → 可排除
```

---

## 🚀 分步导入方案

### 第1步：应用GitHub导入配置

```bash
cd /home/user/cryptosignal

# 使用GitHub导入专用配置
cp .claudeignore.github .claudeignore

# 验证配置
cat .claudeignore
```

**这个配置会排除**：
- ❌ data/, reports/, logs/ (运行时数据)
- ❌ tests/, diagnose/ (测试诊断)
- ❌ ats_core中的非核心模块
- ❌ 大文件（telegram_fmt.py等）
- ❌ 图片、PDF等资源文件

**保留的核心内容**：
- ✅ ats_core/核心模块（features, pipeline, gates, scoring等）
- ✅ config/ (配置文件)
- ✅ scripts/ (运行脚本)
- ✅ standards/ (核心规范)
- ✅ docs/ (核心文档)
- ✅ CLAUDE_PROJECT_CONTEXT.md

**预计大小**: ~3-4M（应该在100%以内）

---

### 第2步：提交.claudeignore到GitHub

```bash
# 提交配置文件
git add .claudeignore
git commit -m "feat: 添加Claude Project GitHub导入优化配置

针对Project容量限制优化：
- 排除运行时数据（data/, reports/, logs/）
- 排除测试诊断（tests/, diagnose/）
- 排除ats_core非核心模块
- 排除大文件和资源文件

目标：将956%压缩到100%以内"

git push -u origin claude/reorganize-repo-structure-011CV4wShXjHEW61P1kc18W9
```

---

### 第3步：在Claude.ai创建Project并导入

**3.1 打开Claude.ai**
- 登录 https://claude.ai
- 点击左侧 "Projects"
- 点击 "Create Project"

**3.2 设置Project**
- 名称：`CryptoSignal v7.2.36`
- 描述：`加密货币交易信号系统 - 6因子模型`

**3.3 添加GitHub仓库**
1. 点击 "Add content"
2. 选择 "Add from GitHub"
3. 授权GitHub访问（如果首次使用）
4. 选择仓库：`FelixWayne0318/cryptosignal`
5. 选择分支：`claude/reorganize-repo-structure-011CV4wShXjHEW61P1kc18W9`

**3.4 选择目录（关键步骤）**

✅ **必选目录**（核心逻辑）：
```
☑ config/                      - 所有配置
☑ standards/                   - 规范文档
☑ docs/                        - 核心文档
☑ ats_core/features/           - 因子计算
☑ ats_core/pipeline/           - 数据流
☑ ats_core/gates/              - 闸门
☑ ats_core/scoring/            - 评分
☑ ats_core/calibration/        - 校准
☑ ats_core/preprocessing/      - 预处理
☑ ats_core/config/             - 配置管理
☑ ats_core/modulators/         - 调制器
☑ ats_core/data/               - 数据管理
☑ scripts/                     - 运行脚本
☑ CLAUDE_PROJECT_CONTEXT.md    - 系统说明
☑ README.md                    - 项目说明
☑ setup.sh                     - 启动脚本
```

⚠️ **可选目录**（视容量而定）：
```
☐ ats_core/sources/            - 数据源（可选）
☐ ats_core/utils/              - 工具函数（可选）
☐ ats_core/execution/          - 执行层（可选）
☐ ats_core/outputs/            - 输出（但排除大文件）
☐ ats_core/publishing/         - 发布（可选）
```

❌ **不选目录**（必须排除）：
```
☐ data/                        - 运行时数据
☐ reports/                     - 扫描报告
☐ logs/                        - 日志
☐ archived/                    - 归档
☐ tests/                       - 测试（占容量）
☐ diagnose/                    - 诊断工具
☐ ats_core/analysis/           - 分析工具
☐ ats_core/monitoring/         - 监控
☐ ats_core/shadow/             - 影子模式
☐ ats_core/factors_v2/         - 旧版因子
☐ ats_core/tools/              - 工具类
```

**3.5 确认导入**
- 点击 "Add files"
- 等待索引完成
- **查看容量进度条**：应该在100%以内

---

### 第4步：验证导入成功

**在Project中测试**：

发送第一条消息：
```
Hi Claude！

我已经从GitHub导入了CryptoSignal v7.2.36核心代码。

请帮我确认：
1. 你能看到 CLAUDE_PROJECT_CONTEXT.md 吗？
2. 你能看到 ats_core/features/fund_leading.py 吗？
3. 你能看到 config/signal_thresholds.json 吗？

请先阅读 CLAUDE_PROJECT_CONTEXT.md 了解系统整体状态。
```

**Claude应该能回答**：
- ✅ 可以看到这些文件
- ✅ 能读取CLAUDE_PROJECT_CONTEXT.md内容
- ✅ 能解释系统架构

---

## 🔧 容量优化策略

### 如果第一次导入还是超限

**逐步排除非核心模块**：

```bash
# 编辑 .claudeignore，增加排除项
vim .claudeignore

# 增加以下行：
ats_core/data/
ats_core/utils/
ats_core/sources/
ats_core/execution/
ats_core/outputs/
ats_core/publishing/

# 提交并推送
git add .claudeignore
git commit -m "feat: 进一步优化Project导入容量"
git push
```

然后在Claude.ai Project中：
- 点击仓库右上角的 "⋮"
- 选择 "Sync"
- 重新同步（会应用新的.claudeignore）

### 最小核心集合（如果还超限）

**只保留最核心的逻辑**：

✅ **绝对核心**（不能再少）：
```
config/signal_thresholds.json
standards/00_INDEX.md
standards/SYSTEM_ENHANCEMENT_STANDARD.md
ats_core/pipeline/analyze_symbol_v72.py
ats_core/features/fund_leading.py
ats_core/scoring/factor_groups.py
ats_core/gates/integrated_gates.py
ats_core/calibration/empirical_calibration.py
CLAUDE_PROJECT_CONTEXT.md
```

**这样应该能控制在1M左右，绝对不会超限。**

---

## 📖 导入后的使用方式

### 1. 理解系统架构

**Project中直接查看**：
```
"请详细解释 ats_core/pipeline/analyze_symbol_v72.py 的工作流程，
结合 CLAUDE_PROJECT_CONTEXT.md 中的架构说明。"
```

Claude会：
- ✅ 读取analyze_symbol_v72.py（已在Project中）
- ✅ 结合CLAUDE_PROJECT_CONTEXT.md（已在Project中）
- ✅ 给出完整分析

### 2. 代码审查

```
"请审查 ats_core/features/fund_leading.py 的F因子v2实现，
检查是否符合 standards/CORE_STANDARDS.md 的要求。"
```

### 3. 功能开发

```
"我想在四道闸门中增加第五道闸门，用于检查流动性。
请基于 ats_core/gates/integrated_gates.py 的现有实现，
给出具体的代码修改方案。"
```

### 4. 配置调整

```
"查看 config/signal_thresholds.json 中的v72闸门阈值，
结合 standards/MODIFICATION_RULES.md 的规范，
帮我调整Gate2的F_min从-10到-5。"
```

---

## 🔄 后续维护

### 代码更新后同步

**本地修改代码后**：
```bash
# 提交到GitHub
git add .
git commit -m "feat: 添加新功能"
git push
```

**在Claude.ai Project中**：
1. 进入Project
2. 点击GitHub仓库旁的 "⋮"
3. 选择 "Sync"
4. Project会自动拉取最新代码

### 添加新文档

**如果创建了新文档需要加入Project**：
```bash
# 确保不在.claudeignore中
vim .claudeignore
# 确认新文档路径没有被排除

# 提交
git add docs/new_document.md
git commit -m "docs: 添加新文档"
git push

# Project中同步
# Sync即可
```

---

## 💡 最佳实践

### ✅ 应该放在Project中的

**代码逻辑**：
- ✅ 因子计算（features/）
- ✅ 数据流程（pipeline/）
- ✅ 评分逻辑（scoring/）
- ✅ 过滤机制（gates/）

**配置规范**：
- ✅ signal_thresholds.json
- ✅ standards/ 规范文档
- ✅ SYSTEM_ENHANCEMENT_STANDARD.md

**架构文档**：
- ✅ CLAUDE_PROJECT_CONTEXT.md
- ✅ CORE_STANDARDS.md
- ✅ 核心技术文档

### ❌ 不应该放在Project中的

**运行时数据**：
- ❌ data/ (K线、市场数据)
- ❌ reports/ (扫描报告)
- ❌ logs/ (运行日志)

**测试文件**（除非特别需要）：
- ❌ tests/ (占容量且不常查)
- ❌ diagnose/ (诊断工具)

**资源文件**：
- ❌ 图片、PDF、压缩包
- ❌ 二进制文件

### 📋 检查清单

**导入前**：
- [ ] .claudeignore配置正确
- [ ] 已提交到GitHub
- [ ] 分支选择正确

**导入时**：
- [ ] 只勾选核心目录
- [ ] 容量进度条在100%以内
- [ ] 没有选择data/reports/等数据目录

**导入后**：
- [ ] 能查看CLAUDE_PROJECT_CONTEXT.md
- [ ] 能查看核心代码文件
- [ ] Claude能正确解释系统架构

---

## 🆘 常见问题

**Q1: 导入后还是显示超限怎么办？**

A: 逐步排除更多目录：
1. 先排除tests/, diagnose/
2. 再排除ats_core/中的utils/, tools/, analysis/
3. 再排除ats_core/data/, sources/
4. 最后只保留绝对核心的6-7个.py文件

**Q2: 排除的文件需要时怎么办？**

A:
- 如果是单个文件：复制粘贴到对话中
- 如果是整个模块：临时调整.claudeignore，Sync后再改回来

**Q3: .claudeignore修改后Project会自动应用吗？**

A: 需要手动Sync：
1. 提交.claudeignore到GitHub
2. 在Project中点击 "Sync"

**Q4: GitHub导入和Upload有什么区别？**

A:
- GitHub：可以Sync更新，适合代码仓库
- Upload：一次性快照，适合单个文档
- 建议：代码用GitHub，零散文档用Upload

**Q5: 能不能创建多个Project分别导入？**

A: 可以！
- Project A：核心代码（ats_core核心模块）
- Project B：测试诊断（tests/, diagnose/）
- Project C：文档规范（standards/, docs/）

但通常一个精心配置的Project就够用。

---

## 📞 技术支持

**如果遇到问题**：

1. 检查.claudeignore配置
2. 确认GitHub分支正确
3. 查看容量进度条具体数值
4. 逐步排除目录定位问题

**需要帮助**：
- 查看本文档的详细步骤
- 参考CLAUDE_PROJECT_CONTEXT.md
- 咨询Claude Code（当前环境）

---

**创建时间**: 2025-11-13
**维护者**: CryptoSignal开发团队
**系统版本**: v7.2.36
**适用范围**: Claude.ai Project GitHub导入

**祝导入顺利！** 🚀
