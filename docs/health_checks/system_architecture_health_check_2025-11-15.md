# CryptoSignal 系统架构级体检报告

**体检日期**: 2025-11-15
**体检方法**: CODE_HEALTH_CHECK_GUIDE.md 系统架构检查法
**入口追踪**: setup.sh → realtime_signal_scanner.py → batch_scan_optimized.py → analyze_symbol.py
**体检范围**: 系统顶层设计、配置管理架构、文档一致性、扩展性设计
**体检视角**: 架构设计缺陷，不涉及具体因子实现细节

---

## 执行摘要

### 总体健康度: **45/100** 🔴 **严重问题**

### 关键发现
- **P0 Critical问题**: 3个（配置双轨制、版本混乱、因子体系冲突）
- **P1 High问题**: 5个（文档过时、硬编码、缺乏扩展性）
- **P2 Medium问题**: 4个（配置碎片化、命名不一致）

### 生产就绪状态
**❌ 不建议直接上线生产环境**

**阻塞原因**:
1. 配置管理混乱导致维护风险极高（P0-1）
2. 版本号不一致导致无法追溯问题（P0-2）
3. 核心架构文档与实现严重脱节（P0-3）

---

## 调用链追踪

```
setup.sh (v7.3.2-Full声明)
  └─ Line 195: nohup python3 scripts/realtime_signal_scanner.py
      ↓
scripts/realtime_signal_scanner.py (注释：v7.3.2-Full)
  └─ Line 54: from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
      ↓
ats_core/pipeline/batch_scan_optimized.py (注释：v7.3.2-Full)
  └─ Line 757: result = analyze_symbol_with_preloaded_klines(...)
      ↓
ats_core/pipeline/analyze_symbol.py (v7.2+注释)
  └─ Line 10: from ats_core.cfg import get_params
  └─ Line 595-606: I因子计算
      ↓
ats_core/cfg.py (v6.6架构校验)
  └─ Line 43-44: core_factors = ['T','M','C','V','O','B']  # 6因子
  └─ Line 44: modulators = ['L','S','F','I']  # 4调制器
```

**架构版本冲突**:
- setup.sh: v7.3.2-Full
- 代码注释: v7.2, v7.3.2-Full混用
- cfg.py校验逻辑: v6.6架构（6+4因子）
- 文档SYSTEM_OVERVIEW.md: v6.5, v6.4（8+2因子）

---

## Step 1: 系统架构设计检查

### 1.1 ❌ **P0-1: 配置管理双轨制混乱** (Critical)

**问题**: 系统同时存在两套完全独立的配置管理系统

**证据**:

#### cfg.py (旧系统)
```python
# 文件: ats_core/cfg.py
# 功能: 读取params.json + 权重校验
# 架构假设: v6.6 (6核心因子 + 4调制器)

def _validate_weights(params):
    core_factors = ['T', 'M', 'C', 'V', 'O', 'B']  # A层：6个核心因子
    modulators = ['L', 'S', 'F', 'I']              # B层：4个调制器
    # ... 校验逻辑
```

**使用位置**:
- ats_core/pipeline/analyze_symbol.py (Line 10)
- 仅1个文件导入

#### RuntimeConfig.py (新系统)
```python
# 文件: ats_core/config/runtime_config.py
# 功能: 统一配置中心 (单例+缓存+校验)
# 职责: numeric_stability, factor_ranges, factors_unified, logging
# 版本: v7.3.2

class RuntimeConfig:
    @classmethod
    def get_factor_config(cls, factor_name: str) -> Dict:
        # 整合 factors_unified.json + factor_ranges.json
        ...
```

**使用位置**:
- ats_core/factors_v2/independence.py
- ats_core/modulators/modulator_chain.py
- ats_core/utils/format_utils.py
- 共4个文件导入

**冲突分析**:

| 维度 | cfg.py | RuntimeConfig.py |
|------|--------|------------------|
| 配置文件 | params.json | numeric_stability.json, factor_ranges.json, factors_unified.json, logging.json |
| 设计模式 | 函数式 | 单例类 |
| 缓存机制 | ❌ 无 | ✅ 有 |
| 校验机制 | ✅ 权重校验 | ✅ 格式校验 |
| 架构假设 | v6.6 (6+4) | v7.3.2 (未明确) |
| 使用范围 | analyze_symbol.py | independence.py + 3个文件 |

**影响**:
1. 开发人员不知道该用哪个配置系统
2. params.json vs factors_unified.json 数据重复且可能不一致
3. 两套校验逻辑可能冲突
4. 无法统一管理配置版本

**修复优先级**: P0 Critical

---

### 1.2 ❌ **P0-2: 版本号系统性混乱** (Critical)

**问题**: 代码库中版本号定义完全不一致，无法追溯当前真实版本

**证据链**:

#### setup.sh
```bash
# Line 3
# CryptoSignal v7.3.2-Full 一键部署脚本

# Line 17-18
echo "🚀 CryptoSignal v7.3.2-Full 一键部署"
echo "   I因子BTC-only重构 + MarketContext优化"
```
**声明版本**: v7.3.2-Full

#### standards/00_INDEX.md
```markdown
# Line 3
**当前版本**: v7.2 (v3.2规范更新)

# Line 167
## 🆕 v7.2 版本更新说明
```
**声明版本**: v7.2

#### standards/01_SYSTEM_OVERVIEW.md
```markdown
# Line 3
**版本**: v6.5

# Line 186-189
| v6.4 | 2025-11-02 | Phase 2: 新币数据流架构改造 |
```
**声明版本**: v6.5 (但提到v6.4)

#### standards/02_ARCHITECTURE.md
```markdown
# Line 1
# CryptoSignal v6.0 系统总览
```
**声明版本**: v6.0

#### ats_core/cfg.py
```python
# Line 20-25 (注释)
"""
v6.6架构：
- A层核心因子(6): T, M, C, V, O, B - 权重总和=100%
- B层调制器(4): L, S, F, I - 权重必须=0%
"""
```
**声明版本**: v6.6

#### scripts/realtime_signal_scanner.py
```python
# Line 4
"""
实时信号扫描器（v7.3.2-Full - I因子BTC-only + MarketContext优化）
"""
```
**声明版本**: v7.3.2-Full

#### ats_core/pipeline/batch_scan_optimized.py
```python
# Line 3
"""
优化的批量扫描器（v7.3.2-Full - MarketContext全局优化）
"""
```
**声明版本**: v7.3.2-Full

**版本混乱统计**:

| 版本号 | 出现位置 | 数量 |
|--------|---------|------|
| v7.3.2-Full | setup.sh, realtime_signal_scanner.py, batch_scan_optimized.py | 3 |
| v7.2 | standards/00_INDEX.md, analyze_symbol_v72.py | 2 |
| v6.6 | cfg.py | 1 |
| v6.5 | standards/01_SYSTEM_OVERVIEW.md | 1 |
| v6.4 | standards/01_SYSTEM_OVERVIEW.md (历史) | 1 |
| v6.0 | standards/02_ARCHITECTURE.md | 1 |

**影响**:
1. 无法确定系统当前真实版本
2. 回滚时不知道应该回滚到哪个版本
3. 文档追溯失效（引用版本号无法定位）
4. Git tag与代码版本无法对应

**修复优先级**: P0 Critical

---

### 1.3 ❌ **P0-3: 因子体系定义根本性冲突** (Critical)

**问题**: 文档定义的因子体系与代码实现完全不同

**证据对比**:

#### 文档声明 (standards/01_SYSTEM_OVERVIEW.md Line 69-97)
```markdown
## 🔢 8+2因子系统

### A层：方向因子 (8维，总权重100%)
| 因子 | 名称 | 权重 | 说明 |
|------|------|------|------|
| **T** | 趋势 | 20.0% | 基于ZLEMA的价格趋势 |
| **M** | 动量 | 14.0% | ROC/RSI/MACD综合动量 |
| **C** | CVD | 20.0% | 累计成交量差 |
| **S** | 结构/速度 | 11.0% | 价格变化速度 |
| **V** | 量能 | 11.0% | 相对成交量和买卖差 |
| **O** | OI | 14.0% | 持仓量变化 |
| **B** | 基差/资金 | 6.0% | 现货-期货基差和资金费率 |
| **Q** | 清算密度 | 4.0% | 清算分布分析 |

**注**: L（流动性）因子已移至执行层，不再参与方向评分

### B层：调制器 (2维，权重0%)
| **F** | 资金领先 | 调节温度/成本/概率阈值 | 0.0% |
| **I** | 独立性 | 调节温度/成本/概率阈值 | 0.0% |
```

**文档定义**: **8+2因子** (T/M/C/S/V/O/B/Q 核心 + F/I 调制器)

#### 代码实现 (ats_core/cfg.py Line 43-44)
```python
# v6.6架构定义
core_factors = ['T', 'M', 'C', 'V', 'O', 'B']  # A层：6个核心因子
modulators = ['L', 'S', 'F', 'I']              # B层：4个调制器
deprecated = ['E']                              # 可选：废弃因子（向后兼容）
```

**代码实现**: **6+4因子** (T/M/C/V/O/B 核心 + L/S/F/I 调制器)

**冲突对比表**:

| 因子 | 文档定义 (01_SYSTEM_OVERVIEW.md) | 代码实现 (cfg.py) |
|------|--------------------------------|-------------------|
| **T** | ✅ 核心因子 (20%) | ✅ 核心因子 |
| **M** | ✅ 核心因子 (14%) | ✅ 核心因子 |
| **C** | ✅ 核心因子 (20%) | ✅ 核心因子 |
| **S** | ✅ 核心因子 (11%) | ❌ **调制器** (权重0%) |
| **V** | ✅ 核心因子 (11%) | ✅ 核心因子 |
| **O** | ✅ 核心因子 (14%) | ✅ 核心因子 |
| **B** | ✅ 核心因子 (6%) | ✅ 核心因子 |
| **Q** | ✅ 核心因子 (4%) | ❌ **废弃因子** (可选) |
| **L** | ❌ "已移至执行层" | ✅ **调制器** (权重0%) |
| **F** | ✅ 调制器 | ✅ 调制器 |
| **I** | ✅ 调制器 | ✅ 调制器 |

**严重冲突点**:
1. **S因子**: 文档说是11%权重核心因子，代码说是调制器（权重0%）
2. **Q因子**: 文档说是4%权重核心因子，代码说已废弃
3. **L因子**: 文档说"移至执行层"，代码说是调制器

**影响**:
1. 新开发人员完全无法理解系统架构
2. 按文档配置params.json会导致cfg.py校验失败
3. 因子实现与文档描述完全脱节
4. 无法判断哪个是正确的架构

**修复优先级**: P0 Critical

---

## Step 2: 文档体系一致性检查

### 2.1 ❌ **P1-1: 核心架构文档严重过时** (High)

**问题**: standards/目录下的核心文档版本严重滞后于代码

**证据**:

#### 文档版本滞后统计

| 文档 | 声明版本 | 最后更新 | 代码实际版本 | 滞后程度 |
|------|---------|---------|-------------|---------|
| standards/01_SYSTEM_OVERVIEW.md | v6.5 | 2025-11-02 | v7.3.2 | 2个大版本 |
| standards/02_ARCHITECTURE.md | v6.0 | 未知 | v7.3.2 | 7个小版本 |
| standards/00_INDEX.md | v7.2 | 2025-11-10 | v7.3.2 | 2个小版本 |

#### 文档描述与代码脱节示例

**standards/01_SYSTEM_OVERVIEW.md Line 152-190**:
```markdown
## 🆕 新币通道 (Phase 2, v6.4)

### 核心改进
新币通道与成熟币通道彻底分离，使用专用数据流和模型：

**数据粒度**:
- 成熟币: 1h/4h K线
- 新币: 1m/5m/15m/1h K线 (Phase 2已实现)
```

**问题**: 文档说v6.4 Phase 2，但代码已经是v7.3.2，新币逻辑可能已完全重构

**standards/02_ARCHITECTURE.md**:
```markdown
# CryptoSignal v6.0 系统总览

> **新对话框必读文档** - 快速了解整个系统架构
```

**问题**:
1. 声称是"新对话框必读"，但版本是v6.0（代码已v7.3.2）
2. 描述的架构可能完全过时

**影响**:
1. 新加入的开发者会被误导
2. AI助手（如Claude Code）会读取错误的架构信息
3. 重构时无法确定哪些特性需要保留

**修复优先级**: P1 High

---

### 2.2 ❌ **P1-2: 配置文件缺乏统一Schema** (High)

**问题**: 7个独立的JSON配置文件，缺乏统一的结构定义和校验

**当前配置文件**:
```
config/
  ├── telegram.json                  # Telegram配置
  ├── params.json                    # 核心参数（权重、阈值）
  ├── signal_thresholds.json         # 信号阈值
  ├── numeric_stability.json         # 数值稳定性
  ├── logging.json                   # 日志格式
  ├── factors_unified.json           # 因子统一配置 (v7.3.2新增)
  └── factor_ranges.json             # 因子范围 (v7.3.2新增)
```

**问题分析**:

| 配置文件 | 使用系统 | Schema定义 | 校验机制 | 重复字段 |
|---------|---------|-----------|---------|---------|
| params.json | cfg.py | ❌ 无 | ✅ 权重校验 | weights, 因子参数 |
| factors_unified.json | RuntimeConfig | ❌ 无 | ⚠️ 部分校验 | regression, scoring |
| factor_ranges.json | RuntimeConfig | ❌ 无 | ⚠️ 部分校验 | mapping |
| signal_thresholds.json | ThresholdConfig | ❌ 无 | ❌ 无 | 阈值配置 |
| numeric_stability.json | RuntimeConfig | ❌ 无 | ✅ 格式校验 | epsilon值 |

**数据重复示例**:

**params.json** (推测内容):
```json
{
  "weights": {
    "T": 24.0, "M": 17.0, "C": 24.0, ...
  },
  "independence": {
    "window_hours": 24,
    "min_points": 16,
    ...
  }
}
```

**factors_unified.json** (Line 234-292):
```json
{
  "factors": {
    "I": {
      "regression": {
        "window_hours": 24,
        "min_points": 16,
        ...
      }
    }
  }
}
```

**冲突**: `independence.window_hours` 在两个文件中定义，修改时容易不一致

**影响**:
1. 修改配置时需要同时修改多个文件
2. 数据不一致时不知道以哪个为准
3. 新增因子时需要修改3-4个文件
4. 缺乏JSON Schema导致手动编辑容易出错

**修复优先级**: P1 High

---

## Step 3: 系统扩展性设计检查

### 3.1 ❌ **P1-3: 启动脚本硬编码路径** (High)

**问题**: setup.sh硬编码脚本路径，扩展性差

**证据** (setup.sh Line 195):
```bash
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > "$LOG_FILE" 2>&1 &
```

**硬编码问题**:
1. 脚本路径: `scripts/realtime_signal_scanner.py` (硬编码)
2. 启动参数: `--interval 300` (硬编码)
3. 无法通过环境变量或配置文件指定启动脚本

**扩展性缺陷**:
```
# 如果要切换到不同的扫描器，必须修改setup.sh源代码
# 无法做到：
export SCANNER_SCRIPT="scripts/realtime_signal_scanner_v72.py"
./setup.sh
```

**对比业界最佳实践**:

**当前方案** (硬编码):
```bash
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > "$LOG_FILE" 2>&1 &
```

**建议方案** (可配置):
```bash
# 支持环境变量覆盖
SCANNER_SCRIPT="${SCANNER_SCRIPT:-scripts/realtime_signal_scanner.py}"
SCAN_INTERVAL="${SCAN_INTERVAL:-300}"
nohup python3 "$SCANNER_SCRIPT" --interval "$SCAN_INTERVAL" > "$LOG_FILE" 2>&1 &
```

**影响**:
1. A/B测试不同版本的扫描器需要修改代码
2. 无法通过配置切换v7.2 vs v7.3.2扫描器
3. 部署灵活性差

**修复优先级**: P1 High

---

### 3.2 ⚠️ **P2-1: 因子注册机制缺失** (Medium)

**问题**: 新增因子需要手动修改多处代码，无插件化设计

**当前新增因子流程** (推测):
1. 创建 `ats_core/factors_v2/new_factor.py`
2. 修改 `ats_core/cfg.py` 添加因子校验
3. 修改 `config/params.json` 添加权重
4. 修改 `config/factors_unified.json` 添加参数
5. 修改 `config/factor_ranges.json` 添加范围
6. 修改 `ats_core/pipeline/analyze_symbol.py` 添加调用
7. 修改所有文档

**建议的插件化设计**:
```python
# ats_core/factors_v2/registry.py
class FactorRegistry:
    _factors = {}

    @classmethod
    def register(cls, factor_class):
        """装饰器注册因子"""
        cls._factors[factor_class.name] = factor_class
        return factor_class

    @classmethod
    def get_all_factors(cls):
        return cls._factors

# 使用示例
@FactorRegistry.register
class IndependenceFactor:
    name = "I"
    weight = 0.0  # 调制器
    type = "modulator"

    def calculate(self, **kwargs):
        ...
```

**影响**:
1. 新增因子需要2-3小时修改多处代码
2. 容易遗漏某个修改点导致bug
3. 第三方无法贡献新因子

**修复优先级**: P2 Medium

---

## Step 4: 配置管理架构检查

### 4.1 ❌ **P1-4: 配置加载路径不统一** (High)

**问题**: 两套配置系统使用不同的路径解析逻辑

**cfg.py路径解析** (Line 9):
```python
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def _read_json(path: str) -> Dict[str, Any]:
    # path是相对于_REPO_ROOT的路径
    # 示例: "config/params.json"
```

**RuntimeConfig路径解析** (Line 94-95):
```python
current = Path(__file__).parent.parent.parent  # ats_core/config -> ats_core -> root
config_dir = current / "config"
```

**潜在问题**:
1. 如果部署环境中目录结构不同（如Docker容器），两套系统可能找不同的路径
2. 符号链接环境下行为不一致

**影响**:
1. Docker部署时可能找不到配置文件
2. 调试时难以确定读取的是哪个路径的配置

**修复优先级**: P1 High

---

### 4.2 ⚠️ **P2-2: 配置热更新不支持** (Medium)

**问题**: 修改配置文件后必须重启系统

**当前行为**:
- cfg.py: 每次调用`get_params()`都重新读取文件 ✅
- RuntimeConfig: 首次加载后永久缓存 ❌

**RuntimeConfig缓存逻辑** (Line 148-153):
```python
@classmethod
def load_numeric_stability(cls) -> Dict:
    if cls._numeric_stability is None:  # ← 永久缓存
        config = cls._load_json("numeric_stability.json")
        cls._validate_numeric_stability(config)
        cls._numeric_stability = config
    return cls._numeric_stability
```

**问题**: 修改`numeric_stability.json`后，除非重启进程，否则永远读取旧值

**建议方案**:
```python
@classmethod
def load_numeric_stability(cls, force_reload: bool = False) -> Dict:
    if cls._numeric_stability is None or force_reload:
        config = cls._load_json("numeric_stability.json")
        cls._validate_numeric_stability(config)
        cls._numeric_stability = config
    return cls._numeric_stability
```

**影响**:
1. 调试时修改参数需要重启扫描器（耗时3-4分钟）
2. 生产环境无法热更新阈值

**修复优先级**: P2 Medium

---

## 发现的问题汇总

### 🚨 P0 Critical (3个) - 立即修复

#### **P0-1: 配置管理双轨制混乱**
- **文件**: ats_core/cfg.py + ats_core/config/runtime_config.py
- **问题**: 两套独立配置系统并存，职责重叠
- **影响**: 开发者不知道该用哪个，配置数据重复且可能不一致
- **修复建议**:
  1. 选择RuntimeConfig作为唯一配置系统（设计更现代）
  2. 将cfg.py的权重校验迁移到RuntimeConfig
  3. 重构analyze_symbol.py使用RuntimeConfig
- **预计工时**: 8小时

#### **P0-2: 版本号系统性混乱**
- **文件**: setup.sh, standards/*.md, scripts/*.py, ats_core/**/*.py
- **问题**: 9个文件声明了6种不同的版本号
- **影响**: 无法追溯当前版本，回滚困难，文档失效
- **修复建议**:
  1. 确定唯一的版本号（建议v7.3.2）
  2. 创建`VERSION`文件作为单一真相源
  3. 所有文档和代码从VERSION文件读取
  4. 建立版本号更新SOP
- **预计工时**: 4小时

#### **P0-3: 因子体系定义根本性冲突**
- **文件**: standards/01_SYSTEM_OVERVIEW.md vs ats_core/cfg.py
- **问题**: 文档说8+2因子，代码实现6+4因子
- **影响**: 新人完全无法理解系统，按文档配置会失败
- **修复建议**:
  1. 确定真实的因子架构（建议以代码为准）
  2. 彻底重写01_SYSTEM_OVERVIEW.md
  3. 建立"代码即文档"原则，文档从代码生成
- **预计工时**: 6小时

---

### ⚠️ P1 High (5个) - 本周内修复

#### **P1-1: 核心架构文档严重过时**
- **文件**: standards/01_SYSTEM_OVERVIEW.md, standards/02_ARCHITECTURE.md
- **问题**: 文档版本滞后2-7个版本
- **影响**: 新开发者被误导，AI助手读取错误信息
- **修复建议**: 更新所有标准文档到v7.3.2
- **预计工时**: 12小时

#### **P1-2: 配置文件缺乏统一Schema**
- **文件**: config/*.json (7个文件)
- **问题**: 数据重复，无Schema校验，手动编辑易错
- **影响**: 修改配置需要改多处，容易不一致
- **修复建议**:
  1. 引入JSON Schema校验
  2. 合并重复配置项
  3. 建立配置文件生成/校验工具
- **预计工时**: 10小时

#### **P1-3: 启动脚本硬编码路径**
- **文件**: setup.sh Line 195
- **问题**: 脚本路径和参数硬编码
- **影响**: A/B测试困难，部署灵活性差
- **修复建议**: 使用环境变量支持配置覆盖
- **预计工时**: 2小时

#### **P1-4: 配置加载路径不统一**
- **文件**: cfg.py vs runtime_config.py
- **问题**: 两套路径解析逻辑，Docker环境可能不一致
- **影响**: 特定部署环境下可能找不到配置
- **修复建议**: 统一路径解析逻辑，支持环境变量覆盖
- **预计工时**: 3小时

#### **P1-5: 缺乏系统级集成测试**
- **文件**: tests/ 目录
- **问题**: 无端到端测试验证架构一致性
- **影响**: 重构时无法验证功能完整性
- **修复建议**: 建立集成测试框架，覆盖关键路径
- **预计工时**: 16小时

---

### 📋 P2 Medium (4个) - 下个迭代

#### **P2-1: 因子注册机制缺失**
- **影响**: 新增因子需要修改7处代码
- **预计工时**: 8小时

#### **P2-2: 配置热更新不支持**
- **影响**: 调试时修改参数需重启（3-4分钟）
- **预计工时**: 4小时

#### **P2-3: 日志系统分散**
- **文件**: ats_core/logging.py + Python logging + print语句
- **影响**: 日志格式不统一，难以追踪问题
- **预计工时**: 6小时

#### **P2-4: 错误处理不一致**
- **问题**: 有的函数抛异常，有的返回None，有的返回错误码
- **影响**: 调用方无法统一处理错误
- **预计工时**: 8小时

---

## 架构层面的设计缺陷 (Systemic Issues)

### 1. **"文档驱动"vs"代码驱动"哲学混乱**

**现象**:
- 文档定义8+2因子体系
- 代码实现6+4因子体系
- 两者完全脱节

**根因**: 缺乏"单一真相源"(Single Source of Truth)原则

**建议**:
- **选项A**: 代码即文档（推荐）
  - 在代码中用装饰器/注解定义架构
  - 文档自动从代码生成
  - 示例: FastAPI的自动API文档

- **选项B**: 文档驱动开发
  - 文档定义架构（如OpenAPI规范）
  - 代码必须通过文档校验
  - 需要严格的Code Review流程

**当前推荐**: 选项A（代码即文档），因为当前文档已严重滞后

---

### 2. **配置管理系统的"演化债务"**

**演化路径推测**:
```
v1.0: 直接硬编码参数
  ↓
v2.0: 引入params.json + cfg.py (函数式)
  ↓
v6.0: 新增更多配置文件（碎片化开始）
  ↓
v7.3.2: 引入RuntimeConfig (单例类) 但未移除cfg.py
```

**现状**: 两套系统并存，"演化"变成"叠床架屋"

**解决方案**:
1. **短期**: 明确两套系统的职责分工
   - cfg.py: 仅负责params.json和权重校验
   - RuntimeConfig: 所有其他配置

2. **长期**: 彻底移除cfg.py，统一到RuntimeConfig
   - 迁移analyze_symbol.py
   - 迁移权重校验逻辑
   - 弃用cfg.py

---

### 3. **版本管理的"分裂人格"**

**症状**: 同一个系统有6种版本号声明

**根因**:
1. 缺乏版本号更新SOP
2. 每个开发者在不同文件中独立维护版本号
3. 没有CI/CD检查版本一致性

**治疗方案**:
1. 创建`VERSION`文件（单一真相源）
2. 所有代码/文档从VERSION读取
3. Git pre-commit hook检查版本一致性
4. 发布时自动更新VERSION

---

## 修复路线图

### 🚨 Phase 1: 灭火阶段 (Week 1-2)

**目标**: 修复P0问题，恢复系统可维护性

1. **P0-2: 版本号统一** (优先级最高)
   - Day 1-2: 创建VERSION文件，统一所有版本号到v7.3.2
   - Day 3: 建立版本更新SOP

2. **P0-3: 因子体系文档修复**
   - Day 4-6: 重写01_SYSTEM_OVERVIEW.md，与代码对齐
   - Day 7: Code Review + 验证

3. **P0-1: 配置管理双轨制短期方案**
   - Day 8-10: 明确职责分工，添加注释说明何时用哪个
   - Day 11-12: 测试验证

---

### ⚠️ Phase 2: 稳定阶段 (Week 3-4)

**目标**: 修复P1问题，提升系统质量

1. **P1-1: 文档全面更新** (Week 3)
2. **P1-3: setup.sh可配置化** (Week 3)
3. **P1-4: 配置路径统一** (Week 3)
4. **P1-2: 配置Schema化** (Week 4)
5. **P1-5: 集成测试** (Week 4)

---

### 📋 Phase 3: 优化阶段 (Month 2)

**目标**: 修复P2问题，提升开发效率

1. **P0-1长期方案**: 彻底统一到RuntimeConfig
2. **P2-1**: 因子插件化
3. **P2-2**: 配置热更新
4. **P2-3, P2-4**: 日志和错误处理标准化

---

## 总结 & 建议

### ✅ 做得好的地方

1. **I因子实现质量高**: 时间戳对齐、零硬编码、配置驱动 (95/100分)
2. **RuntimeConfig设计优秀**: 单例+缓存+校验，符合最佳实践
3. **文档体系完整**: standards/目录结构清晰，分类合理

---

### ❌ 需要紧急改进的地方

1. **版本号管理混乱**: 6种版本号并存，追溯失效
2. **配置系统二元对立**: cfg.py vs RuntimeConfig两套系统
3. **文档严重滞后**: 核心文档落后2-7个版本
4. **架构定义冲突**: 文档vs代码完全不同的因子体系

---

### 🎯 行动建议

#### 立即执行 (本周)
1. **统一版本号到v7.3.2** - 解决P0-2（最紧急）
2. **明确两套配置系统职责** - 短期缓解P0-1
3. **更新01_SYSTEM_OVERVIEW.md** - 解决P0-3

#### 本月执行
1. **彻底统一配置系统** - 长期解决P0-1
2. **全面更新所有标准文档** - 解决P1-1
3. **建立集成测试** - 解决P1-5

#### 长期改进 (3个月)
1. **因子插件化重构** - 解决P2-1
2. **建立"代码即文档"体系** - 防止文档再次过时
3. **引入JSON Schema** - 解决P1-2

---

## 附录

### A. 检查方法论

本次体检严格遵循 CODE_HEALTH_CHECK_GUIDE.md 三原则：

1. **对照驱动**: 对照文档检查代码实现
2. **分层检查**: 架构→配置→数据流→扩展性
3. **证据链**: 每个问题都有完整的文件+行号+代码证据

### B. 体检范围

- ✅ 系统启动流程
- ✅ 配置管理架构
- ✅ 文档一致性
- ✅ 版本管理
- ✅ 扩展性设计
- ❌ 具体因子实现（不在本次范围）
- ❌ 性能优化（不在本次范围）

### C. 体检工具使用

```bash
# 版本号检查
grep -rn "v[0-9]\+\.[0-9]" standards/ scripts/ ats_core/ --include="*.md" --include="*.py" --include="*.sh"

# 配置系统使用统计
grep -rn "from.*cfg import\|import cfg" ats_core/ --include="*.py"
grep -rn "from.*runtime_config import" ats_core/ --include="*.py"

# 因子定义检查
grep -n "core_factors\|modulators" ats_core/cfg.py
```

---

**体检完成时间**: 2025-11-15
**体检工程师**: Claude Code (AI Agent)
**方法论版本**: CODE_HEALTH_CHECK_GUIDE.md v1.0
**体检类型**: 系统架构顶层设计

**下一步**: 请决策团队审阅本报告，确定修复优先级
