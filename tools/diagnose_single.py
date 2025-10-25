#!/usr/bin/env python3
# coding: utf-8
"""
诊断单个币种的完整分析结果
"""
import os
import sys
import json

os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.logging import log

def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"

    log(f"详细分析 {symbol}...")

    try:
        result = analyze_symbol(symbol)

        # 打印完整JSON
        print("\n" + "="*60)
        print("完整返回结果（JSON）")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

        # 打印关键字段
        print("\n" + "="*60)
        print("关键字段")
        print("="*60)
        print(f"symbol: {result.get('symbol')}")
        print(f"side: {result.get('side')}")
        print(f"probability: {result.get('probability')}")
        print(f"P_base: {result.get('P_base')}")
        print(f"F_score: {result.get('F_score')}")
        print(f"F_adjustment: {result.get('F_adjustment')}")

        print(f"\nscores: {result.get('scores')}")
        print(f"scores_long: {result.get('scores_long')}")
        print(f"scores_short: {result.get('scores_short')}")

        print(f"\npublish: {result.get('publish')}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
