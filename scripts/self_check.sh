sudo -u linuxuser -H bash -lc 'mkdir -p /opt/ats-quant/scripts && cat > /opt/ats-quant/scripts/self_check.sh << "SH"
#!/usr/bin/env bash
# 强化自检：DNS → HTTP → Python/包 → 配置文件 → 总结
set -Eeuo pipefail

# 让脚本无论从哪里执行都能定位到项目根（脚本在 /app/scripts/ 下）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

FAIL=0
WARN=0

say()  { printf "%s\n" "$*"; }
ok()   { printf "✅ %s\n" "$*"; }
warn() { printf "⚠️  %s\n" "$*"; WARN=$((WARN+1)); }
err()  { printf "❌ %s\n" "$*"; FAIL=$((FAIL+1)); }

hr()   { printf -- "------------------------------\n"; }

say "=== ATS Self-Check @ $(date -u +"%F %T UTC") ==="
say "[ENV] REPO_ROOT=${REPO_ROOT}"
say "[ENV] PYTHONPATH=${PYTHONPATH}"

hr
say "[1/5] Python 基础与项目包"
if ! command -v python3 >/dev/null 2>&1; then
  err "python3 不存在"
else
  python3 -V || true
  # import ats & requests
  python3 - "$REPO_ROOT" <<'PY'
import sys, importlib, os
root = sys.argv[1]
print("[PY] sys.version:", sys.version.split()[0])
try:
    import requests
    print("[PY] requests OK:", requests.__version__)
except Exception as e:
    print("[PY] requests MISSING:", e); sys.exit(10)

# 尝试导入项目包 ats
try:
    m = importlib.import_module("ats")
    print("[PY] import ats OK:", getattr(m, "__file__", None))
except Exception as e:
    print("[PY] import ats FAILED:", e); sys.exit(11)
PY
  rc=$?
  if [ $rc -eq 0 ]; then ok "Python/requests/ats 检查通过"; else err "Python 环境检查失败(rc=$rc)"; fi
fi

hr
say "[2/5] DNS 解析"
python3 - <<'PY'
import socket, sys
hosts = ["fapi.binance.com","www.google.com","1.1.1.1"]
ok = True
for h in hosts:
    try:
        ip = socket.gethostbyname(h)
        print(f"[DNS] {h} -> {ip}")
    except Exception as e:
        print(f"[DNS] {h} FAIL:", e); ok = False
sys.exit(0 if ok else 12)
PY
rc=$?; [ $rc -eq 0 ] && ok "DNS 解析正常" || err "DNS 解析存在失败 (rc=$rc)"

hr
say "[3/5] Binance HTTP 连通 (使用 requests，不依赖 curl)"
python3 - <<'PY'
import sys, json
try:
    import requests
except Exception as e:
    print("[HTTP] requests MISSING:", e); sys.exit(13)

s = requests.Session()
s.headers.update({"User-Agent":"ats-selfcheck/1.0"})
def check(url, name, timeout=6):
    try:
        r = s.get(url, timeout=timeout)
        print(f"[HTTP] {name}: {r.status_code} {r.text[:120].replace(chr(10),' ')}")
        return r.status_code == 200
    except Exception as e:
        print(f"[HTTP] {name} ERR:", e)
        return False

ok = True
ok &= check("https://fapi.binance.com/fapi/v1/ping","binance.ping")
ok &= check("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT","binance.24hr")
sys.exit(0 if ok else 14)
PY
rc=$?; [ $rc -eq 0 ] && ok "Binance HTTP 正常" || err "Binance HTTP 访问失败 (rc=$rc)"

hr
say "[4/5] 配置文件校验（支持 params.yml 或 config/params.json）"
python3 - "$REPO_ROOT" <<'PY'
import sys, os, json
root = sys.argv[1]
found = False
try:
    import yaml  # PyYAML
except Exception as e:
    yaml = None

paths = [
    os.path.join(root, "params.yml"),
    os.path.join(root, "config", "params.json"),
]
loaded = None; pth = None; fmt = None

for p in paths:
    if os.path.exists(p):
        pth = p
        if p.endswith(".yml") or p.endswith(".yaml"):
            if yaml is None: 
                print("[CFG] 找到", p, "但缺少 PyYAML（requirements 中应包含 PyYAML）")
                break
            with open(p, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            fmt = "yaml"
        else:
            with open(p, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            fmt = "json"
        break

if loaded is None:
    print("[CFG] 未找到 params.yml 或 config/params.json")
    sys.exit(21)

# 打印顶层键与关键子段存在性（尽量通用）
keys = list(loaded.keys()) if isinstance(loaded, dict) else []
print(f"[CFG] 使用 {fmt}: {pth}")
print(f"[CFG] 顶层键数量: {len(keys)}")
if len(keys) == 0:
    print("[CFG] 警告：配置为空？")
# 提示常见字段（不强制）
hints = ["universe","trend","overlay","limits"]
miss = []
for h in hints:
    if isinstance(loaded, dict) and h not in loaded:
        miss.append(h)
if miss:
    print("[CFG] 提示：未见常见键 ->", ",".join(miss))
print("[CFG] OK")
sys.exit(0)
PY
rc=$?
if [ $rc -eq 0 ]; then ok "配置文件可读取"; else warn "配置文件未找到或不可读取 (rc=$rc)"; fi

hr
say "[5/5] Telegram 发送（默认跳过，仅提醒）"
: "${ATS_SKIP_SEND:=1}"
if [ "${ATS_SKIP_SEND}" != "0" ]; then
  say "[TG] ATS_SKIP_SEND != 0 -> 跳过发送验证（如需验证，导出 TELEGRAM_* 后设 ATS_SKIP_SEND=0 自测）"
else
  warn "[TG] 你已启用发送验证，但脚本未实现发送逻辑（建议使用 tools/send_symbol.py 单独验证）"
fi

hr
say "结果：WARN=${WARN}  FAIL=${FAIL}"
if [ ${FAIL} -eq 0 ]; then
  ok "Self-Check PASS"
  exit 0
else
  err "Self-Check FAIL"
  exit 1
fi
SH
chmod +x /opt/ats-quant/scripts/self_check.sh
'