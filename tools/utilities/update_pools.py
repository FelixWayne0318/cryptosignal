#!/usr/bin/env python3
# coding: utf-8
"""
候选池更新脚本 - 定时任务

用法:
1. 更新Elite Pool（每天一次）:
   python update_pools.py --elite

2. 更新Overlay Pool（每小时一次）:
   python update_pools.py --overlay

3. 强制更新所有池（清除缓存）:
   python update_pools.py --all

4. 查看缓存状态:
   python update_pools.py --status

Cron配置示例:
# Elite Pool - 每天凌晨2点更新
0 2 * * * cd /home/user/cryptosignal && /usr/bin/python3 update_pools.py --elite

# Overlay Pool - 每小时更新
0 * * * * cd /home/user/cryptosignal && /usr/bin/python3 update_pools.py --overlay
"""

from __future__ import annotations
import argparse
import json
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.pools.pool_manager import get_pool_manager
from ats_core.logging import log


def update_elite():
    """更新Elite Pool（稳定币种，24h缓存）"""
    log("=" * 60)
    log("🔄 Elite Pool更新任务启动")
    log("=" * 60)

    manager = get_pool_manager(
        elite_cache_hours=24,
        overlay_cache_hours=1,
        verbose=True
    )

    try:
        symbols = manager.force_update_elite()
        log(f"✅ Elite Pool更新成功: {len(symbols)} 个币种")
        log(f"   缓存路径: {manager.elite_cache_path}")
        log(f"   有效期: 24小时")
        return True
    except Exception as e:
        log(f"❌ Elite Pool更新失败: {e}")
        return False


def update_overlay():
    """更新Overlay Pool（异常币种+新币，1h缓存）"""
    log("=" * 60)
    log("🔄 Overlay Pool更新任务启动")
    log("=" * 60)

    manager = get_pool_manager(
        elite_cache_hours=24,
        overlay_cache_hours=1,
        verbose=True
    )

    try:
        symbols = manager.force_update_overlay()
        log(f"✅ Overlay Pool更新成功: {len(symbols)} 个币种")
        log(f"   缓存路径: {manager.overlay_cache_path}")
        log(f"   有效期: 1小时")
        return True
    except Exception as e:
        log(f"❌ Overlay Pool更新失败: {e}")
        return False


def update_all():
    """更新所有池"""
    log("=" * 60)
    log("🔄 全量池更新任务启动")
    log("=" * 60)

    elite_ok = update_elite()
    overlay_ok = update_overlay()

    if elite_ok and overlay_ok:
        log("✅ 所有池更新成功")
        return True
    else:
        log("⚠️ 部分池更新失败")
        return False


def show_status():
    """显示缓存状态"""
    log("=" * 60)
    log("📊 候选池缓存状态")
    log("=" * 60)

    manager = get_pool_manager(
        elite_cache_hours=24,
        overlay_cache_hours=1,
        verbose=False
    )

    status = manager.get_cache_status()

    # Elite Pool状态
    log("\n🏊 Elite Pool (稳定币种, 24h缓存):")
    elite = status.get('elite', {})
    if elite.get('exists'):
        log(f"   状态: {'✅ 有效' if elite['valid'] else '❌ 过期'}")
        log(f"   年龄: {elite['age_hours']:.2f} 小时")
        log(f"   最大有效期: {elite['max_age']} 小时")
        if elite['valid']:
            log(f"   下次更新: {elite['next_update']:.2f} 小时后")
        else:
            log(f"   建议: 立即运行 update_pools.py --elite")
    else:
        log(f"   状态: ⚠️ 不存在")
        log(f"   建议: 立即运行 update_pools.py --elite")

    # Overlay Pool状态
    log("\n⚡ Overlay Pool (异常币种+新币, 1h缓存):")
    overlay = status.get('overlay', {})
    if overlay.get('exists'):
        log(f"   状态: {'✅ 有效' if overlay['valid'] else '❌ 过期'}")
        log(f"   年龄: {overlay['age_hours']:.2f} 小时")
        log(f"   最大有效期: {overlay['max_age']} 小时")
        if overlay['valid']:
            log(f"   下次更新: {overlay['next_update']:.2f} 小时后")
        else:
            log(f"   建议: 立即运行 update_pools.py --overlay")
    else:
        log(f"   状态: ⚠️ 不存在")
        log(f"   建议: 立即运行 update_pools.py --overlay")

    log("\n" + "=" * 60)


def test_pool_manager():
    """测试池管理器"""
    log("=" * 60)
    log("🧪 池管理器测试")
    log("=" * 60)

    manager = get_pool_manager(
        elite_cache_hours=24,
        overlay_cache_hours=1,
        verbose=True
    )

    try:
        # 测试合并候选池
        symbols, metadata = manager.get_merged_universe()

        log("\n✅ 测试成功:")
        log(f"   总币种数: {metadata['total_count']}")
        log(f"   Elite Pool: {metadata['elite_count']} 个")
        log(f"   Overlay Pool: {metadata['overlay_count']} 个")
        log(f"   重叠币种: {metadata['overlap_count']} 个")
        log(f"   Elite缓存: {'有效' if metadata['elite_cache_valid'] else '重建'}")
        log(f"   Overlay缓存: {'有效' if metadata['overlay_cache_valid'] else '重建'}")

        if symbols:
            log(f"\n   前10个币种: {', '.join(symbols[:10])}")

        return True
    except Exception as e:
        log(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="候选池更新工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 更新Elite Pool（每天运行）
  python update_pools.py --elite

  # 更新Overlay Pool（每小时运行）
  python update_pools.py --overlay

  # 强制更新所有池
  python update_pools.py --all

  # 查看缓存状态
  python update_pools.py --status

  # 测试池管理器
  python update_pools.py --test

Cron配置:
  # Elite Pool - 每天凌晨2点
  0 2 * * * cd /home/user/cryptosignal && python update_pools.py --elite

  # Overlay Pool - 每小时
  0 * * * * cd /home/user/cryptosignal && python update_pools.py --overlay
        """
    )

    parser.add_argument(
        '--elite',
        action='store_true',
        help='更新Elite Pool（稳定币种，24h缓存）'
    )

    parser.add_argument(
        '--overlay',
        action='store_true',
        help='更新Overlay Pool（异常币种+新币，1h缓存）'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='更新所有池（Elite + Overlay）'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='显示缓存状态'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='测试池管理器'
    )

    args = parser.parse_args()

    # 如果没有指定任何参数，显示帮助
    if not any([args.elite, args.overlay, args.all, args.status, args.test]):
        parser.print_help()
        sys.exit(0)

    # 执行对应操作
    success = True

    if args.status:
        show_status()
    elif args.test:
        success = test_pool_manager()
    elif args.all:
        success = update_all()
    elif args.elite:
        success = update_elite()
    elif args.overlay:
        success = update_overlay()

    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
