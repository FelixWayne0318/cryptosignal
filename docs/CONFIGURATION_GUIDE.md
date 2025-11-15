# 配置管理指南

**版本**: v7.2.44
**更新日期**: 2025-11-14
**文档类型**: 配置管理和参数修改指南

---

## 📋 目录

1. [配置文件结构](#配置文件结构)
2. [硬编码问题现状](#硬编码问题现状)
3. [如何修改参数](#如何修改参数)
4. [配置优先级](#配置优先级)
5. [常见配置场景](#常见配置场景)
6. [配置验证](#配置验证)

---

## 配置文件结构

### 配置文件位置

系统有2个主要配置文件：

```
cryptosignal/
├── config/
│   ├── factors_unified.json      # 因子参数配置（447行）
│   └── signal_thresholds.json    # 信号阈值配置（718行）
```

### 配置文件职责

| 配置文件 | 职责 | 包含内容 |
|---------|------|---------|
| **factors_unified.json** | 因子计算参数 | 10个因子/调制器的所有计算参数、权重、StandardizationChain参数 |
| **signal_thresholds.json** | 信号生成阈值 | 新币阶段识别、阈值平滑、质量补偿、数据质量要求、Gate规则 |

---

## 硬编码问题现状

### ✅ 已解决的硬编码

**v3.0配置化改造**（2025-11-09）完成了大部分因子的去硬编码：

| 因子/调制器 | 配置文件 | 硬编码状态 | 备注 |
|-----------|---------|-----------|------|
| **T（趋势）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **M（动量）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **C+（CVD）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **V+（量能）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **O+（OI）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **S（结构）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **L（流动性）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **B（基差+资金费）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **F（资金领先）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |
| **I（独立性）** | factors_unified.json | ✅ 已去除 | 使用get_factor_config() |

### ⚠️ 仍存在的硬编码Fallback值

虽然系统已配置化，但**所有因子都保留了硬编码fallback值**作为向后兼容措施：

```python
# 典型的fallback模式（trend.py为例）
try:
    config = get_factor_config()
    config_params = config.get_factor_params("T")
except Exception as e:
    # ⚠️ 配置加载失败时使用硬编码默认值（向后兼容）
    print(f"⚠️ T因子配置加载失败，使用默认值: {e}")
    config_params = {
        "ema_order_min_bars": 6,
        "slope_lookback": 12,
        "atr_period": 14,
        "slope_scale": 0.08,
        "ema_bonus": 12.5,
        "r2_weight": 0.15,
    }
```

**Fallback值存在于以下文件**：

| 文件 | Fallback值数量 | 原因 |
|------|--------------|------|
| `ats_core/features/trend.py` | 6个参数 | 向后兼容 |
| `ats_core/features/momentum.py` | 8个参数 | 向后兼容 |
| `ats_core/features/cvd.py` | 5个参数 | 向后兼容 |
| `ats_core/features/volume.py` | 6个参数 | 向后兼容 |
| `ats_core/features/open_interest.py` | 7个参数 | 向后兼容 |
| `ats_core/features/structure_sq.py` | 5个参数 | 向后兼容 |
| `ats_core/features/fund_leading.py` | 12个参数 | 向后兼容 |
| `ats_core/factors_v2/basis_funding.py` | 4个参数 | 向后兼容 |
| `ats_core/factors_v2/independence.py` | 5个参数 | 向后兼承 |

### 🎯 是否需要移除Fallback？

**建议保留Fallback值**，原因：

1. **鲁棒性**: 配置文件损坏时系统仍能运行
2. **向后兼容**: 旧版本代码可以直接运行
3. **紧急恢复**: 配置错误时可快速回退
4. **单元测试**: 测试时无需依赖配置文件

**但应确保**：
- ✅ Fallback值与配置文件中的默认值**完全一致**
- ✅ 修改参数时**同时更新**配置文件和fallback值
- ✅ 使用配置文件作为**唯一真实来源**（Single Source of Truth）

---

## 如何修改参数

### 方法1: 修改配置文件（推荐）

这是**标准且推荐**的方法。

#### 步骤1: 找到配置文件

```bash
# 因子计算参数
vim config/factors_unified.json

# 信号阈值参数
vim config/signal_thresholds.json
```

#### 步骤2: 修改参数

**示例1: 修改T因子的斜率缩放因子**

```json
// config/factors_unified.json
{
  "factors": {
    "T": {
      "params": {
        "slope_scale": 0.08,  // 修改这里（原值0.08 → 0.10）
        ...
      }
    }
  }
}
```

**示例2: 修改L调制器的冲击测试规模**

```json
// config/factors_unified.json
{
  "factors": {
    "L": {
      "params": {
        "impact_notional_usdt": 100000,  // 修改这里（原值100000 → 50000）
        ...
      }
    }
  }
}
```

**示例3: 修改新币阶段识别阈值**

```json
// config/signal_thresholds.json
{
  "新币阶段识别": {
    "ultra_new_hours": 24,    // 修改这里（原值24 → 48）
    "phase_A_hours": 168,     // 7天
    "phase_B_hours": 400      // 16.7天
  }
}
```

#### 步骤3: 验证JSON格式

```bash
# 使用Python验证JSON格式
python3 -c "import json; json.load(open('config/factors_unified.json'))" && echo "✅ JSON格式正确"

# 或使用jq验证
jq . config/factors_unified.json > /dev/null && echo "✅ JSON格式正确"
```

#### 步骤4: 重启系统

```bash
# 配置文件修改后需要重启才能生效
# （系统启动时加载配置，运行中不会动态重新加载）

# 方法1: 重启批量扫描
./setup.sh

# 方法2: 重启单个脚本
python3 scripts/realtime_signal_scanner.py
```

### 方法2: 通过params参数覆盖（临时测试）

用于**临时测试**或**单次运行**，不修改配置文件。

```python
from ats_core.features.trend import score_trend

# 临时覆盖参数
custom_params = {
    "slope_scale": 0.10,    # 临时改为0.10
    "ema_bonus": 15.0       # 临时改为15.0
}

T, metadata = score_trend(klines, params=custom_params)
```

**优先级**: `params参数` > `配置文件` > `硬编码fallback`

### 方法3: 修改配置文件+同步Fallback（完整方案）

用于**永久性修改**且需要确保一致性。

#### 步骤1: 修改配置文件（如上）

#### 步骤2: 同步修改Fallback值

```python
# ats_core/features/trend.py

try:
    config = get_factor_config()
    config_params = config.get_factor_params("T")
except Exception as e:
    print(f"⚠️ T因子配置加载失败，使用默认值: {e}")
    config_params = {
        "ema_order_min_bars": 6,
        "slope_lookback": 12,
        "atr_period": 14,
        "slope_scale": 0.10,    # 同步修改为0.10
        "ema_bonus": 12.5,
        "r2_weight": 0.15,
    }
```

#### 步骤3: 提交Git

```bash
git add config/factors_unified.json ats_core/features/trend.py
git commit -m "config: 调整T因子slope_scale从0.08到0.10

理由: <说明修改原因>
影响: <说明预期影响>
测试: <说明测试结果>
"
```

---

## 配置优先级

### 优先级顺序

```
函数params参数 > 配置文件 > 硬编码fallback
   (临时)         (标准)        (应急)
```

### 示例

```python
# 配置文件中：slope_scale = 0.08
# Fallback中：slope_scale = 0.08
# 函数调用：params={'slope_scale': 0.10}

T, meta = score_trend(klines, params={'slope_scale': 0.10})
# 实际使用：0.10（函数参数优先）

T, meta = score_trend(klines)
# 实际使用：0.08（配置文件）

# 如果配置文件损坏
T, meta = score_trend(klines)
# 实际使用：0.08（fallback）
```

---

## 常见配置场景

### 场景1: 调整因子权重

**需求**: 提高CVD因子权重，降低基差权重

```json
// config/factors_unified.json
{
  "factors": {
    "C+": {
      "weight": 25,  // 20 → 25（提高5%）
      ...
    },
    "B": {
      "weight": 3,   // 5 → 3（降低2%）
      ...
    },
    "T": {
      "weight": 23,  // 25 → 23（降低2%，平衡总和）
      ...
    }
  }
}
```

**注意**: A层6个评分因子权重总和应为100%。

### 场景2: 调整新币阶段阈值

**需求**: 放宽新币进入mature阶段的要求（从16.7天缩短到14天）

```json
// config/signal_thresholds.json
{
  "新币阶段识别": {
    "ultra_new_hours": 24,
    "phase_A_hours": 168,
    "phase_B_hours": 336,   // 400 → 336（14天）
    "_stages": {
      "mature": "≥ 336小时（14天+）"  // 更新注释
    }
  }
}
```

### 场景3: 调整流动性四道闸阈值

**需求**: 放宽冲击成本阈值（从10bps提高到15bps）

```json
// config/factors_unified.json
{
  "factors": {
    "L": {
      "params": {
        "impact_max_pct": 0.0015,  // 0.01 → 0.0015（10bps → 15bps）
        ...
      }
    }
  }
}
```

**对应修改signal_thresholds.json**:

```json
// config/signal_thresholds.json
{
  "L调制器配置": {
    "impact_threshold_bps": 15,  // 10 → 15
    ...
  }
}
```

### 场景4: 启用/禁用某个因子

**需求**: 临时禁用B因子（基差+资金费）

```json
// config/factors_unified.json
{
  "factors": {
    "B": {
      "enabled": false,  // true → false
      "weight": 0,       // 5 → 0（权重也设为0）
      ...
    }
  }
}
```

**注意**: 禁用因子后需要重新平衡其他因子的权重。

### 场景5: 调整StandardizationChain参数

**需求**: 让S调制器更敏感（降低平滑度）

```json
// config/factors_unified.json
{
  "global": {
    "standardization": {
      "factor_overrides": {
        "S": {
          "alpha": 0.05,
          "tau": 2.0,
          "z0": 2.0,     // 2.5 → 2.0（降低soft-clipping起始点）
          "lam": 3.0
        }
      }
    }
  }
}
```

---

## 配置验证

### 自动验证脚本

```python
#!/usr/bin/env python3
"""
配置文件验证脚本
用法: python3 scripts/validate_config.py
"""

import json
import sys

def validate_factors_unified():
    """验证factors_unified.json"""
    try:
        with open('config/factors_unified.json', 'r') as f:
            config = json.load(f)

        # 检查必需字段
        assert 'version' in config, "缺少version字段"
        assert 'factors' in config, "缺少factors字段"

        # 检查A层因子权重总和
        a_layer_factors = ['T', 'M', 'C+', 'V+', 'O+', 'B']
        total_weight = sum(
            config['factors'][f]['weight']
            for f in a_layer_factors
            if f in config['factors']
        )

        assert abs(total_weight - 100) < 1, f"A层因子权重总和应为100，实际为{total_weight}"

        # 检查B层调制器权重为0
        b_layer_modulators = ['L', 'S', 'F', 'I']
        for mod in b_layer_modulators:
            if mod in config['factors']:
                weight = config['factors'][mod].get('weight', 0)
                assert weight == 0, f"{mod}调制器权重应为0，实际为{weight}"

        print("✅ factors_unified.json 验证通过")
        return True

    except Exception as e:
        print(f"❌ factors_unified.json 验证失败: {e}")
        return False

def validate_signal_thresholds():
    """验证signal_thresholds.json"""
    try:
        with open('config/signal_thresholds.json', 'r') as f:
            config = json.load(f)

        # 检查新币阶段识别
        stages = config.get('新币阶段识别', {})
        assert stages['ultra_new_hours'] < stages['phase_A_hours'], \
            "ultra_new_hours应小于phase_A_hours"
        assert stages['phase_A_hours'] < stages['phase_B_hours'], \
            "phase_A_hours应小于phase_B_hours"

        print("✅ signal_thresholds.json 验证通过")
        return True

    except Exception as e:
        print(f"❌ signal_thresholds.json 验证失败: {e}")
        return False

if __name__ == '__main__':
    success = True
    success &= validate_factors_unified()
    success &= validate_signal_thresholds()

    sys.exit(0 if success else 1)
```

### 运行验证

```bash
# 创建验证脚本
cat > scripts/validate_config.py << 'EOF'
<粘贴上面的脚本>
EOF

# 运行验证
python3 scripts/validate_config.py

# 预期输出:
# ✅ factors_unified.json 验证通过
# ✅ signal_thresholds.json 验证通过
```

---

## 配置文件结构详解

### factors_unified.json结构

```json
{
  "version": "3.0.0",
  "updated_at": "2025-11-09",
  "description": "统一因子参数配置",

  "global": {
    "standardization": {
      "enabled": true,
      "default_params": {
        "alpha": 0.25,    // Winsorization阈值
        "tau": 5.0,       // Huber损失阈值
        "z0": 3.0,        // Soft-clipping起始点
        "zmax": 6.0,      // Soft-clipping最大值
        "lam": 1.5        // Logistic函数陡度
      },
      "factor_overrides": {
        "T": {...},       // T因子特殊参数
        "S": {...}        // S调制器特殊参数
      }
    },
    "data_quality": {
      "min_data_points": {...},
      "historical_lookback": {...}
    },
    "degradation": {
      "fallback_strategy": "zero_score",
      "allow_partial_data": false
    }
  },

  "factors": {
    "T": {
      "name": "Trend",
      "layer": "price_action",
      "weight": 25,              // A层评分因子权重
      "enabled": true,
      "description": "趋势强度",
      "params": {
        "ema_order_min_bars": 6,
        "slope_lookback": 12,
        "atr_period": 14,
        "slope_scale": 0.08,
        "ema_bonus": 12.5,
        "r2_weight": 0.15
      }
    },
    // ... 其他因子 ...

    "L": {
      "name": "Liquidity",
      "layer": "microstructure",
      "weight": 0,               // B层调制器权重为0
      "enabled": true,
      "description": "流动性质量",
      "params": {
        "spread_good_bps": 2.0,
        "depth_target_usdt": 1000000,
        // ... 其他参数 ...
      }
    }
  },

  "thresholds": {
    "composite_score_min": 50,
    "confidence_min": 15,
    "edge_min": 0.12
  },

  "risk_management": {
    "max_position_size": 0.1,
    "default_stop_loss_pct": 0.02
  },

  "weights_config": {
    "mode": "static",
    "custom_weights": null
  },

  "adaptive_weights": {
    "enabled": false,
    "regime_detection": {...}
  }
}
```

### signal_thresholds.json结构

```json
{
  "version": "v7.2.19_data_driven",
  "description": "信号生成阈值配置",

  "基础分析阈值": {
    "mature_coin": {
      "prime_strength_min": 42,
      "confidence_min": 15,
      "edge_min": 0.12,
      "prime_prob_min": 0.50
    },
    "newcoin_phaseB": {...},
    "newcoin_phaseA": {...},
    "newcoin_ultra": {...}
  },

  "新币阶段识别": {
    "ultra_new_hours": 24,
    "phase_A_hours": 168,
    "phase_B_hours": 400
  },

  "阶段过渡参数": {
    "ultra_to_phaseA": {...},
    "phaseA_to_phaseB": {...},
    "phaseB_to_mature": {...}
  },

  "新币质量补偿": {
    "ultra_new_compensate_from": 0.85,
    "ultra_new_compensate_to": 0.90
  },

  "数据质量阈值": {
    "min_bars_1h": 200,
    "data_qual_min": 0.85
  },

  "新币种平滑处理": {
    "enable_newcoin_smooth": true,
    "min_klines_for_stable": 96,
    "newcoin_confidence_penalty": 0.8
  },

  "统计校准参数": {
    "decay_period_days": 30,
    "include_mtm_unrealized": true,
    "mtm_weight_factor": 0.5
  },

  "VIF多重共线性监控": {
    "enable_vif_monitoring": true,
    "vif_threshold": 10.0,
    "vif_warning_threshold": 5.0
  }
}
```

---

## 最佳实践

### ✅ 推荐做法

1. **修改配置文件，不改代码**
   - 所有参数调整都在JSON文件中进行
   - 保持代码稳定，配置灵活

2. **提交前验证JSON格式**
   ```bash
   python3 -c "import json; json.load(open('config/factors_unified.json'))"
   ```

3. **记录修改原因**
   - 在JSON中使用`_comment`字段
   - 在Git commit message中详细说明

4. **增量修改，小步迭代**
   - 一次只修改1-2个参数
   - 观察效果后再继续调整

5. **备份配置文件**
   ```bash
   cp config/factors_unified.json config/factors_unified.json.backup
   ```

6. **使用版本控制**
   - 配置文件纳入Git管理
   - 重大修改创建新分支

### ❌ 避免做法

1. ❌ 直接修改代码中的硬编码值
2. ❌ 修改配置文件后不验证JSON格式
3. ❌ 不记录修改原因和预期效果
4. ❌ 一次修改大量参数
5. ❌ 修改后不测试直接上线
6. ❌ 不备份原始配置文件

---

## 配置热更新

**当前版本不支持热更新**，修改配置文件后需要重启系统。

未来计划（v7.3+）：
- [ ] 添加配置文件监听
- [ ] 支持SIGHUP信号重新加载
- [ ] 提供`reload_config()`API
- [ ] 配置修改webhook通知

---

## 故障排查

### 问题1: 配置文件修改后不生效

**症状**: 修改了`factors_unified.json`，但运行时仍使用旧值

**原因**: 配置在系统启动时加载，运行中不会重新读取

**解决方案**:
```bash
# 重启系统
./setup.sh

# 或重启特定脚本
pkill -f realtime_signal_scanner
python3 scripts/realtime_signal_scanner.py
```

### 问题2: JSON格式错误

**症状**: 系统启动失败，提示`json.decoder.JSONDecodeError`

**原因**: JSON文件格式错误（缺少逗号、括号不匹配等）

**解决方案**:
```bash
# 验证JSON格式
python3 -c "import json; json.load(open('config/factors_unified.json'))"

# 使用jq美化输出（便于找到错误）
jq . config/factors_unified.json

# 如果无法修复，恢复备份
cp config/factors_unified.json.backup config/factors_unified.json
```

### 问题3: 配置加载失败，使用fallback值

**症状**: 日志中出现 `⚠️ T因子配置加载失败，使用默认值`

**原因**:
- 配置文件路径错误
- 配置文件损坏
- 配置文件中缺少某个因子的配置

**解决方案**:
```bash
# 检查配置文件是否存在
ls -la config/factors_unified.json

# 检查配置文件格式
python3 scripts/validate_config.py

# 检查因子配置是否完整
python3 -c "
import json
config = json.load(open('config/factors_unified.json'))
print('已配置的因子:', list(config['factors'].keys()))
"
```

---

## 总结

### 🎯 核心要点

1. **配置文件是唯一真实来源**
   - 修改参数 → 编辑JSON文件
   - 不要修改代码中的fallback值（除非同步修改）

2. **两个配置文件，职责分明**
   - `factors_unified.json`: 因子计算参数
   - `signal_thresholds.json`: 信号生成阈值

3. **硬编码fallback仅用于应急**
   - 系统已配置化，但保留fallback作为保险
   - Fallback值应与配置文件保持一致

4. **修改后需要重启**
   - 当前版本不支持热更新
   - 修改配置文件后必须重启系统

5. **验证-测试-提交**
   - 修改前备份
   - 修改后验证JSON格式
   - 测试无误后提交Git

### 📚 相关文档

- `standards/SYSTEM_ENHANCEMENT_STANDARD.md` - 系统增强规范
- `docs/FACTOR_SYSTEM_COMPLETE_DESIGN.md` - 因子系统设计文档
- `docs/V7.2.44_P0_P1_FIXES_SUMMARY.md` - P0/P1修复总结

---

**文档作者**: Claude
**最后更新**: 2025-11-14
**版本**: v1.0
