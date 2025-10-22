import os
ATS_SEND_WATCH = os.environ.get('ATS_SEND_WATCH','0') == '1'
import os, urllib.request, urllib.parse

def _load_env():
    # read .env at repo root if exists
    try:
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for path in (os.path.join(root,".env"), os.path.expanduser("~/ats-analyzer/.env")):
            if os.path.isfile(path):
                for line in open(path,'r',encoding='utf-8'):
                    s=line.strip()
                    if not s or s.startswith("#") or "=" not in s: continue
                    k,v=s.split("=",1); k=k.strip(); v=v.strip()
                    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")): v=v[1:-1]
                    os.environ.setdefault(k,v)
    except: pass

def telegram_send(html:str):
    _load_env()
    token=os.environ.get("TELEGRAM_BOT_TOKEN")
    chat =os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat: return
    data=urllib.parse.urlencode({"chat_id":chat, "text":html, "parse_mode":"HTML", "disable_web_page_preview":"true"}).encode()
    req=urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=12).read()