#!/usr/bin/env python3
"""
分析telegram_fmt.py中的`or {}`使用，识别哪些需要修复

策略：
1. 找到所有`xxx = _get(...) or {}`的行
2. 在后续代码中查找`xxx.get(`的使用
3. 如果有使用.get()，则需要修复
"""

import re
from pathlib import Path

def analyze_or_dict_usage():
    file_path = Path("/home/user/cryptosignal/ats_core/outputs/telegram_fmt.py")
    content = file_path.read_text()
    lines = content.split('\n')

    # 匹配模式：变量名 = _get(...) or {}
    pattern = r'(\w+)\s*=\s*_get\([^)]+\)\s+or\s+\{\}'

    print("=" * 80)
    print("分析 telegram_fmt.py 中的 `or {}` 使用情况")
    print("=" * 80)

    needs_fix = []
    maybe_safe = []

    for i, line in enumerate(lines, 1):
        match = re.search(pattern, line)
        if match:
            var_name = match.group(1)

            # 检查后续10行中是否有.get()调用
            context_lines = lines[i:min(i+15, len(lines))]
            context = '\n'.join(context_lines)

            # 检查是否有 var_name.get( 调用
            get_pattern = rf'{var_name}\.get\('
            if re.search(get_pattern, context):
                needs_fix.append({
                    'line': i,
                    'var': var_name,
                    'code': line.strip(),
                })
            else:
                maybe_safe.append({
                    'line': i,
                    'var': var_name,
                    'code': line.strip(),
                })

    print(f"\n🔴 需要修复（后续使用.get()）: {len(needs_fix)}个")
    print("-" * 80)
    for item in needs_fix:
        print(f"L{item['line']:4d}: {item['var']:20s} - {item['code'][:60]}")

    print(f"\n🟡 可能安全（未发现.get()调用）: {len(maybe_safe)}个")
    print("-" * 80)
    for item in maybe_safe[:10]:  # 只显示前10个
        print(f"L{item['line']:4d}: {item['var']:20s} - {item['code'][:60]}")
    if len(maybe_safe) > 10:
        print(f"   ... 还有 {len(maybe_safe) - 10} 个")

    print("\n" + "=" * 80)
    print(f"总结: {len(needs_fix)} 个需要修复, {len(maybe_safe)} 个可能安全")
    print("=" * 80)

    return needs_fix, maybe_safe

if __name__ == "__main__":
    analyze_or_dict_usage()
