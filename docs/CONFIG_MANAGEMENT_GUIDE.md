# 配置管理指南

**版本**: v7.3.2
**创建日期**: 2025-11-15
**状态**: 临时指南（v8.0将统一配置系统）

---

## 🎯 目的

解决v7.3.2中存在的**配置管理双轨制**问题（P0-1），明确两套配置系统的职责划分。

**问题背景**: 参见 `docs/health_checks/system_architecture_health_check_2025-11-15.md#P0-1`

---

## 📋 配置系统对比

### 系统概览

| 配置系统 | 文件位置 | 职责 | 状态 | 推荐使用 |
|---------|---------|------|------|---------|
| **cfg.py** | `ats_core/cfg.py` | params.json + 权重校验 | 🔴 将废弃（v8.0） | ❌ 不推荐 |
| **RuntimeConfig** | `ats_core/config/runtime_config.py` | 所有其他配置 | ✅ 推荐使用 | ✅ 推荐 |

### 详细对比

| 维度 | cfg.py | RuntimeConfig |
|------|--------|---------------|
| **配置文件** | params.json | numeric_stability.json, factor_ranges.json, factors_unified.json, logging.json |
| **设计模式** | 函数式 | 单例类 |
| **缓存机制** | ❌ 无（每次读取文件） | ✅ 有（懒加载+缓存） |
| **校验机制** | ✅ 权重校验 | ✅ 格式校验 |
| **架构假设** | v6.6 (6+4因子) | v7.3.2 |
| **使用范围** | analyze_symbol.py | independence.py + modulators + utils |
| **未来计划** | 🔴 v8.0废弃 | ✅ 长期维护 |

---

## 📌 使用指南

### 场景1: 读取因子参数

#### ❌ 旧方式（不推荐）
```python
from ats_core.cfg import get_params

params = get_params()
i_params = params.get("independence", {})
window_hours = i_params.get("window_hours", 24)  # 硬编码默认值
```

**问题**:
- params.json可能不包含该配置
- 默认值硬编码在代码中
- 无缓存，重复读取文件

#### ✅ 新方式（推荐）
```python
from ats_core.config.runtime_config import RuntimeConfig

# 方法1: 获取完整因子配置
i_config = RuntimeConfig.get_factor_config("I")
regression_params = i_config["regression"]
window_hours = regression_params["window_hours"]

# 方法2: 获取数值稳定性配置
stability = RuntimeConfig.get_numeric_stability("independence")
eps_var_min = stability["eps_var_min"]
```

**优势**:
- 配置集中管理（factors_unified.json）
- 懒加载+缓存
- 类型安全+格式校验

---

### 场景2: 验证因子权重

#### ❌ 旧方式（不推荐）
```python
from ats_core.cfg import get_params

params = get_params()
# cfg.py会自动校验权重
```

**问题**:
- 仅支持v6.6架构（6+4因子）
- 与实际代码架构不一致

#### ✅ 新方式（推荐）
```python
from ats_core.config.runtime_config import RuntimeConfig

# RuntimeConfig尚未实现权重校验
# TODO: v8.0迁移权重校验逻辑到RuntimeConfig
```

**临时方案**: 权重校验仍使用cfg.py（v8.0前）

---

### 场景3: 读取信号阈值

#### ❌ 旧方式（不推荐）
```python
from ats_core.cfg import get_params

params = get_params()
publish_cfg = params.get("publish", {})
prime_prob_min = publish_cfg.get("prime_prob_min", 0.68)  # 硬编码
```

**问题**:
- params.json与signal_thresholds.json冲突
- 默认值与配置文件不一致

#### ✅ 新方式（推荐）
```python
from ats_core.config.threshold_config import get_thresholds

config = get_thresholds()
prime_prob_min = config.get_mature_threshold('prime_prob_min', 0.45)
```

**优势**:
- 统一使用signal_thresholds.json
- 默认值与配置文件一致
- 支持新币/成熟币分离配置

---

## 🛠️ 迁移策略

### 短期方案（v7.3.2 - v7.9）

**明确职责划分**:
```
cfg.py:
  - 仅负责 params.json 读取
  - 仅负责权重校验（v6.6架构）
  - 仅 analyze_symbol.py 使用（向后兼容）
  - ❌ 新代码禁止使用

RuntimeConfig:
  - 负责所有其他配置文件
  - ✅ 所有新代码使用此系统
  - ✅ 逐步迁移旧代码
```

### 长期方案（v8.0）

**完全统一到RuntimeConfig**:
1. 迁移权重校验逻辑到RuntimeConfig
2. 重构analyze_symbol.py使用RuntimeConfig
3. 废弃cfg.py
4. params.json仅作归档

**预计工时**: 8小时

---

## 📁 配置文件职责划分

### 配置文件层次

```
config/
├── signal_thresholds.json    ← 信号阈值（优先级最高）
│   └── RuntimeConfig (通过ThresholdConfig)
│
├── factors_unified.json       ← 因子统一配置
│   └── RuntimeConfig
│
├── factor_ranges.json         ← 因子范围配置
│   └── RuntimeConfig
│
├── numeric_stability.json     ← 数值稳定性
│   └── RuntimeConfig
│
├── logging.json               ← 日志格式
│   └── RuntimeConfig
│
└── params.json                ← 系统参数（废弃中）
    └── cfg.py（仅兼容）
```

### 配置文件优先级

当存在配置冲突时：
```
signal_thresholds.json > factors_unified.json > params.json
```

**原则**: 优先使用最新、最专门的配置文件

---

## ⚠️ 注意事项

### 1. 避免配置冲突

**❌ 错误**:
```python
# 同时使用两套系统读取同一参数
from ats_core.cfg import get_params
from ats_core.config.runtime_config import RuntimeConfig

params = get_params()
old_value = params.get("independence", {}).get("window_hours", 24)

new_config = RuntimeConfig.get_factor_config("I")
new_value = new_config["regression"]["window_hours"]

# old_value != new_value 时会混乱！
```

**✅ 正确**:
```python
# 统一使用一套系统
from ats_core.config.runtime_config import RuntimeConfig

config = RuntimeConfig.get_factor_config("I")
window_hours = config["regression"]["window_hours"]
```

### 2. 不要硬编码默认值

**❌ 错误**:
```python
window_hours = config.get("window_hours", 24)  # 24是硬编码
```

**✅ 正确**:
```python
# 方法1: 从配置文件读取，确保有默认值定义在配置文件中
window_hours = config["window_hours"]  # 配置文件必须定义

# 方法2: 使用配置类的默认值（与配置文件一致）
window_hours = config.get("window_hours", config.DEFAULT_WINDOW_HOURS)
```

### 3. 更新配置后清除缓存

**问题**: RuntimeConfig有缓存机制，修改配置文件后需要重启

**解决方案** (v8.0将支持热更新):
```python
# 当前: 必须重启进程
pkill -f realtime_signal_scanner.py
./setup.sh

# 未来: 支持force_reload
RuntimeConfig.load_numeric_stability(force_reload=True)
```

---

## 📊 迁移进度跟踪

### 当前使用情况（v7.3.2）

| 模块 | 使用系统 | 迁移状态 |
|------|---------|---------|
| analyze_symbol.py | cfg.py | ⏸️ 待迁移（v8.0） |
| independence.py | RuntimeConfig | ✅ 已迁移 |
| modulators/*.py | RuntimeConfig | ✅ 已迁移 |
| utils/*.py | RuntimeConfig | ✅ 已迁移 |
| 权重校验 | cfg.py | ⏸️ 待迁移（v8.0） |

**迁移进度**: 60% (3/5模块)

---

## 🔗 相关文档

- **体检报告**: `docs/health_checks/system_architecture_health_check_2025-11-15.md`
- **系统增强标准**: `standards/SYSTEM_ENHANCEMENT_STANDARD.md`
- **配置指南**: `docs/CONFIGURATION_GUIDE.md`

---

## 📝 常见问题

### Q1: 为什么有两套配置系统？

**A**: 历史演化原因。cfg.py是v6.6时代的产物，RuntimeConfig是v7.3.2新引入的现代化设计。为了向后兼容，暂时保留两套系统。

### Q2: 我应该使用哪个系统？

**A**:
- **新代码**: 使用RuntimeConfig
- **旧代码**: 保持现状（v8.0统一迁移）
- **权重校验**: 暂时使用cfg.py

### Q3: 什么时候统一配置系统？

**A**: v8.0版本（预计2个月后）

### Q4: params.json会被删除吗？

**A**: 不会删除，但会变成归档文件，仅作向后兼容。新参数不应添加到params.json。

---

**最后更新**: 2025-11-15
**维护责任**: 系统架构师
**审核周期**: 每季度
