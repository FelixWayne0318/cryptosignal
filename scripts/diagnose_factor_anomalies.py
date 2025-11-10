# coding: utf-8
"""
10因子异常诊断工具

用途：诊断F因子和I因子的分布异常
- F因子：75%=-100，25%=100（极端双峰分布）
- I因子：50%=50（固定值）

运行方法：
cd ~/cryptosignal
python3 scripts/diagnose_factor_anomalies.py
"""

import sys
import json
from pathlib import Path
from collections import Counter, defaultdict
import math

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🔍 10因子异常诊断工具")
print("=" * 80)

# 读取最新扫描详细数据
detail_file = project_root / 'reports' / 'latest' / 'scan_detail.json'
if not detail_file.exists():
    print(f"\n❌ 详细数据文件不存在: {detail_file}")
    print("   请先运行一次完整扫描")
    sys.exit(1)

with open(detail_file, 'r') as f:
    detail = json.load(f)

symbols_data = detail.get('symbols', [])
if not symbols_data:
    print(f"\n❌ 没有找到币种数据")
    sys.exit(1)

print(f"\n📊 数据概况:")
print(f"   币种数量: {len(symbols_data)}")

# ===== F因子诊断 =====
print("\n" + "=" * 80)
print("🔬 F因子诊断（资金领先性）")
print("=" * 80)

F_values = []
F_saturated_neg = []  # F=-100的币种
F_saturated_pos = []  # F=100的币种
F_normal = []         # -99到99之间的币种

for symbol_data in symbols_data:
    symbol = symbol_data.get('symbol', 'UNKNOWN')
    factors = symbol_data.get('factors', {})
    F = factors.get('F', 0)

    F_values.append(F)

    if F <= -100:
        F_saturated_neg.append({
            'symbol': symbol,
            'F': F,
            'meta': factors.get('F_meta', {})
        })
    elif F >= 100:
        F_saturated_pos.append({
            'symbol': symbol,
            'F': F,
            'meta': factors.get('F_meta', {})
        })
    else:
        F_normal.append({
            'symbol': symbol,
            'F': F,
            'meta': factors.get('F_meta', {})
        })

total_F = len(F_values)
print(f"\n📊 F因子分布:")
print(f"   总币种数: {total_F}")
print(f"   F = -100: {len(F_saturated_neg)} ({len(F_saturated_neg)/total_F*100:.1f}%)")
print(f"   F = +100: {len(F_saturated_pos)} ({len(F_saturated_pos)/total_F*100:.1f}%)")
print(f"   -99 ≤ F ≤ 99: {len(F_normal)} ({len(F_normal)/total_F*100:.1f}%)")

# 分析饱和原因
print(f"\n🔍 F=-100 饱和分析（随机抽样5个）:")
for item in F_saturated_neg[:5]:
    meta = item['meta']
    print(f"\n   {item['symbol']}:")
    print(f"      F_raw: {meta.get('F_raw', 'N/A')}")
    print(f"      fund_momentum: {meta.get('fund_momentum', 'N/A')}")
    print(f"      price_momentum: {meta.get('price_momentum', 'N/A')}")
    print(f"      cvd_6h_norm: {meta.get('cvd_6h_norm', 'N/A')}")
    print(f"      oi_6h_pct: {meta.get('oi_6h_pct', 'N/A')}")
    print(f"      atr_norm: {meta.get('atr_norm', 'N/A')}")

    # 计算tanh输入
    F_raw = meta.get('F_raw', 0)
    if F_raw != 'N/A':
        tanh_input = F_raw / 2.0  # scale=2.0
        print(f"      tanh输入: {tanh_input:.4f} (饱和阈值: ±3)")
        if abs(tanh_input) > 3:
            print(f"      ⚠️ tanh已饱和！")

print(f"\n🔍 F=+100 饱和分析（随机抽样5个）:")
for item in F_saturated_pos[:5]:
    meta = item['meta']
    print(f"\n   {item['symbol']}:")
    print(f"      F_raw: {meta.get('F_raw', 'N/A')}")
    print(f"      fund_momentum: {meta.get('fund_momentum', 'N/A')}")
    print(f"      price_momentum: {meta.get('price_momentum', 'N/A')}")
    print(f"      cvd_6h_norm: {meta.get('cvd_6h_norm', 'N/A')}")
    print(f"      oi_6h_pct: {meta.get('oi_6h_pct', 'N/A')}")
    print(f"      atr_norm: {meta.get('atr_norm', 'N/A')}")

    F_raw = meta.get('F_raw', 0)
    if F_raw != 'N/A':
        tanh_input = F_raw / 2.0
        print(f"      tanh输入: {tanh_input:.4f} (饱和阈值: ±3)")
        if abs(tanh_input) > 3:
            print(f"      ⚠️ tanh已饱和！")

# ===== I因子诊断 =====
print("\n" + "=" * 80)
print("🔬 I因子诊断（独立性）")
print("=" * 80)

I_values = []
I_default = []    # I=50的币种（默认值）
I_normal = []     # 非50的币种
I_errors = defaultdict(int)  # 错误原因统计

for symbol_data in symbols_data:
    symbol = symbol_data.get('symbol', 'UNKNOWN')
    factors = symbol_data.get('factors', {})
    I = factors.get('I', 50)

    I_values.append(I)

    if I == 50:
        meta = factors.get('I_meta', {})
        error = meta.get('error', None)

        I_default.append({
            'symbol': symbol,
            'I': I,
            'meta': meta,
            'error': error
        })

        if error:
            I_errors[error] += 1
    else:
        I_normal.append({
            'symbol': symbol,
            'I': I,
            'meta': factors.get('I_meta', {})
        })

total_I = len(I_values)
print(f"\n📊 I因子分布:")
print(f"   总币种数: {total_I}")
print(f"   I = 50（默认值）: {len(I_default)} ({len(I_default)/total_I*100:.1f}%)")
print(f"   I ≠ 50（正常计算）: {len(I_normal)} ({len(I_normal)/total_I*100:.1f}%)")

if I_errors:
    print(f"\n🔍 I=50 降级原因分析:")
    for error_type, count in sorted(I_errors.items(), key=lambda x: -x[1]):
        print(f"   {error_type}: {count} ({count/len(I_default)*100:.1f}%)")

# 抽样分析
print(f"\n🔍 I=50 降级案例（随机抽样5个）:")
for item in I_default[:5]:
    meta = item['meta']
    print(f"\n   {item['symbol']}:")
    error = meta.get('error', 'Unknown')
    print(f"      降级原因: {error}")

    if error == 'Insufficient data':
        print(f"      alt_len: {meta.get('alt_len', 'N/A')}")
        print(f"      btc_len: {meta.get('btc_len', 'N/A')}")
        print(f"      eth_len: {meta.get('eth_len', 'N/A')}")
        print(f"      required: {meta.get('required', 'N/A')}")

if I_normal:
    print(f"\n🔍 I≠50 正常案例（随机抽样5个）:")
    for item in I_normal[:5]:
        meta = item['meta']
        print(f"\n   {item['symbol']}: I={item['I']}")
        print(f"      beta_sum: {meta.get('beta_sum', 'N/A')}")
        print(f"      beta_btc: {meta.get('beta_btc', 'N/A')}")
        print(f"      beta_eth: {meta.get('beta_eth', 'N/A')}")
        print(f"      independence_level: {meta.get('independence_level', 'N/A')}")

# ===== 诊断结论 =====
print("\n" + "=" * 80)
print("💡 诊断结论")
print("=" * 80)

print(f"\n【问题1】F因子极端双峰分布")
print(f"   ❌ 现象: {len(F_saturated_neg)/total_F*100:.1f}% 币种F=-100, {len(F_saturated_pos)/total_F*100:.1f}% 币种F=100")
print(f"   🔍 根本原因: tanh函数饱和")
print(f"      - F_raw值过大（>>2.0）或过小（<<-2.0）")
print(f"      - 导致tanh(F_raw/2.0)饱和到±1")
print(f"   🎯 可能原因:")
print(f"      1. atr_norm_factor过小，导致归一化后值过大")
print(f"      2. CVD或OI数据异常")
print(f"      3. scale参数（当前=2.0）过小，需要增大")

print(f"\n【问题2】I因子固定为50")
print(f"   ❌ 现象: {len(I_default)/total_I*100:.1f}% 币种I=50（默认值）")
print(f"   🔍 根本原因: BTC/ETH价格数据不足")
if I_errors:
    print(f"   📊 主要错误:")
    for error_type, count in list(sorted(I_errors.items(), key=lambda x: -x[1]))[:3]:
        print(f"      - {error_type}: {count} 币种")
print(f"   🎯 要求:")
print(f"      - 需要至少49根K线的BTC/ETH价格数据（48小时窗口）")
print(f"      - 如果数据不足，降级为默认值50")

# ===== 修复建议 =====
print("\n" + "=" * 80)
print("🔧 修复建议")
print("=" * 80)

print(f"\n【修复方案1】F因子 - 调整scale参数")
print(f"   当前: scale = 2.0")
print(f"   建议: scale = 5.0 或更大")
print(f"   目的: 减少tanh饱和，增加中间值分布")
print(f"   修改文件: config/factors_unified.json")
print(f"   路径: F.v2.scale")

print(f"\n【修复方案2】F因子 - 检查数据质量")
print(f"   检查项:")
print(f"      1. CVD数据是否正常")
print(f"      2. OI数据是否正常")
print(f"      3. ATR计算是否合理")
print(f"   诊断工具: 上面的F_meta元数据")

print(f"\n【修复方案3】I因子 - 确保BTC/ETH数据")
print(f"   当前问题: {len(I_default)} 币种缺少BTC/ETH数据")
print(f"   解决方案:")
print(f"      1. 检查BTC/ETH价格获取逻辑")
print(f"      2. 确保scan_symbols时传入BTC/ETH数据")
print(f"      3. 降低window_hours（当前48h）到24h")
print(f"   修改文件: config/factors_unified.json")
print(f"   路径: I.window_hours")

print(f"\n【优先级】")
print(f"   P0: 修复F因子（影响信号质量）")
print(f"   P1: 修复I因子（影响Gate5过滤）")

print("\n" + "=" * 80)
print("✅ 诊断完成")
print("=" * 80)
