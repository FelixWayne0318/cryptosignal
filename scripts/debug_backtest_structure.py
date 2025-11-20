#!/usr/bin/env python3
"""
调试回测结果数据结构
"""
import json
import sys

def debug_structure(report_path):
    with open(report_path) as f:
        data = json.load(f)

    print("="*60)
    print("回测结果数据结构调试")
    print("="*60)

    # 顶层键
    print(f"\n顶层键: {list(data.keys())}")

    # 检查signals
    signals = data.get('signals', [])
    print(f"\nSignals数量: {len(signals)}")

    if signals:
        print("\n第一个signal的键:")
        sig = signals[0]
        for key in sorted(sig.keys()):
            val = sig[key]
            if isinstance(val, dict):
                print(f"  {key}: dict with keys {list(val.keys())[:5]}...")
            elif isinstance(val, list):
                print(f"  {key}: list[{len(val)}]")
            else:
                print(f"  {key}: {type(val).__name__} = {str(val)[:50]}")

        # 检查step2_result
        if 'step2_result' in sig:
            print("\n  step2_result的键:")
            step2 = sig['step2_result']
            for key in sorted(step2.keys()):
                val = step2[key]
                if isinstance(val, dict):
                    print(f"    {key}: dict with keys {list(val.keys())}")
                else:
                    print(f"    {key}: {val}")
        else:
            print("\n  ⚠️ 没有step2_result!")
            # 查找可能的替代键
            possible = [k for k in sig.keys() if 'step' in k.lower() or 'timing' in k.lower()]
            if possible:
                print(f"  可能相关的键: {possible}")

    # 检查rejected_analyses
    rejects = data.get('rejected_analyses', [])
    print(f"\nRejected analyses数量: {len(rejects)}")

    if rejects:
        print("\n第一个reject的键:")
        rej = rejects[0]
        for key in sorted(rej.keys()):
            val = rej[key]
            if isinstance(val, dict):
                print(f"  {key}: dict with keys {list(val.keys())[:5]}...")
            elif isinstance(val, list):
                print(f"  {key}: list[{len(val)}]")
            else:
                print(f"  {key}: {type(val).__name__} = {str(val)[:50]}")

        # 检查step2_result
        if 'step2_result' in rej:
            print("\n  step2_result的键:")
            step2 = rej['step2_result']
            for key in sorted(step2.keys()):
                val = step2[key]
                if isinstance(val, dict):
                    print(f"    {key}: dict with keys {list(val.keys())}")
                else:
                    print(f"    {key}: {val}")

    # 检查是否有四步系统结果嵌套在其他地方
    print("\n" + "="*60)
    print("搜索enhanced_f相关字段...")
    print("="*60)

    def find_keys(obj, target, path=""):
        results = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if target.lower() in k.lower():
                    results.append((new_path, type(v).__name__, str(v)[:30] if not isinstance(v, (dict, list)) else "..."))
                results.extend(find_keys(v, target, new_path))
        elif isinstance(obj, list) and obj:
            results.extend(find_keys(obj[0], target, f"{path}[0]"))
        return results

    if signals:
        found = find_keys(signals[0], "enhanced")
        if found:
            print("\n在signal中找到的enhanced相关字段:")
            for path, typ, val in found:
                print(f"  {path}: {typ} = {val}")
        else:
            print("\n⚠️ 在signal中没有找到enhanced相关字段")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "reports/bnb_backtest_v743.json"
    debug_structure(path)
