# ats_core/cfg.py
# coding: utf-8
"""
配置管理器 - 旧系统 (v6.6架构，向后兼容)

⚠️ 职责范围（临时）:
- 仅负责 params.json 读取
- 仅负责因子权重校验 (6+4架构)
- 向后兼容性支持

🎯 未来计划（v8.0）:
- 本模块将被废弃
- 所有配置统一迁移到 RuntimeConfig
- 权重校验迁移到 RuntimeConfig

📌 何时使用:
- ❌ 新代码不应使用此模块
- ✅ 仅 analyze_symbol.py 历史兼容（旧系统v6.6）
- ✅ 新代码请使用 ats_core.config.runtime_config.RuntimeConfig
- ✅ v7.4.0四步系统使用RuntimeConfig

🆕 v7.4.0更新:
- 支持Dual Run模式（v6.6 + v7.4四步系统）
- 使用统一路径解析器 (path_resolver.py)
- 支持环境变量 CRYPTOSIGNAL_CONFIG_ROOT

参考:
- docs/health_checks/system_architecture_health_check_2025-11-15.md#P0-1
- /tmp/revised_fix_plan.md#Phase2-3
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

# v7.3.2: 使用统一路径解析器
from .config.path_resolver import get_params_file

def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _validate_weights(params: Dict[str, Any]) -> None:
    """
    验证权重配置（v6.6: 6+4维架构）

    v6.6架构：
    - A层核心因子(6): T, M, C, V, O, B - 权重总和=100%
    - B层调制器(4): L, S, F, I - 权重必须=0%（不参与评分）
    - 废弃因子: E（环境）, Q（清算密度） - 可选，建议权重=0%

    Raises:
        ValueError: 如果权重配置无效
    """
    weights = params.get("weights")
    if not weights:
        raise ValueError(
            "配置错误: 缺少'weights'配置项\n"
            "请检查 config/params.json 是否包含 'weights' 字段"
        )

    if not isinstance(weights, dict):
        raise ValueError(
            f"配置错误: 'weights'必须是字典类型，当前类型: {type(weights).__name__}"
        )

    # v6.6架构定义
    core_factors = ['T', 'M', 'C', 'V', 'O', 'B']  # A层：6个核心因子
    modulators = ['L', 'S', 'F', 'I']              # B层：4个调制器
    deprecated = ['E']                              # 可选：废弃因子（向后兼容）

    # 检查必需的核心因子
    missing_core = [f for f in core_factors if f not in weights]
    if missing_core:
        raise ValueError(
            f"配置错误: 缺少必需的核心因子权重\n"
            f"缺失因子: {', '.join(missing_core)}\n"
            f"v6.6架构要求:\n"
            f"  A层核心因子(6): T/M/C/V/O/B - 权重总和=100%\n"
            f"  B层调制器(4): L/S/F/I - 权重必须=0%"
        )

    # 检查必需的调制器
    missing_mod = [m for m in modulators if m not in weights]
    if missing_mod:
        raise ValueError(
            f"配置错误: 缺少必需的调制器权重\n"
            f"缺失调制器: {', '.join(missing_mod)}\n"
            f"v6.6架构要求:\n"
            f"  A层核心因子(6): T/M/C/V/O/B - 权重总和=100%\n"
            f"  B层调制器(4): L/S/F/I - 权重必须=0%"
        )

    # 计算核心因子权重总和
    try:
        core_weights = {k: weights[k] for k in core_factors}
        core_total = sum(core_weights.values())
    except (TypeError, AttributeError) as e:
        raise ValueError(
            f"配置错误: 权重值必须是数字类型\n"
            f"错误详情: {e}\n"
            f"提示: 权重值应为数字（如 24.0），不能是字符串"
        )

    # v6.6要求：核心因子权重总和=100%
    if abs(core_total - 100.0) > 0.01:
        raise ValueError(
            f"配置错误: 核心因子权重总和必须=100.0% (v6.6系统)\n"
            f"当前总和: {core_total}%\n"
            f"核心因子权重: {core_weights}\n\n"
            f"修复方法: 调整 config/params.json 中的核心因子权重，确保总和=100.0\n"
            f"v6.6标准配置: T=24%, M=17%, C=24%, V=12%, O=17%, B=6%"
        )

    # v6.6要求：调制器权重必须=0%
    modulator_weights = {k: weights[k] for k in modulators}
    for mod, wt in modulator_weights.items():
        if abs(wt) > 0.01:
            raise ValueError(
                f"配置错误: 调制器权重必须=0% (v6.6系统)\n"
                f"调制器 {mod} 权重={wt}% (应为0%)\n"
                f"v6.6架构: 调制器不参与评分，仅调节执行参数\n"
                f"调制器权重: {modulator_weights}\n\n"
                f"修复方法: 设置 L/S/F/I 权重为 0.0"
            )

class _Cfg:
    def __init__(self) -> None:
        self._params: Optional[Dict[str, Any]] = None
        # v7.3.2: 使用统一路径解析器
        # 支持 ATS_PARAMS_FILE 环境变量（向后兼容）
        # 否则使用 path_resolver 自动解析（支持 CRYPTOSIGNAL_CONFIG_ROOT）
        import os
        self._params_file = os.getenv(
            "ATS_PARAMS_FILE",
            str(get_params_file()),  # 使用统一路径解析器
        )

    def _ensure_defaults(self, p: Dict[str, Any]) -> Dict[str, Any]:
        # 基本段落
        p.setdefault("trend", {})
        p.setdefault("overlay", {})
        p.setdefault("universe", [])

        # 关键：structure 缺失时给一个温和的默认，防止 analyze_symbol 里 KeyError
        p.setdefault("structure", {
            "enabled": True,          # 打开结构评分（score_structure 内部若找不到细节，再用它自己的默认）
            "fallback_score": 50      # 万一内部无法计算，可当作中性分
        })

        return p

    def reload(self) -> None:
        raw = _read_json(self._params_file)
        if not isinstance(raw, dict):
            raw = {}

        # 验证配置（v6.6: 核心因子权重总和=100%, 调制器权重=0%）
        try:
            _validate_weights(raw)
        except ValueError as e:
            print(f"\n❌ {e}\n")
            raise

        self._params = self._ensure_defaults(raw)

    @property
    def params(self) -> Dict[str, Any]:
        if self._params is None:
            self.reload()
        return self._params or {}

    # 兼容两种 default 传参方式：
    #   CFG.get("overlay", {})             # 位置参数当 default
    #   CFG.get("overlay", default={})     # 关键字 default
    #   CFG.get("overlay", {}, default={}) # 旧代码同时传也能容忍
    def get(self, key: str, *pos, default: Any = None) -> Any:
        if pos:
            # 只取第一个位置参数作为 default
            if default is None:
                default = pos[0]
        return (self.params or {}).get(key, default)

CFG = _Cfg()