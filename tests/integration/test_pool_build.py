#!/usr/bin/env python3
# coding: utf-8
"""
测试候选池构建 - 带详细进度显示
用途：诊断候选池构建是否卡住，还是只是需要时间
"""
import os
import sys
import time

# 设置 PYTHONPATH
sys.path.insert(0, '/home/cryptosignal/cryptosignal')
os.chdir('/home/cryptosignal/cryptosignal')

print("=" * 60)
print("🔍 测试候选池构建（带详细进度）")
print("=" * 60)
print()

# 步骤1：测试获取24h数据
print("📊 [步骤1/3] 获取所有交易对24h数据...")
start = time.time()
try:
    from ats_core.sources.tickers import all_24h
    tickers = all_24h()
    elapsed = time.time() - start
    print(f"✅ 成功获取 {len(tickers)} 个交易对的24h数据")
    print(f"⏱️  耗时: {elapsed:.2f} 秒")
    print()
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 步骤2：筛选USDT交易对
print("🔍 [步骤2/3] 筛选USDT交易对（成交量>500万）...")
from ats_core.cfg import CFG

base_params = CFG.get("base", default={})
min_quote = base_params.get("min_quote_volume", 5000000)
blacklist = getattr(CFG, 'blacklist', []) or []

candidates = []
for x in tickers:
    try:
        sym = x["symbol"]
        q = float(x["quoteVolume"])
        if not sym.endswith("USDT"):
            continue
        if q < min_quote:
            continue
        if sym in blacklist:
            continue
        candidates.append({"symbol": sym, "quote": q})
    except:
        pass

candidates = sorted(candidates, key=lambda x: -x["quote"])
print(f"✅ 筛选出 {len(candidates)} 个候选交易对")
print(f"   前5名: {', '.join([c['symbol'] for c in candidates[:5]])}")
print()

# 步骤3：测试Z24计算（只测试前3个）
print("📈 [步骤3/3] 测试Z24计算（仅测试前3个交易对）...")
print("⚠️  每个交易对需要获取800根K线数据，可能需要几秒钟")
print()

from ats_core.sources.klines import klines_1h, split_ohlcv
import math
from statistics import median

def _robust_z24(symbol):
    print(f"   → 正在获取 {symbol} 的K线数据...", end="", flush=True)
    start = time.time()
    rows = klines_1h(symbol, 800)  # ~33d
    elapsed = time.time() - start
    print(f" 完成 ({elapsed:.2f}秒, {len(rows)}根K线)")

    _,_,_,c,_,_,_ = split_ohlcv(rows)
    if len(c) < 25:
        return None

    # build r24 series
    r = []
    for i in range(24, len(c)):
        r.append(math.log(c[i] / c[i-24]))
    if len(r) < 30:
        return None

    med = median(r)
    mad = median([abs(x-med) for x in r]) or 1e-9
    z = (r[-1] - med) / (1.4826 * mad)
    return z

test_count = min(3, len(candidates))
total_start = time.time()

for i in range(test_count):
    sym = candidates[i]["symbol"]
    try:
        z24 = _robust_z24(sym)
        if z24 is not None:
            print(f"      Z24 = {z24:+.3f}")
        else:
            print(f"      Z24 = None (数据不足)")
    except Exception as e:
        print(f"      ❌ 失败: {e}")

total_elapsed = time.time() - total_start
print()
print(f"⏱️  测试{test_count}个交易对总耗时: {total_elapsed:.2f} 秒")
print(f"⏱️  平均每个交易对: {total_elapsed/test_count:.2f} 秒")
print()

# 估算完整构建时间
estimated_total = (total_elapsed / test_count) * len(candidates)
print("=" * 60)
print(f"📊 估算完整候选池构建时间: {estimated_total/60:.1f} 分钟")
print(f"   (需要处理 {len(candidates)} 个交易对)")
print("=" * 60)
print()
print("💡 建议：")
print("   1. 如果等待时间过长，可以考虑减少 min_quote_volume")
print("   2. 或者使用缓存机制，避免每次都重新计算")
print("   3. 当前系统正常运行，只是需要时间处理网络请求")
