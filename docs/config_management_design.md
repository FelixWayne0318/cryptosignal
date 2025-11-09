# 统一配置管理系统设计方案

## 目录
1. [问题分析](#问题分析)
2. [设计方案](#设计方案)
3. [实施步骤](#实施步骤)
4. [代码示例](#代码示例)
5. [测试方案](#测试方案)
6. [风险评估](#风险评估)

---

## 问题分析

### 当前硬编码参数清单

#### 1. StandardizationChain参数（模块级硬编码）
```python
# 6个因子，参数不一致：
T:  alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5
M:  alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5
C+: alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5
S:  alpha=0.15, tau=2.0, z0=2.5, zmax=6.0, lam=1.5 (已禁用)
V+: alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5
O+: alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5 (z0重复定义bug)
```

#### 2. 因子算法参数（default_params字典）
```python
# 6个因子有default_params，每个20-30行代码
M:  ema_fast, ema_slow, slope_lookback, slope_scale, accel_scale...
C+: lookback_hours, cvd_scale, crowding_p95_penalty...
V+: vlevel_scale, vroc_scale, vlevel_weight, price_lookback...
O+: oi24_scale, align_scale, oi_weight, min_oi_samples...
T:  直接从cfg读取（ema_order_min_bars, slope_lookback...）
S:  直接从params读取（theta参数字典）
```

#### 3. 数据质量检查阈值（硬编码）
```python
M:  len(c) < 20
C+: len(cvd_series) < 7 or len(c) < 7
T:  len(C) < 30
V+: len(vol) < 25
O+: par["min_oi_samples"] = 30
S:  无明确检查
```

#### 4. 配置文件过时（factors_unified.json）
```json
// M因子配置过时
"M": {
  "params": {
    "lookback_periods": 20,  // ❌ 代码未使用
    "acceleration_window": 10  // ❌ 代码未使用
  }
}
// 实际代码使用: ema_fast=3, ema_slow=5, slope_lookback=6...
```

---

## 设计方案

### 1. 配置文件结构设计（factors_unified.json v3.0）

```json
{
  "version": "3.0.0",
  "updated_at": "2025-11-09",
  
  // ========== 新增：全局配置 ==========
  "global": {
    "standardization": {
      "enabled": true,
      "default_params": {
        "alpha": 0.25,
        "tau": 5.0,
        "z0": 3.0,
        "zmax": 6.0,
        "lam": 1.5
      },
      "factor_overrides": {
        "T": {"alpha": 0.15, "tau": 3.0, "z0": 2.5},
        "S": {"alpha": 0.15, "tau": 2.0, "z0": 2.5, "enabled": false}
      }
    },
    
    "data_quality": {
      "min_data_points": {
        "default": 20,
        "T": 30,
        "V+": 25,
        "O+": 30,
        "C+": 7
      },
      "historical_lookback": {
        "default": 50,
        "C+": 30,
        "O+": 50
      }
    },
    
    "degradation": {
      "fallback_strategy": "zero_score",
      "allow_partial_data": false,
      "log_degradation_events": true
    }
  },
  
  // ========== 因子配置（更新） ==========
  "factors": {
    "M": {
      "name": "Momentum",
      "layer": "price_action",
      "weight": 15,
      "enabled": true,
      "description": "价格动量（加速度）",
      
      // ✅ 更新为实际使用的参数
      "params": {
        // P2.2短窗口EMA配置
        "ema_fast": 3,
        "ema_slow": 5,
        "slope_lookback": 6,
        "slope_scale": 2.0,
        "accel_scale": 2.0,
        "slope_weight": 0.6,
        "accel_weight": 0.4,
        "atr_period": 14,
        
        // 新增：归一化配置
        "normalization_method": "relative_historical",
        "min_historical_samples": 30
      }
    },
    
    "C+": {
      "name": "Enhanced CVD",
      "params": {
        "lookback_hours": 6,
        "cvd_scale": 0.15,
        "crowding_p95_penalty": 10,
        "normalization_method": "relative_historical",
        "min_historical_samples": 30,
        "r2_threshold": 0.7
      }
    },
    
    "V+": {
      "params": {
        "vlevel_scale": 0.9,
        "vroc_scale": 0.9,
        "vlevel_weight": 0.6,
        "vroc_weight": 0.4,
        "price_lookback": 5,
        "adaptive_threshold_mode": "hybrid"
      }
    },
    
    "O+": {
      "params": {
        "oi24_scale": 2.0,
        "align_scale": 4.0,
        "oi_weight": 0.7,
        "align_weight": 0.3,
        "crowding_p95_penalty": 10,
        "min_oi_samples": 30,
        "adaptive_threshold_mode": "hybrid",
        "use_notional_oi": true,
        "contract_multiplier": 1.0
      }
    },
    
    "T": {
      "params": {
        "ema_order_min_bars": 6,
        "slope_lookback": 12,
        "atr_period": 14,
        "slope_scale": 0.08,
        "ema_bonus": 12.5,
        "r2_weight": 0.15
      }
    },
    
    "S": {
      "params": {
        "theta": {
          "big": 0.40,
          "small": 0.35,
          "overlay_add": 0.05,
          "new_phaseA_add": 0.08,
          "strong_regime_sub": 0.10
        }
      }
    }
    
    // ... 其他因子 L, B, Q, I, F
  }
}
```

### 2. 配置验证器设计

创建新文件：`ats_core/config/config_validator.py`

```python
"""
配置文件验证器
验证factors_unified.json的完整性和正确性
"""
from typing import Dict, List, Any, Tuple
import json
from pathlib import Path

class ConfigValidator:
    """配置验证器"""
    
    # 因子参数定义（类型、必需性、范围）
    FACTOR_PARAM_SPECS = {
        "M": {
            "ema_fast": {"type": int, "required": True, "range": (1, 50)},
            "ema_slow": {"type": int, "required": True, "range": (1, 100)},
            "slope_lookback": {"type": int, "required": True, "range": (1, 50)},
            "slope_scale": {"type": float, "required": True, "range": (0.1, 10.0)},
            "accel_scale": {"type": float, "required": True, "range": (0.1, 10.0)},
            "slope_weight": {"type": float, "required": True, "range": (0.0, 1.0)},
            "accel_weight": {"type": float, "required": True, "range": (0.0, 1.0)},
            "atr_period": {"type": int, "required": True, "range": (5, 30)},
        },
        "C+": {
            "lookback_hours": {"type": int, "required": True, "range": (1, 24)},
            "cvd_scale": {"type": float, "required": True, "range": (0.01, 1.0)},
            "crowding_p95_penalty": {"type": int, "required": True, "range": (0, 50)},
        },
        # ... 其他因子
    }
    
    # StandardizationChain参数定义
    STANDARDIZATION_SPECS = {
        "alpha": {"type": float, "required": True, "range": (0.01, 0.5)},
        "tau": {"type": float, "required": True, "range": (1.0, 10.0)},
        "z0": {"type": float, "required": True, "range": (1.0, 5.0)},
        "zmax": {"type": float, "required": True, "range": (3.0, 10.0)},
        "lam": {"type": float, "required": True, "range": (1.0, 3.0)},
    }
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "factors_unified.json"
        
        self.config_path = Path(config_path)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> Tuple[bool, Dict[str, Any]]:
        """
        验证配置文件
        
        Returns:
            (is_valid, report)
        """
        self.errors = []
        self.warnings = []
        
        # 1. 文件存在性
        if not self.config_path.exists():
            self.errors.append(f"配置文件不存在: {self.config_path}")
            return False, self._generate_report()
        
        # 2. JSON格式
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON格式错误: {e}")
            return False, self._generate_report()
        
        # 3. 版本检查
        if "version" not in config:
            self.errors.append("缺少version字段")
        
        # 4. 全局配置验证
        self._validate_global_config(config.get("global", {}))
        
        # 5. 因子配置验证
        self._validate_factors(config.get("factors", {}))
        
        # 6. 一致性检查
        self._validate_consistency(config)
        
        is_valid = len(self.errors) == 0
        return is_valid, self._generate_report()
    
    def _validate_global_config(self, global_config: Dict):
        """验证全局配置"""
        # 验证standardization配置
        std_config = global_config.get("standardization", {})
        
        if "default_params" in std_config:
            self._validate_params(
                std_config["default_params"],
                self.STANDARDIZATION_SPECS,
                context="global.standardization.default_params"
            )
        
        # 验证data_quality配置
        dq_config = global_config.get("data_quality", {})
        
        if "min_data_points" in dq_config:
            min_pts = dq_config["min_data_points"]
            if not isinstance(min_pts, dict):
                self.errors.append("global.data_quality.min_data_points必须是字典")
            else:
                if "default" not in min_pts:
                    self.warnings.append("建议设置default最小数据点数")
    
    def _validate_factors(self, factors: Dict):
        """验证因子配置"""
        expected_factors = ["T", "M", "C+", "S", "V+", "O+", "L", "B", "Q", "I", "F"]
        
        for factor_name in expected_factors:
            if factor_name not in factors:
                self.warnings.append(f"缺少因子配置: {factor_name}")
                continue
            
            factor = factors[factor_name]
            
            # 必需字段检查
            for field in ["name", "layer", "weight", "enabled", "params"]:
                if field not in factor:
                    self.errors.append(f"{factor_name}缺少{field}字段")
            
            # 参数验证
            if factor_name in self.FACTOR_PARAM_SPECS:
                self._validate_params(
                    factor.get("params", {}),
                    self.FACTOR_PARAM_SPECS[factor_name],
                    context=f"factors.{factor_name}.params"
                )
    
    def _validate_params(self, params: Dict, specs: Dict, context: str):
        """验证参数"""
        for param_name, spec in specs.items():
            if spec.get("required", False) and param_name not in params:
                self.errors.append(f"{context}.{param_name} 缺失（必需参数）")
                continue
            
            if param_name not in params:
                continue
            
            value = params[param_name]
            expected_type = spec["type"]
            
            # 类型检查
            if not isinstance(value, expected_type):
                self.errors.append(
                    f"{context}.{param_name} 类型错误: "
                    f"期望{expected_type.__name__}，实际{type(value).__name__}"
                )
                continue
            
            # 范围检查
            if "range" in spec:
                min_val, max_val = spec["range"]
                if not (min_val <= value <= max_val):
                    self.errors.append(
                        f"{context}.{param_name} 超出范围: "
                        f"{value} 不在 [{min_val}, {max_val}]"
                    )
    
    def _validate_consistency(self, config: Dict):
        """验证一致性"""
        # 检查权重一致性
        factors = config.get("factors", {})
        
        # M因子权重检查
        if "M" in factors:
            m_params = factors["M"].get("params", {})
            slope_weight = m_params.get("slope_weight", 0)
            accel_weight = m_params.get("accel_weight", 0)
            
            if abs(slope_weight + accel_weight - 1.0) > 0.01:
                self.warnings.append(
                    f"M因子权重之和不为1: "
                    f"slope_weight({slope_weight}) + accel_weight({accel_weight}) = "
                    f"{slope_weight + accel_weight}"
                )
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        return {
            "config_path": str(self.config_path),
            "is_valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }
    
    def print_report(self, report: Dict[str, Any]):
        """打印验证报告"""
        print("=" * 60)
        print("配置文件验证报告")
        print("=" * 60)
        print(f"文件路径: {report['config_path']}")
        print(f"验证结果: {'✅ 通过' if report['is_valid'] else '❌ 失败'}")
        print(f"错误数: {report['error_count']}")
        print(f"警告数: {report['warning_count']}")
        
        if report['errors']:
            print("\n❌ 错误:")
            for i, error in enumerate(report['errors'], 1):
                print(f"  {i}. {error}")
        
        if report['warnings']:
            print("\n⚠️  警告:")
            for i, warning in enumerate(report['warnings'], 1):
                print(f"  {i}. {warning}")
        
        print("=" * 60)
```

### 3. 扩展factor_config.py

在`ats_core/config/factor_config.py`中添加新方法：

```python
class FactorConfig:
    # ... 现有代码 ...
    
    def get_standardization_params(self, factor_name: str) -> Dict[str, float]:
        """
        获取因子的StandardizationChain参数
        
        优先级:
        1. global.standardization.factor_overrides[factor_name]
        2. global.standardization.default_params
        
        Args:
            factor_name: 因子名称
        
        Returns:
            StandardizationChain参数字典
        """
        # 获取全局配置
        global_config = self.config.get("global", {})
        std_config = global_config.get("standardization", {})
        
        # 默认参数
        default_params = std_config.get("default_params", {
            "alpha": 0.25,
            "tau": 5.0,
            "z0": 3.0,
            "zmax": 6.0,
            "lam": 1.5
        })
        
        # 因子特定覆盖
        overrides = std_config.get("factor_overrides", {})
        factor_override = overrides.get(factor_name, {})
        
        # 合并参数
        params = dict(default_params)
        params.update(factor_override)
        
        # 检查是否禁用
        params["enabled"] = std_config.get("enabled", True) and \
                           factor_override.get("enabled", True)
        
        return params
    
    def get_data_quality_threshold(
        self,
        factor_name: str,
        threshold_type: str = "min_data_points"
    ) -> int:
        """
        获取数据质量阈值
        
        Args:
            factor_name: 因子名称
            threshold_type: 阈值类型（min_data_points, historical_lookback）
        
        Returns:
            阈值值
        """
        global_config = self.config.get("global", {})
        dq_config = global_config.get("data_quality", {})
        thresholds = dq_config.get(threshold_type, {})
        
        # 优先使用因子特定阈值，否则使用default
        return thresholds.get(factor_name, thresholds.get("default", 20))
    
    def get_degradation_strategy(self) -> str:
        """
        获取降级策略
        
        Returns:
            降级策略名称（zero_score, last_valid, cvd_fallback等）
        """
        global_config = self.config.get("global", {})
        degradation = global_config.get("degradation", {})
        return degradation.get("fallback_strategy", "zero_score")
    
    def should_log_degradation(self) -> bool:
        """是否记录降级事件"""
        global_config = self.config.get("global", {})
        degradation = global_config.get("degradation", {})
        return degradation.get("log_degradation_events", True)
    
    def validate_config(self) -> Tuple[bool, Dict[str, Any]]:
        """
        验证配置文件
        
        Returns:
            (is_valid, report)
        """
        from .config_validator import ConfigValidator
        validator = ConfigValidator(self.config_path)
        return validator.validate()
    
    def get_factor_config_full(self, factor_name: str) -> Dict[str, Any]:
        """
        获取因子的完整配置（包括params + standardization + data_quality）
        
        Args:
            factor_name: 因子名称
        
        Returns:
            完整配置字典
        """
        if factor_name not in self.factors:
            raise ValueError(f"Unknown factor: {factor_name}")
        
        factor_config = self.factors[factor_name].copy()
        
        # 添加standardization参数
        factor_config["standardization"] = self.get_standardization_params(factor_name)
        
        # 添加data_quality阈值
        factor_config["data_quality"] = {
            "min_data_points": self.get_data_quality_threshold(
                factor_name, "min_data_points"
            ),
            "historical_lookback": self.get_data_quality_threshold(
                factor_name, "historical_lookback"
            ),
        }
        
        return factor_config
```

---

## 实施步骤

### P0优先级（必须立即完成）

#### Step 1: 更新配置文件（1小时）
```bash
# 1. 备份现有配置
cp config/factors_unified.json config/factors_unified.json.v2.0.backup

# 2. 更新配置文件（添加global section）
# 手动编辑 config/factors_unified.json
# 或使用脚本自动生成
```

**Before:**
```json
{
  "version": "2.0.0",
  "factors": {
    "M": {
      "params": {
        "lookback_periods": 20,  // ❌ 过时
        "acceleration_window": 10
      }
    }
  }
}
```

**After:**
```json
{
  "version": "3.0.0",
  "global": {
    "standardization": {
      "enabled": true,
      "default_params": {...},
      "factor_overrides": {...}
    },
    "data_quality": {...},
    "degradation": {...}
  },
  "factors": {
    "M": {
      "params": {
        "ema_fast": 3,  // ✅ 与代码一致
        "ema_slow": 5,
        "slope_lookback": 6,
        ...
      }
    }
  }
}
```

#### Step 2: 扩展FactorConfig（2小时）
```bash
# 在 ats_core/config/factor_config.py 添加新方法
# - get_standardization_params()
# - get_data_quality_threshold()
# - get_degradation_strategy()
# - get_factor_config_full()
```

#### Step 3: 创建配置验证器（2小时）
```bash
# 创建 ats_core/config/config_validator.py
# 实现 ConfigValidator 类
```

#### Step 4: 重构第一个因子（M因子）（2小时）
```bash
# 重构 ats_core/features/momentum.py
# 使用配置系统替代硬编码
```

**Before:**
```python
# ats_core/features/momentum.py

# 硬编码 StandardizationChain
_momentum_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5)

# 硬编码 default_params
default_params = {
    "ema_fast": 3,
    "ema_slow": 5,
    "slope_lookback": 6,
    ...
}

# 硬编码数据检查
if len(c) < 20:
    return 0, {...}
```

**After:**
```python
# ats_core/features/momentum.py

from ats_core.config.factor_config import get_factor_config
from ats_core.scoring.scoring_utils import StandardizationChain

# 全局配置实例（延迟初始化）
_factor_config = None
_momentum_chain = None

def _get_momentum_chain():
    """获取StandardizationChain实例（延迟初始化，使用配置）"""
    global _factor_config, _momentum_chain
    
    if _factor_config is None:
        _factor_config = get_factor_config()
    
    if _momentum_chain is None:
        std_params = _factor_config.get_standardization_params("M")
        
        if std_params.get("enabled", True):
            _momentum_chain = StandardizationChain(
                alpha=std_params["alpha"],
                tau=std_params["tau"],
                z0=std_params["z0"],
                zmax=std_params["zmax"],
                lam=std_params["lam"]
            )
        else:
            _momentum_chain = None  # 禁用标准化
    
    return _momentum_chain

def score_momentum(
    h: List[float],
    l: List[float],
    c: List[float],
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """M（动量）维度评分"""
    
    # 获取配置
    config = get_factor_config()
    
    # 参数优先级: 1. 传入params, 2. 配置文件
    if params is None:
        params = {}
    
    # 从配置文件获取默认参数
    default_params = config.get_factor_params("M")
    
    # 合并参数（传入的params优先级更高，用于向后兼容）
    p = dict(default_params)
    p.update(params)
    
    # 数据质量检查（使用配置）
    min_data_points = config.get_data_quality_threshold("M", "min_data_points")
    if len(c) < min_data_points:
        # 降级策略
        strategy = config.get_degradation_strategy()
        if config.should_log_degradation():
            import logging
            logging.warning(f"M因子数据不足: len(c)={len(c)} < {min_data_points}")
        
        if strategy == "zero_score":
            return 0, {"degraded": True, "reason": "insufficient_data"}
    
    # ... 原有计算逻辑 ...
    
    # 应用StandardizationChain（使用配置）
    chain = _get_momentum_chain()
    if chain is not None:
        M_pub, diagnostics = chain.standardize(M_raw)
        M = int(round(M_pub))
    else:
        # 禁用标准化：直接使用原始值
        M = int(round(max(-100, min(100, M_raw))))
    
    return M, meta
```

### P1优先级（一周内完成）

#### Step 5-10: 渐进式重构其他因子
- Step 5: C+因子（2小时）
- Step 6: V+因子（2小时）
- Step 7: O+因子（2小时）
- Step 8: T因子（2小时）
- Step 9: S因子（1小时）
- Step 10: L/B/Q/I/F因子（5小时）

#### Step 11: 集成启动流程（1小时）
```python
# 在主程序启动时验证配置
# main.py 或 __init__.py

from ats_core.config.factor_config import get_factor_config

def startup_validation():
    """启动时验证配置"""
    config = get_factor_config()
    
    is_valid, report = config.validate_config()
    
    if not is_valid:
        print("❌ 配置文件验证失败:")
        config.print_report(report)
        raise RuntimeError("配置文件无效，请修复后重新启动")
    
    if report["warning_count"] > 0:
        print("⚠️  配置文件有警告:")
        config.print_report(report)
    
    print("✅ 配置文件验证通过")
    print(config.summary())
```

### P2优先级（可选增强）

#### Step 12: 配置热重载（2小时）
```python
# 添加配置文件监听和热重载
import watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("factors_unified.json"):
            print("🔄 检测到配置文件变化，重新加载...")
            reload_config()
```

#### Step 13: 配置继承和环境覆盖（2小时）
```python
# 支持多环境配置
# factors_unified.json (默认)
# factors_unified.dev.json (开发环境覆盖)
# factors_unified.prod.json (生产环境覆盖)

class FactorConfig:
    def __init__(self, config_path=None, env=None):
        # 加载基础配置
        base_config = self._load_json("factors_unified.json")
        
        # 加载环境覆盖配置
        if env:
            env_config = self._load_json(f"factors_unified.{env}.json")
            base_config = self._merge_configs(base_config, env_config)
        
        self.config = base_config
```

---

## 测试方案

### 单元测试（test_config_management.py）
```python
import pytest
from ats_core.config.factor_config import get_factor_config
from ats_core.config.config_validator import ConfigValidator

def test_config_loading():
    """测试配置加载"""
    config = get_factor_config()
    assert config.version == "3.0.0"

def test_get_factor_params():
    """测试获取因子参数"""
    config = get_factor_config()
    
    m_params = config.get_factor_params("M")
    assert "ema_fast" in m_params
    assert m_params["ema_fast"] == 3
    assert m_params["ema_slow"] == 5

def test_get_standardization_params():
    """测试获取标准化参数"""
    config = get_factor_config()
    
    # M因子使用factor_overrides
    m_std = config.get_standardization_params("M")
    assert m_std["alpha"] == 0.25
    assert m_std["tau"] == 5.0
    
    # T因子使用factor_overrides
    t_std = config.get_standardization_params("T")
    assert t_std["alpha"] == 0.15
    assert t_std["tau"] == 3.0
    
    # L因子使用default_params
    l_std = config.get_standardization_params("L")
    assert l_std["alpha"] == 0.25  # default
    assert l_std["tau"] == 5.0  # default

def test_get_data_quality_threshold():
    """测试数据质量阈值"""
    config = get_factor_config()
    
    assert config.get_data_quality_threshold("M", "min_data_points") == 20
    assert config.get_data_quality_threshold("T", "min_data_points") == 30
    assert config.get_data_quality_threshold("V+", "min_data_points") == 25

def test_config_validation():
    """测试配置验证"""
    validator = ConfigValidator()
    is_valid, report = validator.validate()
    
    assert is_valid, f"配置验证失败: {report['errors']}"
    assert report["error_count"] == 0

def test_backwards_compatibility():
    """测试向后兼容性"""
    from ats_core.features.momentum import score_momentum
    
    # 旧用法：传入params参数（应该仍然工作）
    h = [100] * 50
    l = [90] * 50
    c = [95, 96, 97, 98, 99] * 10
    
    custom_params = {"ema_fast": 5, "ema_slow": 10}
    score, meta = score_momentum(h, l, c, params=custom_params)
    
    # 应该使用传入的参数，而非配置文件
    assert isinstance(score, int)
    assert -100 <= score <= 100

def test_degradation_handling():
    """测试降级处理"""
    from ats_core.features.momentum import score_momentum
    
    # 数据不足的情况
    h = [100] * 10
    l = [90] * 10
    c = [95] * 10
    
    score, meta = score_momentum(h, l, c)
    
    # 应该返回降级分数
    assert score == 0
    assert meta.get("degraded", False) == True
```

### 集成测试（test_factor_integration.py）
```python
def test_all_factors_use_config():
    """测试所有因子都正确使用配置"""
    config = get_factor_config()
    
    # 所有因子都应该能够从配置获取参数
    for factor_name in config.get_enabled_factors():
        params = config.get_factor_params(factor_name)
        assert len(params) > 0, f"{factor_name}缺少参数配置"
        
        std_params = config.get_standardization_params(factor_name)
        assert "alpha" in std_params
        assert "tau" in std_params

def test_config_change_propagation():
    """测试配置修改后的传播"""
    config = get_factor_config()
    
    # 修改配置
    original_alpha = config.get_standardization_params("M")["alpha"]
    
    # 重新加载配置（模拟配置文件修改）
    config.reload()
    
    # 验证新配置生效
    new_alpha = config.get_standardization_params("M")["alpha"]
    # （需要实际修改配置文件才能验证）
```

### 性能测试
```python
import time

def test_config_loading_performance():
    """测试配置加载性能"""
    start_time = time.time()
    
    for _ in range(100):
        config = get_factor_config()
        _ = config.get_factor_params("M")
    
    elapsed = time.time() - start_time
    
    # 应该很快（<0.1秒）
    assert elapsed < 0.1, f"配置加载过慢: {elapsed:.3f}s"
```

---

## 风险评估

### 高风险（需要缓解措施）

1. **向后兼容性破坏** (风险等级: HIGH)
   - **风险**: 修改因子函数签名导致现有代码失败
   - **缓解**: 
     - 保持params参数可选
     - 传入的params优先级高于配置文件
     - 添加deprecation警告

2. **配置文件错误导致系统失败** (风险等级: HIGH)
   - **风险**: 配置文件格式错误或参数错误导致启动失败
   - **缓解**:
     - 启动时验证配置文件
     - 提供详细错误信息
     - 保留配置文件备份

3. **StandardizationChain参数变化影响分数** (风险等级: MEDIUM)
   - **风险**: 参数统一后，某些因子的分数分布可能改变
   - **缓解**:
     - 使用factor_overrides保留现有参数
     - 先在测试环境验证分数分布
     - 逐步调整参数而非一次性修改

### 中风险

4. **配置热重载导致状态不一致** (风险等级: MEDIUM)
   - **风险**: 运行时重载配置可能导致StandardizationChain状态重置
   - **缓解**:
     - P2阶段才实现热重载
     - 提供明确的重载语义文档
     - 保留EW状态或提供状态迁移

5. **配置文件体积增大** (风险等级: LOW)
   - **风险**: 添加详细配置后JSON文件过大
   - **缓解**:
     - 合理组织配置层级
     - 使用注释说明参数含义
     - 考虑使用YAML（更易读）

### 低风险

6. **配置验证性能开销** (风险等级: LOW)
   - **风险**: 每次启动都验证配置可能增加启动时间
   - **缓解**:
     - 验证只在启动时执行一次
     - 优化验证逻辑
     - 提供skip_validation选项（生产环境）

---

## 预估工作量

### P0优先级（立即完成）
| 任务 | 预估时间 | 复杂度 |
|------|---------|--------|
| Step 1: 更新配置文件 | 1h | 低 |
| Step 2: 扩展FactorConfig | 2h | 中 |
| Step 3: 创建配置验证器 | 2h | 中 |
| Step 4: 重构M因子 | 2h | 中 |
| **P0小计** | **7h** | **1个工作日** |

### P1优先级（一周内）
| 任务 | 预估时间 | 复杂度 |
|------|---------|--------|
| Step 5-9: 重构C+/V+/O+/T/S | 10h | 中 |
| Step 10: 重构L/B/Q/I/F | 5h | 中 |
| Step 11: 集成启动流程 | 1h | 低 |
| **P1小计** | **16h** | **2个工作日** |

### P2优先级（可选）
| 任务 | 预估时间 | 复杂度 |
|------|---------|--------|
| Step 12: 配置热重载 | 2h | 高 |
| Step 13: 配置继承和环境覆盖 | 2h | 中 |
| **P2小计** | **4h** | **0.5个工作日** |

### 总计
- **最小可行版本（P0）**: 7小时 ≈ 1个工作日
- **完整版本（P0+P1）**: 23小时 ≈ 3个工作日
- **增强版本（P0+P1+P2）**: 27小时 ≈ 3.5个工作日

---

## 附录：配置文件完整示例

见单独文件：`config/factors_unified.v3.0.json`

---

## 总结

### 核心改进
1. ✅ **集中式配置管理**: 所有硬编码参数迁移到配置文件
2. ✅ **配置验证机制**: 启动时自动验证配置完整性
3. ✅ **向后兼容**: params参数仍然有效，优先级更高
4. ✅ **灵活性**: 支持全局默认+因子级覆盖
5. ✅ **可维护性**: 修改参数无需改代码

### 实施路径
1. **第1天（P0）**: 配置文件+验证器+M因子重构
2. **第2-3天（P1）**: 剩余因子重构+集成测试
3. **可选（P2）**: 热重载+环境覆盖

### 成功指标
- ✅ 配置文件验证通过率 = 100%
- ✅ 所有因子使用配置系统
- ✅ 0个硬编码StandardizationChain参数
- ✅ 向后兼容性测试通过率 = 100%

---

**作者**: Claude Code  
**日期**: 2025-11-09  
**版本**: 1.0
