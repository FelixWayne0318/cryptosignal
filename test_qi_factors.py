#!/usr/bin/env python
# coding: utf-8
"""
测试Q和I因子是否正常工作
"""
import asyncio
from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner

async def test_qi_factors():
    """测试Q和I因子"""
    scanner = OptimizedBatchScanner()

    # 初始化（预加载所有数据）
    print("\n初始化扫描器...")
    await scanner.initialize()

    # 扫描前3个币种
    print("\n开始扫描前3个币种...")
    results = await scanner.scan()

    if not results:
        print("❌ 扫描失败，没有结果")
        return

    # 只显示前3个币种的Q和I因子
    print("\n" + "=" * 80)
    print("Q和I因子测试结果")
    print("=" * 80)

    for i, result in enumerate(results[:3]):
        symbol = result.get('symbol', 'UNKNOWN')
        scores = result.get('scores', {})
        scores_meta = result.get('scores_meta', {})

        Q = scores.get('Q', 0)
        I = scores.get('I', 0)
        L = scores.get('L', 0)
        B = scores.get('B', 0)

        Q_meta = scores_meta.get('Q', {})
        I_meta = scores_meta.get('I', {})

        print(f"\n【{symbol}】")
        print(f"  10维因子（新增部分）:")
        print(f"    L(流动性): {L:+.0f}")
        print(f"    B(基差+资金费): {B:+.0f}")
        print(f"    Q(清算密度): {Q:+.0f}")
        print(f"    I(独立性): {I:+.0f}")

        # Q因子详情
        if Q != 0 and 'note' not in Q_meta and 'error' not in Q_meta:
            print(f"\n  ✅ Q因子计算成功:")
            print(f"     分数: {Q:+.0f}/100")
            if 'long_liq_value' in Q_meta:
                long_val = Q_meta.get('long_liq_value', 0)
                short_val = Q_meta.get('short_liq_value', 0)
                print(f"     多单清算: ${long_val:,.0f}")
                print(f"     空单清算: ${short_val:,.0f}")
        elif 'note' in Q_meta:
            print(f"\n  ⚠️  Q因子: {Q_meta['note']}")
        elif 'error' in Q_meta:
            print(f"\n  ❌ Q因子失败: {Q_meta['error']}")
        else:
            print(f"\n  ⚠️  Q因子返回0（可能清算平衡）")

        # I因子详情
        if I != 0 and 'note' not in I_meta and 'error' not in I_meta:
            print(f"\n  ✅ I因子计算成功:")
            print(f"     分数: {I:+.0f}/100")
            if 'raw_score' in I_meta:
                raw = I_meta.get('raw_score', 0)
                beta_sum = I_meta.get('beta_sum', 0)
                print(f"     原始分数: {raw:.1f}/100")
                print(f"     Beta总和: {beta_sum:.3f}")
        elif 'note' in I_meta:
            print(f"\n  ⚠️  I因子: {I_meta['note']}")
        elif 'error' in I_meta:
            print(f"\n  ❌ I因子失败: {I_meta['error']}")
        else:
            print(f"\n  ⚠️  I因子返回0（可能与BTC/ETH完全相关）")

    print("\n" + "=" * 80)

    # 统计所有币种的Q和I因子
    q_nonzero = sum(1 for r in results if r.get('scores', {}).get('Q', 0) != 0)
    i_nonzero = sum(1 for r in results if r.get('scores', {}).get('I', 0) != 0)

    print(f"\n统计（共{len(results)}个币种）:")
    print(f"  Q因子非零: {q_nonzero}/{len(results)}")
    print(f"  I因子非零: {i_nonzero}/{len(results)}")

    # 判断测试是否成功
    if q_nonzero > 0 and i_nonzero > 0:
        print(f"\n✅ 测试通过！Q和I因子都正常工作")
    elif q_nonzero > 0:
        print(f"\n⚠️  部分成功：Q因子工作，但I因子全部为0")
    elif i_nonzero > 0:
        print(f"\n⚠️  部分成功：I因子工作，但Q因子全部为0")
    else:
        print(f"\n❌ 测试失败：Q和I因子都返回0")

    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_qi_factors())
