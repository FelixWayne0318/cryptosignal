#!/usr/bin/env python3
"""
自动修复telegram_fmt.py中的所有`or {}`模式

替换模式：
    Before: xxx = _get(r, "key") or {}
    After:  xxx = _get_dict(r, "key")
"""

import re
from pathlib import Path

def auto_fix_or_dict():
    file_path = Path("/home/user/cryptosignal/ats_core/outputs/telegram_fmt.py")
    content = file_path.read_text()

    # 替换模式：xxx = _get(...) or {}  →  xxx = _get_dict(...)
    pattern = r'(\w+)\s*=\s*_get\(([^)]+)\)\s+or\s+\{\}'
    replacement = r'\1 = _get_dict(\2)'

    # 执行替换
    new_content, count = re.subn(pattern, replacement, content)

    print(f"✅ 成功替换 {count} 个 `or {{}}` 模式")

    # 写回文件
    file_path.write_text(new_content)
    print(f"✅ 文件已更新: {file_path}")

    # 验证语法
    import py_compile
    try:
        py_compile.compile(str(file_path), doraise=True)
        print("✅ Python语法验证通过")
    except py_compile.PyCompileError as e:
        print(f"❌ 语法错误: {e}")
        return False

    return True

if __name__ == "__main__":
    auto_fix_or_dict()
