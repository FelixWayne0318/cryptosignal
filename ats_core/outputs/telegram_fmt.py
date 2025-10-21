def _fmt_price(x): 
    return f"{x:.6g}"

def render_prime(r):
    s=r["scores"]; m=r["meta"]; p=r["pricing"]
    lines=[]
    lines.append(f"<b>{r['symbol']} · 现价 {_fmt_price(r['price'])}</b>")
    lines.append(f"{'🟩 做多' if r['side']=='多' else '🟥 做空'} 概率<b>{r['prob']}%</b>")
    lines.append(f"入场区：<code>{_fmt_price(p['entry_lo'])} – {_fmt_price(p['entry_hi'])}</code>  止损：<code>{_fmt_price(p['sl'])}</code>")
    lines.append(f"止盈：TP1=<code>+1R</code>  TP2=≤<code>2.5R</code>（对手位/Donchian72 限顶）")
    lines.append("六维分析：")
    lines.append(f"• 趋势 {s['T']}  (斜率/ATR={m['trend']['slopeATR']:+.2f} · R²={m['trend']['r2']:.2f} · 同侧={'是' if m['trend']['bg_same'] else '否'})")
    lines.append(f"• 结构 {s['S']}  (θ={m['struct']['theta']:.2f} · ICR={m['struct']['icr']:.2f} · 回撤={m['struct']['retr']:.2f} · 不过度={'是' if m['struct']['not_over'] else '否'})")
    lines.append(f"• 量能 {s['V']}  (v5/v20={m['volume']['v5v20']:.2f} · Vroc={m['volume']['vroc_abs']:.2f})")
    lines.append(f"• 加速 {s['A']}  (Δslope/CVD6h={m['accel']['dslope30']:+.3f}/{m['accel']['cvd6']:+.4f})")
    lines.append(f"• 持仓 {s['O']}  (OI24h={m['oi'].get('oi24h_pct')}% {'⚠️' if m['oi'].get('crowding_warn') else ''})")
    lines.append(f"• 环境 {s['E']}  (CHOP={m['env']['chop']:.1f} · Room={m['env']['room']:.2f}×ATR)")
    lines.append(f"环境：prior={m['prior']:.2f} · Q={m['Q']:.2f} · Funding极端={'否' if r['publish']['prime'] else ('是' if m['fund'].get('reason','')!='ok' else '否')}")
    lines.append("失效：① 回收入场下沿且 v5/v20<1  ② CVD 连续2h 反向")
    return "\n".join(lines)

def render_watch(r):
    s=r["scores"]; m=r["meta"]; p=r["pricing"]
    lines=[]
    lines.append(f"<b>ℹ️ 观察 · {r['symbol']}</b>")
    lines.append(f"侧：{r['side']} 概率 <b>{r['prob']}%</b> · 维度≥65 数量 {m['pass_dims']}/6")
    lines.append(f"参考区间（非指令）：<code>{_fmt_price(p['entry_lo'])} – {_fmt_price(p['entry_hi'])}</code> · 近端SR带 72h")
    why = "；".join(r["publish"]["reason"])
    lines.append(f"未发布原因：{why if why else '—'}")
    return "\n".join(lines)