# Claude Project 开发者导入方案（推荐）

**创建时间**: 2025-11-13
**核心思路**: 只导入经常需要修改和分析的文件，其他留在仓库
**工作流程**: Project修改代码 → 同步GitHub → Termius运行

---

## 🎯 正确的开发思路

### 从setup.sh追踪完整调用链

```
setup.sh
  └─> scripts/realtime_signal_scanner.py (启动扫描器)
        └─> ats_core/pipeline/batch_scan_optimized.py (批量扫描)
              └─> ats_core/pipeline/analyze_symbol_v72.py (v7.2分析引擎)
                    ├─> ats_core/features/fund_leading.py (F因子v2)
                    ├─> ats_core/scoring/factor_groups.py (因子分组TC/VOM/B)
                    ├─> ats_core/gates/integrated_gates.py (四道闸门)
                    ├─> ats_core/calibration/empirical_calibration.py (统计校准)
                    └─> ats_core/outputs/telegram_fmt.py (Telegram输出)
```

---

## 📦 应该导入Project的文件（经常修改）

### 1. 核心算法逻辑（最常修改）

✅ **因子计算** - 优化策略时经常调整
```
ats_core/features/fund_leading.py           - F因子v2（资金流领先）
ats_core/features/trend.py                  - T因子（趋势）
ats_core/features/momentum.py               - M因子（动量）
ats_core/features/cvd.py                    - C因子（CVD）
ats_core/features/volume.py                 - V因子（量能）
ats_core/features/open_interest.py          - O因子（持仓）
ats_core/features/basis.py                  - B因子（基差）
```

✅ **评分和分组** - 调整权重时修改
```
ats_core/scoring/factor_groups.py           - 因子分组（TC/VOM/B）
ats_core/scoring/integrated_score.py        - 综合评分
```

✅ **过滤系统** - 调整过滤逻辑时修改
```
ats_core/gates/integrated_gates.py          - 四道闸门
```

✅ **统计校准** - 优化校准时修改
```
ats_core/calibration/empirical_calibration.py - 经验校准器
```

✅ **v7.2分析引擎** - 修改整体流程时
```
ats_core/pipeline/analyze_symbol_v72.py     - v7.2集成分析
```

### 2. 配置文件（经常调整）

✅ **阈值配置** - 最频繁修改
```
config/signal_thresholds.json               - 所有阈值配置
```

### 3. 核心规范（参考）

✅ **开发规范** - 修改代码时遵循
```
standards/SYSTEM_ENHANCEMENT_STANDARD.md    - 开发规范
standards/00_INDEX.md                       - 规范索引
```

### 4. 系统说明（理解架构）

✅ **架构文档**
```
CLAUDE_PROJECT_CONTEXT.md                   - 系统完整状态
README.md                                   - 项目说明
```

---

## 🗂️ 应该留在仓库的文件（不需要导入Project）

### 只读文件（不需要修改，需要时查看）

❌ **启动脚本** - 很少修改
```
setup.sh
auto_restart.sh
deploy_and_run.sh
```

❌ **扫描器** - 稳定后很少改
```
scripts/realtime_signal_scanner.py
scripts/init_databases.py
```

❌ **数据管理** - 底层稳定代码
```
ats_core/data/*.py
ats_core/sources/*.py
```

❌ **工具函数** - 稳定的工具类
```
ats_core/utils/*.py
ats_core/preprocessing/*.py
```

❌ **测试文件** - 本地运行
```
tests/*.py
diagnose/*.py
```

❌ **详细文档** - 需要时查阅
```
docs/*.md
standards/specifications/*.md
standards/deployment/*.md
```

❌ **输出格式化** - 稳定后很少改
```
ats_core/outputs/telegram_fmt.py (89K大文件)
```

---

## 🚀 推荐导入清单（约15-20个文件，<2M）

```
项目根目录：
├─ CLAUDE_PROJECT_CONTEXT.md              - 系统状态说明
├─ README.md                              - 项目说明
│
├─ config/
│  └─ signal_thresholds.json              - 阈值配置（最常改）
│
├─ standards/
│  ├─ 00_INDEX.md                         - 规范索引
│  └─ SYSTEM_ENHANCEMENT_STANDARD.md      - 开发规范
│
└─ ats_core/
   ├─ pipeline/
   │  └─ analyze_symbol_v72.py            - v7.2分析引擎
   │
   ├─ features/ (7个因子)
   │  ├─ fund_leading.py                  - F因子v2
   │  ├─ trend.py                         - T因子
   │  ├─ momentum.py                      - M因子
   │  ├─ cvd.py                           - C因子
   │  ├─ volume.py                        - V因子
   │  ├─ open_interest.py                 - O因子
   │  └─ basis.py                         - B因子
   │
   ├─ scoring/
   │  ├─ factor_groups.py                 - 因子分组
   │  └─ integrated_score.py              - 综合评分
   │
   ├─ gates/
   │  └─ integrated_gates.py              - 四道闸门
   │
   └─ calibration/
      └─ empirical_calibration.py         - 统计校准

总计：约18个文件
```

---

## 📝 .claudeignore 配置（开发者版）

```bash
# 版本控制
.git/
.gitignore
__pycache__/
*.pyc

# 运行时数据
data/
reports/
logs/
*.log
*.csv
*.db

# 归档和测试
archived/
tests/
diagnose/

# 启动脚本（稳定，不需要导入Project）
setup.sh
auto_restart.sh
deploy_and_run.sh
start_live.sh

# 扫描器（稳定，很少修改）
scripts/realtime_signal_scanner.py
scripts/init_databases.py
scripts/batch*.py

# ats_core中的稳定模块（不需要经常修改）
ats_core/data/
ats_core/sources/
ats_core/execution/
ats_core/publishing/
ats_core/utils/
ats_core/preprocessing/
ats_core/config/
ats_core/analysis/
ats_core/monitoring/
ats_core/tools/
ats_core/shadow/
ats_core/risk/
ats_core/rl/
ats_core/streaming/
ats_core/factors_v2/
ats_core/modulators/

# ats_core/pipeline/ 中只保留analyze_symbol_v72.py
ats_core/pipeline/analyze_symbol.py
ats_core/pipeline/batch_scan_optimized.py
ats_core/pipeline/realtime_scanner.py
ats_core/pipeline/scanner_*.py

# 大文件输出
ats_core/outputs/

# docs/ 只保留README，其他太多
docs/

# standards/ 只保留2个核心规范
standards/01_SYSTEM_OVERVIEW.md
standards/02_ARCHITECTURE.md
standards/03_VERSION_HISTORY.md
standards/CORE_STANDARDS.md
standards/DEVELOPMENT_WORKFLOW.md
standards/DOCUMENTATION_RULES.md
standards/MODIFICATION_RULES.md
standards/deployment/
standards/specifications/

# 其他配置文件
config/binance_credentials.json
config/telegram.json
config/params.json
config/factors_unified.json

# 资源文件
*.png
*.jpg
*.pdf
*.zip
```

---

## 🔄 开发工作流程

### 1. 在Claude Project中修改代码

```
场景：优化F因子v2的计算逻辑

1. 在Project中打开 ats_core/features/fund_leading.py
2. Claude帮你分析现有逻辑
3. 直接在Project中修改代码
4. Claude审查修改的合理性
```

### 2. 同步到GitHub

```bash
# 在本地（或Termius上）
cd ~/cryptosignal
git pull  # 拉取Project中的修改
git add ats_core/features/fund_leading.py
git commit -m "feat: 优化F因子v2计算逻辑"
git push
```

### 3. 在Termius运行测试

```bash
# SSH到服务器
ssh user@server

# 拉取最新代码并重启
cd ~/cryptosignal
./setup.sh

# 或者快速重启
./auto_restart.sh

# 查看日志验证修改
tail -f ~/cryptosignal_*.log
```

---

## ✅ 这个方案的优势

### 1. 精准的导入范围
- ✅ 只导入**经常修改的核心算法**（18个文件）
- ✅ 容量占用小（约2M，远低于100%）
- ✅ 每个文件都有明确的修改理由

### 2. 符合实际开发流程
- ✅ 80%的时间在修改因子计算、评分、闸门
- ✅ 配置调整最频繁（signal_thresholds.json）
- ✅ 其他稳定代码不需要在Project中

### 3. 高效的工作流
- ✅ Project：分析算法、修改代码
- ✅ GitHub：版本控制、代码同步
- ✅ Termius：运行测试、查看结果

### 4. 清晰的职责分工
- **Project** = 开发环境（修改核心算法）
- **GitHub** = 代码仓库（版本管理）
- **Termius/服务器** = 运行环境（实际交易）

---

## 🎯 实际使用场景

### 场景1：优化F因子计算

**在Project中**:
```
"我想优化F因子v2的fund_momentum计算，
现在OI/VOL/CVD的权重是多少？
能否根据市场特征自适应调整？

请查看 fund_leading.py 的实现，
给出优化方案。"
```

Claude会：
1. 读取fund_leading.py（已在Project中）
2. 分析现有权重配置
3. 结合signal_thresholds.json（已在Project中）
4. 提出优化方案并修改代码

**修改后**:
```bash
git pull
git add ats_core/features/fund_leading.py
git commit -m "feat: F因子v2自适应权重优化"
git push
./auto_restart.sh  # Termius上重启测试
```

### 场景2：调整闸门阈值

**在Project中**:
```
"当前Gate2的F_min是-10，
导致过滤率太高（95%）。

请分析 integrated_gates.py 的逻辑，
结合 signal_thresholds.json 的配置，
建议合适的F_min值。"
```

Claude会：
1. 读取integrated_gates.py（已在Project中）
2. 读取signal_thresholds.json（已在Project中）
3. 分析过滤逻辑
4. 建议调整F_min到-5或-3

**修改后**:
```bash
# 只需修改配置文件
git pull
git add config/signal_thresholds.json
git commit -m "config: 调整Gate2 F_min从-10到-5"
git push
./auto_restart.sh
```

### 场景3：调整因子分组权重

**在Project中**:
```
"当前TC组权重50%，VOM组38%，B组12%。
我想增加资金流的重要性，
调整为TC:45%, VOM:43%, B:12%。

请帮我修改 factor_groups.py，
并更新 signal_thresholds.json 中的配置。"
```

Claude会：
1. 读取factor_groups.py（已在Project中）
2. 读取signal_thresholds.json（已在Project中）
3. 修改权重配置
4. 确保权重总和=100%

### 场景4：新增因子

**在Project中**:
```
"我想新增一个L因子（流动性因子），
参考 fund_leading.py 的实现方式，
创建 ats_core/features/liquidity.py。

然后在 factor_groups.py 中集成这个新因子。"
```

Claude会：
1. 参考fund_leading.py的结构
2. 创建新的liquidity.py
3. 修改factor_groups.py集成L因子
4. 更新signal_thresholds.json添加L因子配置

---

## 📋 导入验证清单

### Project中应该有：
- [x] CLAUDE_PROJECT_CONTEXT.md
- [x] config/signal_thresholds.json
- [x] standards/SYSTEM_ENHANCEMENT_STANDARD.md
- [x] ats_core/pipeline/analyze_symbol_v72.py
- [x] ats_core/features/ (7个因子文件)
- [x] ats_core/scoring/ (2个文件)
- [x] ats_core/gates/integrated_gates.py
- [x] ats_core/calibration/empirical_calibration.py

### Project中不应该有：
- [ ] setup.sh
- [ ] scripts/realtime_signal_scanner.py
- [ ] ats_core/data/
- [ ] ats_core/outputs/telegram_fmt.py
- [ ] tests/, diagnose/

### 容量占用：
- [ ] 进度条 < 30%（约2M）

---

## 🔧 快速开始

### 步骤1：创建开发者配置（10秒）

```bash
cd /home/user/cryptosignal
cp .claudeignore.developer .claudeignore
git add .claudeignore
git commit -m "feat: 应用开发者导入配置"
git push
```

### 步骤2：Claude.ai导入（2分钟）

1. https://claude.ai → Create Project
2. 名称："CryptoSignal v7.2 Dev"
3. Add from GitHub
4. 仓库：FelixWayne0318/cryptosignal
5. 分支：claude/reorganize-repo-structure-011CV4wShXjHEW61P1kc18W9
6. 让.claudeignore自动过滤

### 步骤3：开始开发（立即可用）

```
"Hi Claude！

我已导入CryptoSignal v7.2的核心开发文件。

请先阅读 CLAUDE_PROJECT_CONTEXT.md 了解系统。

然后帮我分析当前因子权重配置：
- 查看 factor_groups.py 的实现
- 查看 signal_thresholds.json 的配置
- 建议优化方案"
```

---

**创建时间**: 2025-11-13
**系统版本**: v7.2.36
**推荐程度**: ⭐⭐⭐⭐⭐（强烈推荐）

**这才是正确的开发思路！** 🎯
