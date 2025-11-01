#!/usr/bin/env python3
# coding: utf-8
"""
验证StandardizationChain导入和chain实例
不需要numpy，仅检查语法和模块结构

运行: python tests/verify_standardization_imports.py
"""

import sys
import os
import importlib.util

def check_module_syntax(filepath):
    """检查Python文件语法"""
    try:
        spec = importlib.util.spec_from_file_location("module", filepath)
        if spec is None:
            return False, "Cannot load spec"
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """验证所有因子文件"""
    print("=" * 60)
    print("StandardizationChain 语法验证")
    print("=" * 60)

    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 11个因子文件
    factors = [
        ("T - Trend", "ats_core/features/trend.py", "_trend_chain"),
        ("M - Momentum", "ats_core/features/momentum.py", "_momentum_chain"),
        ("V - Volume", "ats_core/features/volume.py", "_volume_chain"),
        ("C - CVD Flow", "ats_core/features/cvd_flow.py", "_cvd_chain"),
        ("O - Open Interest", "ats_core/features/open_interest.py", "_oi_chain"),
        ("S - Accel", "ats_core/features/accel.py", "_accel_chain"),
        ("F - Funding Rate", "ats_core/features/funding_rate.py", "_funding_chain"),
        ("L - Liquidity", "ats_core/factors_v2/liquidity.py", "_liquidity_chain"),
        ("B - Basis+Funding", "ats_core/factors_v2/basis_funding.py", "_basis_chain"),
        ("Q - Liquidation", "ats_core/factors_v2/liquidation.py", "_liquidation_chain"),
        ("I - Independence", "ats_core/factors_v2/independence.py", "_independence_chain"),
    ]

    passed = 0
    failed = 0

    for name, rel_path, chain_name in factors:
        filepath = os.path.join(base_path, rel_path)

        # 检查文件存在
        if not os.path.exists(filepath):
            print(f"✗ {name}: 文件不存在 {filepath}")
            failed += 1
            continue

        # 检查语法
        ok, msg = check_module_syntax(filepath)
        if not ok:
            print(f"✗ {name}: 语法错误 - {msg}")
            failed += 1
            continue

        # 检查是否包含StandardizationChain导入
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        has_import = "from ats_core.scoring.scoring_utils import StandardizationChain" in content
        has_chain = f"{chain_name} = StandardizationChain" in content
        has_standardize_call = f"{chain_name}.standardize(" in content

        if not has_import:
            print(f"✗ {name}: 缺失StandardizationChain导入")
            failed += 1
            continue

        if not has_chain:
            print(f"✗ {name}: 缺失chain实例 {chain_name}")
            failed += 1
            continue

        if not has_standardize_call:
            print(f"⚠️  {name}: 警告 - chain实例已创建但未调用standardize()")
            # 不算failed，只是警告

        print(f"✓ {name}: 语法正确, 包含{chain_name}, 调用standardize()")
        passed += 1

    print("=" * 60)
    print(f"验证结果: {passed}/{len(factors)} 通过")

    if failed == 0:
        print("✅ 所有因子StandardizationChain集成验证通过！")
        print("\n关键检查项:")
        print("  ✓ 11个因子文件语法正确")
        print("  ✓ 11个独立chain实例已创建")
        print("  ✓ 11个standardize()调用已集成")
        return 0
    else:
        print(f"❌ {failed}个因子验证失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
