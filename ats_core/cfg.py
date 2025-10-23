# coding: utf-8
from __future__ import annotations

import os
import json
import copy
import pathlib
from typing import Any, Dict


# ---- 内建默认参数（防止线上配置缺键时直接崩）----
DEFAULTS: Dict[str, Any] = {
    "trend": {
        "ema_order_min_bars": 6,
        "slope_atr_min_long": 0.06,
        "slope_atr_min_short": 0.04,
        "slope_lookback": 12,
        "atr_period": 14,
    },

    "overlay": {
        "oi_1h_pct_big": 0.003,
        "oi_1h_pct_small": 0.01,
        "hot_decay_hours": 2,

        "z_volume_1h_threshold": 3,
        "min_hour_quote_usdt": 5_000_000,

        "z24_and_24h_quote": {"z24": 2, "quote": 20_000_000},

        "triple_sync": {
            "dP1h_abs_pct": 0.10,
            "v5_over_v20": 2.5,
            "cvd_mix_abs_per_h": 0.12,
        },
    },

    "universe": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "TRXUSDT", "AVAXUSDT", "LINKUSDT",
        "MATICUSDT", "DOTUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT",
        "FILUSDT", "NEARUSDT", "APTUSDT", "OPUSDT", "ARBUSDT",
        "SUIUSDT", "SEIUSDT", "INJUSDT", "RUNEUSDT", "IMXUSDT",
        "TONUSDT", "ICPUSDT", "AAVEUSDT", "UNIUSDT", "ETCUSDT",
        "COAIUSDT", "PAXGUSDT", "XPLUSDT", "CLOUSDT",
    ],
}


def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    """递归深合并，把 over 覆盖到 base 上。"""
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


class _Cfg:
    def __init__(self):
        self.params: Dict[str, Any] = {}
        self.reload()

    def _repo_root(self) -> pathlib.Path:
        # ats_core/cfg.py -> ats_core -> 仓库根
        return pathlib.Path(__file__).resolve().parents[1]

    def _load_json(self, path: pathlib.Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            txt = path.read_text(encoding="utf-8")
            data = json.loads(txt)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def reload(self):
        # 允许外部覆盖路径：
        #  - ATS_CONFIG_PATH 指向某个具体文件
        #  - ATS_ROOT 指向仓库根；默认用当前文件回溯
        root = pathlib.Path(os.environ.get("ATS_ROOT") or self._repo_root())
        cfg_path_env = os.environ.get("ATS_CONFIG_PATH")
        cfg_path = pathlib.Path(cfg_path_env) if cfg_path_env else (root / "config" / "params.json")

        user_cfg = self._load_json(cfg_path)
        # 用默认值补齐，避免 KeyError
        self.params = _deep_merge(copy.deepcopy(DEFAULTS), user_cfg)

    def get(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


CFG = _Cfg()