import os, time, urllib.parse, urllib.request, json, pathlib

def load_env(env_path=".env"):
    """极简 .env 加载（KEY=VALUE），忽略注释与空行"""
    p = pathlib.Path(env_path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if not line or line.startswith("#"): 
            continue
        if "=" in line:
            k,v = line.split("=",1)
            os.environ.setdefault(k.strip(), v.strip())

def tg_send(text, parse_mode=None):
    """发送 Telegram 文本消息（标准库 urllib 实现）"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[WARN] TELEGRAM_* 未配置，跳过发送")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True
    }
    if parse_mode:
        data["parse_mode"] = parse_mode
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(req, timeout=10) as resp:
        _ = resp.read()
