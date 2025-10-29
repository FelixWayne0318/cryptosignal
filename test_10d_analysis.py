#!/usr/bin/env python3
# coding: utf-8
"""
代表性币种的10维评分详细分析（修复版）
"""

from ats_core.pipeline.analyze_symbol import analyze_symbol

# 测试几个代表性币种
test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT']

print('\n' + '='*80)
print('代表性币种的10维评分分析')
print('='*80)

results = []
for symbol in test_symbols:
    result = analyze_symbol(symbol)
    results.append(result)

    prime_strength = result.get('publish', {}).get('prime_strength', 0)
    probability = result.get('probability', 0)
    confidence = result.get('confidence', 0)
    weighted_score = result.get('weighted_score', 0)

    # ✅ 正确：从 factors 字典中提取10维分数
    factors = result.get('factors', {})
    T = factors.get('T', 0)
    M = factors.get('M', 0)
    C = factors.get('C', 0)
    S = factors.get('S', 0)
    V = factors.get('V', 0)
    O = factors.get('O', 0)
    L = factors.get('L', 0)
    B = factors.get('B', 0)
    Q = factors.get('Q', 0)
    I = factors.get('I', 0)

    # L和B元数据
    meta = result.get('meta', {})
    L_meta = meta.get('L', {})
    B_meta = meta.get('B', {})
    O_meta = meta.get('O', {})

    # Layer汇总
    layer1 = T + M + S + V  # 价格行为（65分权重）
    layer2 = C + O          # 资金流（40分权重）
    layer3 = L + B + Q      # 微观结构（45分权重）
    layer4 = I              # 市场环境（10分权重）

    print(f'\n【{symbol}】')
    print(f'  Prime强度: {prime_strength:.1f}/100 (阈值65)')
    print(f'  概率: {probability:.1%} (阈值62%)')
    print(f'  置信度: {confidence:.1f}')
    print(f'  加权分数: {weighted_score:+.1f}')

    print(f'\n  10维评分:')
    print(f'    Layer1（价格行为，65分）: T={T:+4.0f} M={M:+4.0f} S={S:+4.0f} V={V:+4.0f} → {layer1:+4.0f}')
    print(f'    Layer2（资金流，40分）  : C={C:+4.0f} O={O:+4.0f}                   → {layer2:+4.0f}')
    print(f'    Layer3（微观结构，45分）: L={L:+4.0f} B={B:+4.0f} Q={Q:+4.0f}       → {layer3:+4.0f}')
    print(f'    Layer4（市场环境，10分）: I={I:+4.0f}                            → {layer4:+4.0f}')

    # L因子详情
    if L_meta and 'note' not in L_meta:
        L_raw = L_meta.get('raw_score', 0)
        spread_bps = L_meta.get('spread_bps', 0)
        bid_depth = L_meta.get('bid_depth_usdt', 0)
        ask_depth = L_meta.get('ask_depth_usdt', 0)
        depth_total = bid_depth + ask_depth
        level = L_meta.get('liquidity_level', 'unknown')

        print(f'\n  L(流动性): {L:+.1f} (原始{L_raw:.1f}/100)')
        print(f'    价差: {spread_bps:.2f} bps')
        print(f'    深度: ${depth_total:,.0f} (买${bid_depth:,.0f} + 卖${ask_depth:,.0f})')
        print(f'    等级: {level}')
    else:
        note = L_meta.get('note', '未知') if L_meta else '无数据'
        print(f'\n  L(流动性): {L:+.0f} ({note})')

    # B因子详情
    if B_meta and 'note' not in B_meta:
        basis_bps = B_meta.get('basis_bps', 0)
        funding_rate = B_meta.get('funding_rate', 0)
        sentiment = B_meta.get('sentiment', 'unknown')

        print(f'\n  B(基差+资金费): {B:+.1f}')
        print(f'    基差: {basis_bps:+.2f} bps')
        print(f'    资金费率: {funding_rate:.4%}')
        print(f'    情绪: {sentiment}')
    else:
        note = B_meta.get('note', '未知') if B_meta else '无数据'
        print(f'\n  B(基差+资金费): {B:+.0f} ({note})')

    # O因子详情
    if O_meta:
        regime = O_meta.get('regime', 'unknown')
        oi_change = O_meta.get('oi_change_pct', 0)
        print(f'\n  O(持仓量): {O:+.1f}')
        print(f'    制度: {regime}')
        print(f'    OI变化: {oi_change:+.1f}%')

    # Prime判定
    is_prime = result.get('publish', {}).get('prime', False)
    if is_prime:
        print(f'\n  ✅ 通过Prime筛选')
    else:
        reasons = []
        if prime_strength < 65:
            reasons.append(f'强度{prime_strength:.0f}<65')
        if probability < 0.62:
            reasons.append(f'概率{probability:.0%}<62%')
        print(f'\n  ❌ 未通过Prime: {", ".join(reasons)}')

# 找出最强的币种
top_result = max(results, key=lambda x: x.get('publish', {}).get('prime_strength', 0))
top_symbol = top_result.get('symbol', 'UNKNOWN')
top_prime = top_result.get('publish', {}).get('prime_strength', 0)

print(f'\n' + '='*80)
print(f'最强币种: {top_symbol} = {top_prime:.1f}分')
print(f'市场状态: {"有高质量机会" if top_prime >= 65 else "当前没有Prime级别的交易机会"}')
print('='*80)

# 汇总表格
print(f'\n{"="*80}')
print('汇总对比')
print(f'{"="*80}')
print(f'{"币种":<10} {"Prime":<8} {"概率":<8} {"L":<8} {"B":<8} {"Layer3":<10}')
print('-'*80)

for r in results:
    symbol = r.get('symbol', 'UNKNOWN')
    prime = r.get('publish', {}).get('prime_strength', 0)
    prob = r.get('probability', 0) * 100

    factors = r.get('factors', {})
    L = factors.get('L', 0)
    B = factors.get('B', 0)
    Q = factors.get('Q', 0)
    layer3 = L + B + Q

    print(f'{symbol:<10} {prime:>6.1f}  {prob:>6.1f}%  {L:>+6.0f}  {B:>+6.0f}  {layer3:>+8.0f}')

print('='*80)
