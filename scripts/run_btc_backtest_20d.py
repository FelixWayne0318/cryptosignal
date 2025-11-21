#!/usr/bin/env python3
# coding: utf-8
"""
BTC 20天回测脚本
运行BTCUSDT最近20天的四步系统回测

Usage:
    python scripts/run_btc_backtest_20d.py
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

def main():
    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=20)

    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    # 创建输出目录
    reports_dir = Path(__file__).parent.parent / 'reports'
    reports_dir.mkdir(exist_ok=True)

    # 输出文件名
    output_file = reports_dir / f'btc_backtest_{start_str}_to_{end_str}.json'

    print("=" * 60)
    print("BTC 20天回测")
    print("=" * 60)
    print(f"交易对: BTCUSDT")
    print(f"开始日期: {start_str}")
    print(f"结束日期: {end_str}")
    print(f"输出文件: {output_file}")
    print("=" * 60)
    print()

    # 构建命令
    cmd = [
        sys.executable,
        str(Path(__file__).parent / 'backtest_four_step.py'),
        '--symbols', 'BTCUSDT',
        '--start', start_str,
        '--end', end_str,
        '--output', str(output_file)
    ]

    print(f"执行命令: {' '.join(cmd)}")
    print()

    # 运行回测
    try:
        result = subprocess.run(
            cmd,
            cwd=str(Path(__file__).parent.parent),
            check=True
        )

        print()
        print("=" * 60)
        print("回测完成!")
        print(f"报告文件: {output_file}")
        print("=" * 60)

        return 0

    except subprocess.CalledProcessError as e:
        print(f"回测失败: {e}")
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
