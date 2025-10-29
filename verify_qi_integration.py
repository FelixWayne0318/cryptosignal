#!/usr/bin/env python
# coding: utf-8
"""
验证Q和I因子集成逻辑（无需API访问）

此脚本通过模拟数据验证数据流是否正确。
"""
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.pipeline.analyze_symbol import _analyze_symbol_core

def create_mock_klines(num_candles, base_price):
    """创建模拟K线数据"""
    klines = []
    for i in range(num_candles):
        price = base_price * (1 + (i % 10) * 0.001)  # 小幅波动
        klines.append([
            1000000000 + i * 3600000,  # timestamp
            str(price),  # open
            str(price * 1.01),  # high
            str(price * 0.99),  # low
            str(price),  # close
            str(1000 + i),  # volume
            1000000000 + (i + 1) * 3600000,  # close time
            str(5000000),  # quote volume
            100,  # trades
            str(500),  # taker buy base
            str(2500000),  # taker buy quote
            "0"
        ])
    return klines

def create_mock_liquidations(count):
    """创建模拟清算数据"""
    liquidations = []
    for i in range(count):
        side = 'long' if i % 2 == 0 else 'short'
        liquidations.append({
            'side': side,
            'volume': 10000 + i * 1000,
            'price': 50000 + i * 10,
            'timestamp': 1000000000 + i * 60000
        })
    return liquidations

def verify_qi_integration():
    """验证Q和I因子集成逻辑"""
    print("\n" + "=" * 80)
    print("Q和I因子集成逻辑验证（模拟数据）")
    print("=" * 80)

    # 创建模拟数据
    print("\n📦 创建模拟数据...")
    k1h = create_mock_klines(300, 50000)  # 1h K线
    k4h = create_mock_klines(200, 50000)  # 4h K线
    oi_data = create_mock_klines(300, 50000)  # OI数据

    liquidations = create_mock_liquidations(100)  # 清算数据
    btc_klines = create_mock_klines(48, 95000)   # BTC K线
    eth_klines = create_mock_klines(48, 3500)    # ETH K线

    print(f"  ✅ 1h K线: {len(k1h)}根")
    print(f"  ✅ 4h K线: {len(k4h)}根")
    print(f"  ✅ OI数据: {len(oi_data)}条")
    print(f"  ✅ 清算数据: {len(liquidations)}条")
    print(f"  ✅ BTC K线: {len(btc_klines)}根")
    print(f"  ✅ ETH K线: {len(eth_klines)}根")

    # 调用核心分析函数
    print("\n🔍 调用_analyze_symbol_core()...")
    try:
        result = _analyze_symbol_core(
            symbol='BTCUSDT',
            k1=k1h,
            k4=k4h,
            oi_data=oi_data,
            spot_k1=None,
            elite_meta=None,
            orderbook=None,
            mark_price=None,
            funding_rate=None,
            spot_price=None,
            liquidations=liquidations,  # Q因子数据
            btc_klines=btc_klines,      # I因子数据
            eth_klines=eth_klines       # I因子数据
        )

        # 提取Q和I因子
        scores = result.get('scores', {})
        scores_meta = result.get('scores_meta', {})

        Q = scores.get('Q', 0)
        I = scores.get('I', 0)
        Q_meta = scores_meta.get('Q', {})
        I_meta = scores_meta.get('I', {})

        print("\n" + "=" * 80)
        print("📊 分析结果")
        print("=" * 80)

        # Q因子结果
        print(f"\n【Q因子 - 清算密度】")
        print(f"  分数: {Q:+.1f}/100")
        print(f"  元数据: {Q_meta}")

        if Q != 0:
            print("  ✅ Q因子计算成功（非零值）")
        elif 'note' in Q_meta:
            print(f"  ⚠️  Q因子返回0: {Q_meta['note']}")
        elif 'error' in Q_meta:
            print(f"  ❌ Q因子失败: {Q_meta['error']}")

        # I因子结果
        print(f"\n【I因子 - 独立性】")
        print(f"  分数: {I:+.1f}/100")
        print(f"  元数据: {I_meta}")

        if I != 0:
            print("  ✅ I因子计算成功（非零值）")
        elif 'note' in I_meta:
            print(f"  ⚠️  I因子返回0: {I_meta['note']}")
        elif 'error' in I_meta:
            print(f"  ❌ I因子失败: {I_meta['error']}")

        # 总结
        print("\n" + "=" * 80)
        print("💡 验证结论")
        print("=" * 80)

        if Q != 0 and I != 0:
            print("\n✅ Q和I因子集成逻辑正确！")
            print("   数据成功传递到分析函数并计算出非零值。")
            print("\n📝 下一步：")
            print("   在有Binance API访问的环境中运行test_10d_analysis.py")
            print("   验证真实数据下Q/I因子是否正常工作。")
        elif Q != 0:
            print("\n⚠️  Q因子工作，I因子返回0")
            print(f"   I因子原因: {I_meta}")
        elif I != 0:
            print("\n⚠️  I因子工作，Q因子返回0")
            print(f"   Q因子原因: {Q_meta}")
        else:
            print("\n❌ Q和I因子都返回0")
            print(f"   Q因子: {Q_meta}")
            print(f"   I因子: {I_meta}")

        print("\n" + "=" * 80)

        return result

    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    verify_qi_integration()
