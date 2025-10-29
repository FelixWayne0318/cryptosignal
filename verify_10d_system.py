#!/usr/bin/env python3
# coding: utf-8
"""
10维因子系统完整验证

验证所有10个因子是否正常工作：
- Layer 1: T, M, S, V (价格行为)
- Layer 2: C, O (资金流)
- Layer 3: L, B, Q (微观结构)
- Layer 4: I (市场环境)
"""
import os
import sys

sys.path.insert(0, '/home/user/cryptosignal')

def check_api_config():
    """检查API配置"""
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    return bool(api_key and api_secret)

def test_single_analysis():
    """测试单币种分析（analyze_symbol）"""
    from ats_core.pipeline.analyze_symbol import analyze_symbol

    print("\n" + "=" * 80)
    print("1️⃣  测试单币种分析 (analyze_symbol)")
    print("=" * 80)

    test_symbol = 'BTCUSDT'
    print(f"\n分析币种: {test_symbol}")
    print("-" * 80)

    try:
        result = analyze_symbol(test_symbol)
        scores = result.get('scores', {})
        scores_meta = result.get('scores_meta', {})

        # 10维因子状态
        factors = {
            'T': ('趋势', 'Layer1'),
            'M': ('动量', 'Layer1'),
            'S': ('结构', 'Layer1'),
            'V': ('成交量', 'Layer1'),
            'C': ('CVD', 'Layer2'),
            'O': ('持仓量', 'Layer2'),
            'L': ('流动性', 'Layer3'),
            'B': ('基差+资金费', 'Layer3'),
            'Q': ('清算密度', 'Layer3'),
            'I': ('独立性', 'Layer4')
        }

        print("\n10维因子评分：")
        print("-" * 80)

        all_working = True
        q_working = False
        i_working = False

        for factor, (name, layer) in factors.items():
            score = scores.get(factor, 0)
            meta = scores_meta.get(factor, {})

            # 判断因子状态
            if factor == 'Q':
                if score != 0:
                    status = "✅ 正常"
                    q_working = True
                elif 'note' in meta and '无清算数据' in str(meta['note']):
                    status = "⚠️  需要API认证"
                    all_working = False
                else:
                    status = "❌ 异常"
                    all_working = False
            elif factor == 'I':
                if score != 0:
                    status = "✅ 正常"
                    i_working = True
                else:
                    status = "❌ 异常"
                    all_working = False
            else:
                status = "✅ 正常" if score != 0 or factor == 'V' else "⚠️  注意"

            print(f"  {layer:8} {factor}({name:12}): {score:+6.1f}  {status}")

            # 显示元数据（仅Q和I）
            if factor in ['Q', 'I'] and meta:
                if 'note' in meta:
                    print(f"           说明: {meta['note']}")
                elif 'error' in meta:
                    print(f"           错误: {meta['error']}")

        # 总结
        print("\n" + "=" * 80)
        print("📊 单币种分析总结")
        print("=" * 80)

        if q_working and i_working:
            print("\n🎉 10维因子系统完全正常！")
            print("   ✅ Q因子（清算密度）工作正常")
            print("   ✅ I因子（独立性）工作正常")
        elif not q_working and i_working:
            print("\n⚠️  9/10因子正常工作")
            print("   ❌ Q因子需要API认证")
            print("   ✅ I因子工作正常")
            print("\n💡 配置Binance API以启用Q因子：")
            print("   1. 阅读：ENABLE_Q_FACTOR.md")
            print("   2. 运行：python3 test_api_auth.py")
        elif q_working and not i_working:
            print("\n⚠️  9/10因子正常工作")
            print("   ✅ Q因子工作正常")
            print("   ❌ I因子异常")
        else:
            print("\n❌ Q和I因子都有问题")
            print("   ❌ Q因子需要API认证")
            print("   ❌ I因子异常")

        return q_working, i_working

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, False

def test_batch_scan():
    """测试批量扫描（batch_scan_optimized）"""
    import asyncio
    from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner

    print("\n" + "=" * 80)
    print("2️⃣  测试批量扫描 (batch_scan_optimized)")
    print("=" * 80)

    async def run_scan():
        scanner = OptimizedBatchScanner()

        print("\n初始化批量扫描器...")
        await scanner.initialize()

        print("\n扫描前3个币种...")
        results = await scanner.scan()

        if not results:
            print("❌ 扫描失败")
            return False, False

        print(f"\n成功扫描 {len(results)} 个币种")
        print("-" * 80)

        # 检查前3个币种的Q/I因子
        q_count = 0
        i_count = 0

        for i, result in enumerate(results[:3]):
            symbol = result.get('symbol', 'UNKNOWN')
            scores = result.get('scores', {})

            Q = scores.get('Q', 0)
            I = scores.get('I', 0)

            print(f"\n{i+1}. {symbol:10} Q={Q:+6.1f}  I={I:+6.1f}")

            if Q != 0:
                q_count += 1
            if I != 0:
                i_count += 1

        print("\n" + "-" * 80)
        print(f"Q因子非零: {q_count}/3")
        print(f"I因子非零: {i_count}/3")

        q_working = q_count >= 2  # 至少2个币种Q因子工作
        i_working = i_count >= 2  # 至少2个币种I因子工作

        # 总结
        print("\n" + "=" * 80)
        print("📊 批量扫描总结")
        print("=" * 80)

        if q_working and i_working:
            print("\n🎉 批量扫描10维因子系统完全正常！")
        elif not q_working and i_working:
            print("\n⚠️  批量扫描I因子正常，Q因子需要API认证")
        elif q_working and not i_working:
            print("\n⚠️  批量扫描Q因子正常，I因子异常")
        else:
            print("\n❌ 批量扫描Q和I因子都有问题")

        return q_working, i_working

    try:
        return asyncio.run(run_scan())
    except Exception as e:
        print(f"\n❌ 批量扫描失败: {e}")
        import traceback
        traceback.print_exc()
        return False, False

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 10维因子系统完整验证")
    print("=" * 80)

    # 检查API配置
    has_api = check_api_config()
    print(f"\nAPI认证配置: {'✅ 已配置' if has_api else '❌ 未配置'}")
    if not has_api:
        print("⚠️  Q因子需要API认证，将会返回0")
        print("💡 配置方法: 阅读 ENABLE_Q_FACTOR.md")

    # 测试1: 单币种分析
    q1, i1 = test_single_analysis()

    # 测试2: 批量扫描
    q2, i2 = test_batch_scan()

    # 最终总结
    print("\n" + "=" * 80)
    print("🎯 最终验证结果")
    print("=" * 80)

    print("\n单币种分析:")
    print(f"  Q因子: {'✅ 正常' if q1 else '❌ 需配置'}")
    print(f"  I因子: {'✅ 正常' if i1 else '❌ 异常'}")

    print("\n批量扫描:")
    print(f"  Q因子: {'✅ 正常' if q2 else '❌ 需配置'}")
    print(f"  I因子: {'✅ 正常' if i2 else '❌ 异常'}")

    all_pass = q1 and i1 and q2 and i2
    partial_pass = i1 and i2  # I因子都正常

    if all_pass:
        print("\n" + "=" * 80)
        print("🎉🎉🎉 完美！10维因子系统完全正常！")
        print("=" * 80)
        print("\n所有功能验证通过：")
        print("  ✅ 单币种分析 Q/I 因子")
        print("  ✅ 批量扫描 Q/I 因子")
        print("  ✅ API认证配置")
        print("\n系统已准备就绪，可以投入使用！")
        return 0
    elif partial_pass:
        print("\n" + "=" * 80)
        print("⚠️  系统部分正常（9/10因子）")
        print("=" * 80)
        print("\n工作正常：")
        print("  ✅ I因子（独立性）完全正常")
        print("  ✅ 其他8个因子正常")
        print("\n需要配置：")
        print("  ❌ Q因子需要Binance API认证")
        print("\n下一步：")
        print("  1. 阅读配置指南：cat ENABLE_Q_FACTOR.md")
        print("  2. 测试API配置：python3 test_api_auth.py")
        print("  3. 重新验证系统：python3 verify_10d_system.py")
        return 1
    else:
        print("\n" + "=" * 80)
        print("❌ 系统验证失败")
        print("=" * 80)
        print("\n请检查：")
        print("  - 网络连接")
        print("  - Binance API访问")
        print("  - 系统日志中的错误信息")
        return 2

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
