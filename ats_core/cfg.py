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