#!/usr/bin/env python3
# coding: utf-8
"""
Mock价格数据生成器

用于生成模拟的历史K线数据，供回测系统使用（当Binance API不可用时）

功能：
1. 生成逼真的OHLCV数据
2. 包含随机波动和趋势
3. 可配置价格范围和波动率
4. 保存为缓存格式供回测加载

用法：
    python3 tools/generate_mock_price_data.py --symbols BTCUSDT ETHUSDT --days 30
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from random import Random

# Mock price ranges
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


def generate_mock_klines(symbol, start_time, end_time, interval='1h', seed=42):
    """
    生成模拟K线数据

    Args:
        symbol: 币种
        start_time: 开始时间
        end_time: 结束时间
        interval: 周期（仅支持1h）
        seed: 随机种子

    Returns:
        K线数据列表 [(timestamp, open, high, low, close, volume), ...]
    """
    rng = Random(seed + hash(symbol))

    # 获取价格范围
    price_range = MOCK_PRICES.get(symbol, (100, 200))
    base_price = (price_range[0] + price_range[1]) / 2

    # 计算时间跨度
    hours = int((end_time - start_time).total_seconds() / 3600) + 1

    # 生成K线
    bars = []
    current_price = base_price * rng.uniform(0.95, 1.05)

    for i in range(hours):
        bar_time = start_time + timedelta(hours=i)

        # 随机走势（趋势 + 随机）
        trend = rng.uniform(-0.005, 0.005)  # ±0.5%趋势
        volatility = rng.uniform(0.01, 0.03)  # 1-3%波动

        # OHLC
        open_price = current_price
        change = base_price * (trend + rng.uniform(-volatility, volatility))
        close_price = max(open_price + change, price_range[0] * 0.8)  # 不低于下限
        close_price = min(close_price, price_range[1] * 1.2)  # 不超过上限

        # High/Low
        high = max(open_price, close_price) * rng.uniform(1.001, 1.02)
        low = min(open_price, close_price) * rng.uniform(0.98, 0.999)

        # Volume（模拟）
        base_volume = 1000000 if 'BTC' in symbol or 'ETH' in symbol else 10000
        volume = base_volume * rng.uniform(0.5, 2.0)

        bars.append((bar_time, open_price, high, low, close_price, volume))

        # 更新当前价格
        current_price = close_price

    return bars


def save_to_backtest_cache(symbol, start_time, end_time, bars, cache_dir='data/backtest/cache'):
    """
    保存到回测缓存目录

    Args:
        symbol: 币种
        start_time: 开始时间
        end_time: 结束时间
        bars: K线数据
        cache_dir: 缓存目录
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    # 生成缓存文件名（与BacktestDataLoader格式一致）
    start_str = start_time.strftime('%Y%m%d')
    end_str = end_time.strftime('%Y%m%d')
    filename = f"{symbol}_1h_{start_str}_{end_str}.json"

    cache_file = cache_path / filename

    # 转换为JSON格式
    data = []
    for bar in bars:
        timestamp_str = bar[0].isoformat()
        data.append([timestamp_str, bar[1], bar[2], bar[3], bar[4], bar[5]])

    # 保存
    with open(cache_file, 'w') as f:
        json.dump(data, f)

    print(f"   💾 Saved {len(bars)} bars to {filename}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate mock price data for backtest')

    # 时间范围
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--days', type=int, help='最近N天（默认30天）')
    time_group.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbols', nargs='+', help='币种列表（默认全部）')
    parser.add_argument('--seed', type=int, default=42, help='随机种子（默认42）')

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

    # 处理币种列表
    symbols = args.symbols if args.symbols else list(MOCK_PRICES.keys())

    print("🔄 Generating mock price data...")
    print(f"   Period: {start_time.date()} to {end_time.date()}")
    print(f"   Symbols: {len(symbols)}")
    print()

    for symbol in symbols:
        print(f"📊 Generating {symbol}...")

        # 生成K线
        bars = generate_mock_klines(symbol, start_time, end_time, seed=args.seed)

        # 保存到缓存
        save_to_backtest_cache(symbol, start_time, end_time, bars)

    print()
    print(f"✅ Successfully generated mock data for {len(symbols)} symbols")
    print(f"   Cache location: data/backtest/cache/")
    print()


if __name__ == '__main__':
    main()
