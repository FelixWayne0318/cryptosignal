# coding: utf-8
"""
批量收集六维分数的真实数据，进行统计分析

用途：
1. 从候选池获取交易对（或手动指定）
2. 逐个分析，收集六维分数 (T, A, S, V, O, E)
3. 统计每个维度的分布（最小、最大、中位数、0分占比）
4. 生成统计报告

用法：
  python3 collect_six_dim_stats.py --limit 30  # 分析前 30 个币
  python3 collect_six_dim_stats.py --symbols BTC ETH SOL  # 指定币种
"""
import sys
import argparse
import json
from statistics import median, mean
from collections import defaultdict

sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.pools.base_builder import build_base_universe
from ats_core.pools.overlay_builder import build as build_overlay

def collect_data(symbols, verbose=False):
    """收集六维分数数据"""
    results = []

    for idx, sym in enumerate(symbols, 1):
        if verbose:
            print(f"[{idx}/{len(symbols)}] 分析 {sym}...", end=" ", flush=True)

        try:
            r = analyze_symbol(sym)
            scores = r.get('scores', {})
            meta = r.get('scores_meta', {})

            data = {
                'symbol': sym,
                'side': r.get('side', ''),
                'probability': r.get('probability', 0),
                'T': scores.get('T', 50),
                'A': scores.get('A', 50),
                'S': scores.get('S', 50),
                'V': scores.get('V', 50),
                'O': scores.get('O', 50),
                'E': scores.get('E', 50),
                # 元数据
                'T_meta': meta.get('T', {}),
                'A_meta': meta.get('A', {}),
                'S_meta': meta.get('S', {}),
                'V_meta': meta.get('V', {}),
                'O_meta': meta.get('O', {}),
                'E_meta': meta.get('E', {}),
            }
            results.append(data)

            if verbose:
                print(f"✓ T={data['T']} A={data['A']} S={data['S']} V={data['V']} O={data['O']} E={data['E']}")

        except Exception as e:
            if verbose:
                print(f"✗ {e}")

    return results

def analyze_stats(results):
    """统计分析六维分数"""
    dims = ['T', 'A', 'S', 'V', 'O', 'E']

    stats = {}
    for dim in dims:
        values = [r[dim] for r in results]

        zero_count = sum(1 for v in values if v == 0)
        low_count = sum(1 for v in values if v < 30)

        stats[dim] = {
            'min': min(values),
            'max': max(values),
            'mean': round(mean(values), 1),
            'median': median(values),
            'zero_count': zero_count,
            'zero_pct': round(100 * zero_count / len(values), 1),
            'low_count': low_count,
            'low_pct': round(100 * low_count / len(values), 1),
            'distribution': _histogram(values)
        }

    return stats

def _histogram(values, bins=5):
    """简单直方图"""
    ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    hist = {}
    for lo, hi in ranges:
        count = sum(1 for v in values if lo <= v < hi or (hi == 100 and v == 100))
        hist[f'{lo}-{hi}'] = count
    return hist

def print_report(stats, total):
    """打印统计报告"""
    print(f"\n{'='*80}")
    print(f"六维分数统计报告（样本数：{total}）")
    print('='*80)

    print(f"\n{'维度':<6} {'最小':<6} {'最大':<6} {'平均':<6} {'中位数':<8} {'0分占比':<10} {'<30占比':<10}")
    print('-'*80)

    for dim in ['T', 'A', 'S', 'V', 'O', 'E']:
        s = stats[dim]
        print(f"{dim:<6} {s['min']:<6} {s['max']:<6} {s['mean']:<6} {s['median']:<8} "
              f"{s['zero_pct']}% ({s['zero_count']:<3}) {s['low_pct']}% ({s['low_count']:<3})")

    print('\n' + '='*80)
    print("分布详情")
    print('='*80)

    for dim in ['T', 'A', 'S', 'V', 'O', 'E']:
        print(f"\n{dim} 分数分布：")
        hist = stats[dim]['distribution']
        for range_name, count in hist.items():
            bar = '█' * int(count / total * 50)
            print(f"  {range_name:>8}: {count:3d} {bar}")

def main(argv):
    parser = argparse.ArgumentParser(description="批量收集六维分数统计")
    parser.add_argument("--limit", type=int, default=30, help="分析的交易对数量（默认 30）")
    parser.add_argument("--symbols", nargs="+", help="手动指定交易对符号")
    parser.add_argument("--save", action="store_true", help="保存详细数据为 JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细过程")

    args = parser.parse_args(argv)

    # 获取交易对列表
    if args.symbols:
        symbols = [s.upper() + ("USDT" if not s.endswith("USDT") else "") for s in args.symbols]
    else:
        print("正在构建候选池...")
        try:
            base = build_base_universe()
            overlay = build_overlay()
            symbols = overlay + [s for s in base if s not in overlay]
        except Exception as e:
            print(f"⚠️ 构建候选池失败: {e}")
            print("使用默认列表...")
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

        symbols = symbols[:args.limit]

    print(f"\n准备分析 {len(symbols)} 个交易对...")

    # 收集数据
    results = collect_data(symbols, verbose=args.verbose)

    if not results:
        print("❌ 未收集到任何数据")
        return 1

    # 统计分析
    stats = analyze_stats(results)

    # 打印报告
    print_report(stats, len(results))

    # 保存详细数据
    if args.save:
        import time
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"six_dim_stats_{ts}.json"

        output = {
            'timestamp': ts,
            'total_samples': len(results),
            'stats': stats,
            'details': results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 详细数据已保存: {filename}")

    # 关键发现
    print(f"\n{'='*80}")
    print("关键发现")
    print('='*80)

    for dim in ['T', 'A', 'S', 'V', 'O', 'E']:
        s = stats[dim]
        if s['zero_pct'] > 30:
            print(f"⚠️  {dim}: {s['zero_pct']}% 的币种得 0 分（{s['zero_count']}/{len(results)}），需要关注！")
        if s['mean'] < 35:
            print(f"⚠️  {dim}: 平均分只有 {s['mean']}，整体偏低")
        if s['max'] - s['min'] < 30:
            print(f"⚠️  {dim}: 分数范围只有 {s['max']-s['min']}，区分度不足")

    print('='*80)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
