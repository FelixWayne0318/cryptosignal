import json, os

_ROOT = os.path.dirname(os.path.dirname(__file__))

def _load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

class Cfg:
    def __init__(self):
        self.params = _load_json(os.path.join(_ROOT, "config", "params.json"), {})
        self.blacklist = set(_load_json(os.path.join(_ROOT, "config", "blacklist.json"), {}).get("symbols", []))
        self.root = os.path.dirname(_ROOT)

    def get(self, *keys, default=None):
        d = self.params
        for k in keys:
            if not isinstance(d, dict) or k not in d: return default
            d = d[k]
        return d

CFG = Cfg()