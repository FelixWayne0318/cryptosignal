#!/usr/bin/env python3
# coding: utf-8
"""
候选池更新管理工具

更新策略：
- Base Pool: 每日更新1次（UTC 00:00）
- Overlay Pool: 每小时更新1次

用法：
  python3 update_pools.py --base      # 更新Base Pool
  python3 update_pools.py --overlay   # 更新Overlay Pool
  python3 update_pools.py --all       # 更新两者
  python3 update_pools.py --check     # 检查缓存状态
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.pools.base_builder import build_base_universe
from ats_core.pools.overlay_builder import build as build_overlay

DATA_DIR = project_root / "data"
BASE_FILE = DATA_DIR / "base_pool.json"
OVERLAY_FILE = DATA_DIR / "overlay_pool.json"

def get_file_age(filepath):
    """获取文件年龄（秒）"""
    if not filepath.exists():
        return float('inf')
    mtime = filepath.stat().st_mtime
    return time.time() - mtime

def format_age(seconds):
    """格式化时间"""
    if seconds == float('inf'):
        return "不存在"
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    if hours > 0:
        return f"{hours}小时{minutes}分钟前"
    else:
        return f"{minutes}分钟前"

def check_cache_status():
    """检查缓存状态"""
    print("=" * 60)
    print("候选池缓存状态")
    print("=" * 60)

    # Base Pool
    base_age = get_file_age(BASE_FILE)
    base_status = "✅ 有效" if base_age < 24*3600 else "⚠️ 过期"
    print(f"\n📦 Base Pool:")
    print(f"   文件: {BASE_FILE}")
    print(f"   更新: {format_age(base_age)}")
    print(f"   状态: {base_status} (建议每日更新)")

    if BASE_FILE.exists():
        with open(BASE_FILE) as f:
            base_data = json.load(f)
            print(f"   数量: {len(base_data)} 个币种")

    # Overlay Pool
    overlay_age = get_file_age(OVERLAY_FILE)
    overlay_status = "✅ 有效" if overlay_age < 3600 else "⚠️ 过期"
    print(f"\n🔥 Overlay Pool:")
    print(f"   文件: {OVERLAY_FILE}")
    print(f"   更新: {format_age(overlay_age)}")
    print(f"   状态: {overlay_status} (建议每小时更新)")

    if OVERLAY_FILE.exists():
        with open(OVERLAY_FILE) as f:
            overlay_data = json.load(f)
            print(f"   数量: {len(overlay_data)} 个币种")

    print("\n" + "=" * 60)

def update_base_pool():
    """更新Base Pool"""
    print("\n🔄 更新 Base Pool...")
    start = time.time()

    try:
        symbols = build_base_universe()
        elapsed = time.time() - start

        print(f"✅ Base Pool 更新成功！")
        print(f"   - 耗时: {elapsed:.1f}秒")
        print(f"   - 数量: {len(symbols)} 个币种")
        print(f"   - 文件: {BASE_FILE}")

        # 显示前10个
        if symbols:
            print(f"   - 样例: {', '.join(symbols[:10])}")

        return True
    except Exception as e:
        print(f"❌ Base Pool 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_overlay_pool():
    """更新Overlay Pool"""
    print("\n🔄 更新 Overlay Pool...")
    start = time.time()

    try:
        symbols = build_overlay()
        elapsed = time.time() - start

        # 保存到文件
        with open(OVERLAY_FILE, 'w', encoding='utf-8') as f:
            json.dump(symbols, f, ensure_ascii=False, indent=2)

        print(f"✅ Overlay Pool 更新成功！")
        print(f"   - 耗时: {elapsed:.1f}秒")
        print(f"   - 数量: {len(symbols)} 个币种")
        print(f"   - 文件: {OVERLAY_FILE}")

        if symbols:
            print(f"   - 列表: {', '.join(symbols)}")

        return True
    except Exception as e:
        print(f"❌ Overlay Pool 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='候选池更新管理工具')
    parser.add_argument('--base', action='store_true', help='更新Base Pool')
    parser.add_argument('--overlay', action='store_true', help='更新Overlay Pool')
    parser.add_argument('--all', action='store_true', help='更新全部')
    parser.add_argument('--check', action='store_true', help='检查缓存状态')
    parser.add_argument('--force', action='store_true', help='强制更新（忽略缓存）')

    args = parser.parse_args()

    # 默认检查状态
    if not (args.base or args.overlay or args.all or args.check):
        args.check = True

    if args.check:
        check_cache_status()
        return

    success = True

    if args.all or args.base:
        # 检查是否需要更新Base
        if args.force or get_file_age(BASE_FILE) > 24*3600:
            if not update_base_pool():
                success = False
        else:
            print("\n✓ Base Pool 仍然有效，跳过更新（使用 --force 强制更新）")

    if args.all or args.overlay:
        # 检查是否需要更新Overlay
        if args.force or get_file_age(OVERLAY_FILE) > 3600:
            if not update_overlay_pool():
                success = False
        else:
            print("\n✓ Overlay Pool 仍然有效，跳过更新（使用 --force 强制更新）")

    # 显示最终状态
    print()
    check_cache_status()

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
