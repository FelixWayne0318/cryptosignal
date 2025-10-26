#!/usr/bin/env python3
# coding: utf-8
"""
数据库初始化脚本

使用方法：
    python3 scripts/init_database.py            # 创建表
    python3 scripts/init_database.py --drop     # 删除并重建（危险！）
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.database.models import db, init_database


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Initialize CryptoSignal Database')
    parser.add_argument('--drop', action='store_true', help='Drop existing tables before creating (DANGEROUS!)')
    parser.add_argument('--db-url', help='Database URL (default: from environment or sqlite:///data/database/cryptosignal.db)')

    args = parser.parse_args()

    # 如果指定了数据库URL，更新全局实例
    if args.db_url:
        from ats_core.database.models import Database
        global db
        db = Database(args.db_url)

    print("=" * 60)
    print("CryptoSignal Database Initialization")
    print("=" * 60)
    print(f"Database URL: {db.db_url}")
    print()

    if args.drop:
        print("⚠️  WARNING: This will DROP all existing tables!")
        response = input("Are you absolutely sure? Type 'DROP' to confirm: ")
        if response == 'DROP':
            init_database(drop_existing=True)
        else:
            print("Cancelled. No changes made.")
            return
    else:
        init_database(drop_existing=False)

    print()
    print("=" * 60)
    print("✅ Database initialization completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Run your analysis: python3 tools/manual_run.py --send --top 10")
    print("  2. Query statistics: python3 scripts/query_stats.py")
    print()


if __name__ == '__main__':
    main()
