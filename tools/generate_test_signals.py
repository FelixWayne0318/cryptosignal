#!/usr/bin/env python3
# coding: utf-8
"""
测试信号生成器

用于生成历史测试信号，以便测试回测系统。

功能：
1. 基于真实历史价格数据
2. 生成符合系统格式的信号
3. 随机分布不同概率和方向
4. 包含完整的止盈止损信息

用法：
    python3 tools/generate_test_signals.py --days 30 --signals 50
    python3 tools/generate_test_signals.py --start 2024-01-01 --end 2024-01-31 --signals 100
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from random import Random

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.database.models import db, Signal


# Mock price ranges for different symbols (for testing without API calls)
MOCK_PRICES = {
    'BTCUSDT': (60000, 70000),
    'ETHUSDT': (3000, 3500),
    'BNBUSDT': (500, 600),
    'SOLUSDT': (120, 180),
    'ADAUSDT': (0.4, 0.6),
    'XRPUSDT': (0.5, 0.7),
    'DOGEUSDT': (0.08, 0.12),
    'AVAXUSDT': (25, 35),
    'MATICUSDT': (0.6, 0.9),
    'LINKUSDT': (12, 18),
}


def generate_test_signals(start_time, end_time, num_signals=50, seed=42, use_mock_prices=True):
    """
    生成测试信号

    Args:
        start_time: 开始时间
        end_time: 结束时间
        num_signals: 生成信号数量
        seed: 随机种子（可重现）
    """
    rng = Random(seed)

    # 常用币种池
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
               'XRPUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT']

    session = db.get_session()
    created_count = 0

    print(f"🔄 Generating {num_signals} test signals...")
    print(f"   Period: {start_time.date()} to {end_time.date()}")
    print(f"   Symbols: {', '.join(symbols)}")
    print()

    # 时间跨度（小时）
    total_hours = int((end_time - start_time).total_seconds() / 3600)

    for i in range(num_signals):
        # 随机选择币种
        symbol = rng.choice(symbols)

        # 随机选择时间点
        hours_offset = rng.randint(0, total_hours)
        signal_time = start_time + timedelta(hours=hours_offset)

        # 随机方向
        side = rng.choice(['long', 'short'])

        # 随机概率（50%-85%）
        probability = rng.uniform(0.5, 0.85)

        # 随机生成7维分数（40-90分）
        scores = {
            'T': rng.randint(40, 90),
            'M': rng.randint(40, 90),
            'C': rng.randint(40, 90),
            'S': rng.randint(40, 90),
            'V': rng.randint(40, 90),
            'O': rng.randint(40, 90),
            'E': rng.randint(40, 90),
        }

        # 判断是否Prime（概率>=62% 且至少4维>=65分）
        dims_ok = sum(1 for score in scores.values() if score >= 65)
        is_prime = probability >= 0.62 and dims_ok >= 4

        # 使用Mock价格（更快更可靠，用于测试）
        try:
            if use_mock_prices:
                # 使用预设的价格范围
                price_range = MOCK_PRICES.get(symbol, (100, 200))
                current_price = rng.uniform(*price_range)

                # 模拟ATR（约为价格的2-3%）
                atr = current_price * rng.uniform(0.02, 0.03)
            else:
                # 获取真实价格（可能较慢或失败）
                from ats_core.sources.binance import get_klines

                klines = get_klines(symbol, '1h', limit=100)
                if not klines:
                    print(f"   ⚠️  Skipping {symbol} at {signal_time}: No price data")
                    continue

                # 找到最接近信号时间的K线
                closest_bar = None
                min_diff = float('inf')

                for k in klines:
                    bar_time = datetime.fromtimestamp(int(k[0]) / 1000)
                    diff = abs((bar_time - signal_time).total_seconds())

                    if diff < min_diff:
                        min_diff = diff
                        closest_bar = k

                if not closest_bar:
                    print(f"   ⚠️  Skipping {symbol} at {signal_time}: No matching bar")
                    continue

                # 提取价格信息
                current_price = float(closest_bar[4])  # close
                high = float(closest_bar[2])
                low = float(closest_bar[3])

                # 估算ATR（简化版）
                atr = (high - low) * 0.7

            # 生成给价计划
            if side == 'long':
                entry_price = current_price * (1 + rng.uniform(-0.005, 0.005))
                stop_loss = entry_price - atr * rng.uniform(1.5, 2.5)
                take_profit_1 = entry_price + atr * rng.uniform(0.8, 1.2)
                take_profit_2 = entry_price + atr * rng.uniform(2.0, 3.0)
            else:  # short
                entry_price = current_price * (1 + rng.uniform(-0.005, 0.005))
                stop_loss = entry_price + atr * rng.uniform(1.5, 2.5)
                take_profit_1 = entry_price - atr * rng.uniform(0.8, 1.2)
                take_profit_2 = entry_price - atr * rng.uniform(2.0, 3.0)

            # 创建信号记录
            signal = Signal(
                symbol=symbol,
                timestamp=signal_time,
                side=side,
                probability=probability,
                scores=scores,
                entry_price=entry_price,
                current_price=current_price,
                stop_loss=stop_loss,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
                is_prime=is_prime,
                is_watch=not is_prime and probability >= 0.58,
                dims_ok=dims_ok,
                base_probability=probability * 0.95,  # Mock base prob
                f_adjustment=rng.uniform(0.95, 1.05),
                status='open'
            )

            session.add(signal)
            created_count += 1

            emoji = "⭐" if is_prime else "👀"
            print(f"{emoji} Signal #{i+1}: {symbol} {side.upper()} @ {current_price:.4f} "
                  f"(Prob: {probability:.1%}, Dims: {dims_ok}/7)")

        except Exception as e:
            print(f"   ❌ Error generating signal for {symbol}: {e}")
            continue

        # 每10个信号提交一次
        if (i + 1) % 10 == 0:
            session.commit()

    # 最终提交
    session.commit()
    session.close()

    print()
    print(f"✅ Successfully created {created_count} test signals")
    print(f"   Prime signals: ~{int(created_count * 0.4)}")
    print(f"   Watch signals: ~{int(created_count * 0.3)}")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate test signals for backtest')

    # 时间范围
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--days', type=int, help='最近N天（默认30天）')
    time_group.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--signals', type=int, default=50, help='生成信号数量（默认50）')
    parser.add_argument('--seed', type=int, default=42, help='随机种子（默认42）')
    parser.add_argument('--real-prices', action='store_true', help='使用真实API价格（默认使用Mock）')

    args = parser.parse_args()

    # 处理时间范围
    if args.start:
        start_time = datetime.strptime(args.start, '%Y-%m-%d')
        if args.end:
            end_time = datetime.strptime(args.end, '%Y-%m-%d')
        else:
            end_time = datetime.utcnow()
    else:
        days = args.days or 30
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

    # 生成测试信号
    generate_test_signals(start_time, end_time, args.signals, args.seed, use_mock_prices=not args.real_prices)


if __name__ == '__main__':
    main()
