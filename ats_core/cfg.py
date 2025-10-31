# ats_core/cfg.py
# coding: utf-8
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _validate_weights(params: Dict[str, Any]) -> None:
    """
    验证权重配置（v6.0: 100%系统）

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

    # 计算权重总和
    try:
        total = sum(weights.values())
    except (TypeError, AttributeError) as e:
        raise ValueError(
            f"配置错误: 权重值必须是数字类型\n"
            f"错误详情: {e}"
        )

    # v6.0系统要求权重总和=100%
    if abs(total - 100.0) > 0.01:
        raise ValueError(
            f"配置错误: 权重总和必须=100.0% (v6.0系统)\n"
            f"当前总和: {total}%\n"
            f"权重明细: {weights}\n\n"
            f"修复方法: 调整 config/params.json 中的权重值，确保总和=100.0\n"
            f"验证命令: python3 -c \"import json; w=json.load(open('config/params.json'))['weights']; print(f'总和={{sum(w.values())}}')\""
        )

    # 检查必需的因子（v6.0: 10+1维）
    required_factors = ['T', 'M', 'C', 'S', 'V', 'O', 'L', 'B', 'Q', 'I', 'F']
    missing_factors = [f for f in required_factors if f not in weights]
    if missing_factors:
        raise ValueError(
            f"配置错误: 缺少必需的因子权重\n"
            f"缺失因子: {', '.join(missing_factors)}\n"
            f"v6.0系统要求: T/M/C/S/V/O/L/B/Q/I + F (10+1维)"
        )

class _Cfg:
    def __init__(self) -> None:
        self._params: Optional[Dict[str, Any]] = None
        self._params_file = os.getenv(
            "ATS_PARAMS_FILE",
            os.path.join(_REPO_ROOT, "config", "params.json"),
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

        # 验证配置（v6.0: 权重总和必须=100%）
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