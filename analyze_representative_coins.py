#!/usr/bin/env python
# coding: utf-8
"""
代表性币种的10维评分详细分析
"""

def analyze_coins():
    """分析代表性币种"""
    from ats_core.pipeline.analyze_symbol import analyze_symbol

    # 选择5个代表性币种
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT']

    print("=" * 80)
    print("代表性币种的10维评分分析")
    print("=" * 80)

    all_results = []

    for symbol in symbols:
        try:
            print(f"\n正在分析 {symbol}...")
            result = analyze_symbol(symbol)

            # 提取关键信息
            factors = result.get('factors', {})
            meta = result.get('meta', {})
            weighted_score = result.get('weighted_score', 0)
            confidence = result.get('confidence', 0)
            probability = result.get('probability', 0.5) * 100
            prime_strength = result.get('publish', {}).get('prime_strength', 0)

            # 10维因子
            T = factors.get('T', 0)
            M = factors.get('M', 0)
            S = factors.get('S', 0)
            V = factors.get('V', 0)
            C = factors.get('C', 0)
            O = factors.get('O', 0)
            L = factors.get('L', 0)
            B = factors.get('B', 0)
            Q = factors.get('Q', 0)
            I = factors.get('I', 0)

            # Layer分数
            layer1 = T + M + S + V  # 价格行为（65分权重）
            layer2 = C + O           # 资金流（40分权重）
            layer3 = L + B + Q       # 微观结构（45分权重）
            layer4 = I               # 市场环境（10分权重）

            # 打印结果
            print(f"\n{'=' * 80}")
            print(f"【{symbol}】")
            print(f"{'=' * 80}")
            print(f"  Prime强度: {prime_strength:.1f}/100 (阈值65)")
            print(f"  概率: {probability:.1f}% (阈值62%)")
            print(f"  置信度: {confidence:.1f}")
            print(f"  加权分数: {weighted_score:+.1f}")

            print(f"\n  10维评分:")
            print(f"    Layer1（价格行为，65分）: T={T:+4.0f} M={M:+4.0f} S={S:+4.0f} V={V:+4.0f} → {layer1:+4.0f}")
            print(f"    Layer2（资金流，40分）  : C={C:+4.0f} O={O:+4.0f}                   → {layer2:+4.0f}")
            print(f"    Layer3（微观结构，45分）: L={L:+4.0f} B={B:+4.0f} Q={Q:+4.0f}       → {layer3:+4.0f}")
            print(f"    Layer4（市场环境，10分）: I={I:+4.0f}                            → {layer4:+4.0f}")

            # L因子详情
            L_meta = meta.get('L', {})
            if L_meta and 'note' not in L_meta:
                print(f"\n  L(流动性): {L:+.1f} (原始{L_meta.get('raw_score', 0):.1f}/100)")
                print(f"    价差: {L_meta.get('spread_bps', 0):.2f} bps")
                print(f"    深度: ${L_meta.get('bid_depth_usdt', 0) + L_meta.get('ask_depth_usdt', 0):,.0f}")
                print(f"    等级: {L_meta.get('liquidity_level', 'unknown')}")
            elif L_meta and 'note' in L_meta:
                print(f"\n  L(流动性): {L:+.1f} ({L_meta['note']})")

            # B因子详情
            B_meta = meta.get('B', {})
            if B_meta and 'note' not in B_meta:
                print(f"\n  B(基差+资金费): {B:+.1f}")
                print(f"    基差: {B_meta.get('basis_bps', 0):+.2f} bps")
                print(f"    资金费率: {B_meta.get('funding_rate', 0):.4%}")
                print(f"    情绪: {B_meta.get('sentiment', 'unknown')}")
            elif B_meta and 'note' in B_meta:
                print(f"\n  B(基差+资金费): {B:+.1f} ({B_meta['note']})")

            # O因子详情
            O_meta = meta.get('O', {})
            if O_meta:
                print(f"\n  O(持仓量): {O:+.1f}")
                print(f"    制度: {O_meta.get('regime', 'unknown')}")
                print(f"    OI变化: {O_meta.get('oi_change_pct', 0):+.1f}%")

            all_results.append({
                'symbol': symbol,
                'prime_strength': prime_strength,
                'probability': probability,
                'weighted_score': weighted_score,
                'L': L,
                'B': B,
                'layer1': layer1,
                'layer2': layer2,
                'layer3': layer3,
                'layer4': layer4
            })

        except Exception as e:
            print(f"\n❌ {symbol} 分析失败: {e}")
            import traceback
            traceback.print_exc()

    # 汇总对比
    print(f"\n{'=' * 80}")
    print("汇总对比")
    print(f"{'=' * 80}")
    print(f"{'币种':<12} {'Prime':<8} {'概率':<8} {'L':<8} {'B':<8} {'Layer3':<8}")
    print("-" * 80)

    for r in all_results:
        print(f"{r['symbol']:<12} {r['prime_strength']:>6.1f}  {r['probability']:>6.1f}%  "
              f"{r['L']:>+6.0f}  {r['B']:>+6.0f}  {r['layer3']:>+6.0f}")

    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)

if __name__ == "__main__":
    analyze_coins()
