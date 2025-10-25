#!/usr/bin/env python3
# coding: utf-8
"""
历史信号生成器（用于回测）

基于历史K线数据生成交易信号，模拟完整的分析流程：
1. 加载历史价格数据
2. 计算技术指标
3. 评估趋势、动量等
4. 生成带有止盈止损的信号
5. 应用Prime/Watch标准

这个工具专门用于回测，使用缓存的历史数据而不依赖实时API。
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from random import Random

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.database.models import db, Signal


def load_historical_klines(symbol: str, start_time: datetime, end_time: datetime, cache_dir='data/backtest/cache'):
    """
    从缓存加载历史K线

    Returns:
        List of (timestamp, open, high, low, close, volume)
    """
    cache_path = Path(cache_dir)

    start_str = start_time.strftime('%Y%m%d')
    end_str = end_time.strftime('%Y%m%d')
    filename = f"{symbol}_1h_{start_str}_{end_str}.json"

    cache_file = cache_path / filename

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)

        # 转换回datetime对象
        bars = []
        for bar in data:
            timestamp = datetime.fromisoformat(bar[0])
            bars.append((timestamp, bar[1], bar[2], bar[3], bar[4], bar[5]))

        return bars

    except Exception as e:
        print(f"   ⚠️  Error loading {symbol}: {e}")
        return None


def calculate_simple_indicators(bars: List[tuple], lookback: int = 50) -> Dict:
    """
    计算简化的技术指标

    Args:
        bars: K线数据
        lookback: 回看周期

    Returns:
        指标字典
    """
    if len(bars) < lookback:
        return None

    # 提取价格
    closes = [b[4] for b in bars[-lookback:]]
    highs = [b[2] for b in bars[-lookback:]]
    lows = [b[3] for b in bars[-lookback:]]
    volumes = [b[5] for b in bars[-lookback:]]

    current_price = closes[-1]

    # 简单移动平均
    sma_20 = sum(closes[-20:]) / 20
    sma_50 = sum(closes) / len(closes)

    # 趋势判断
    trend_score = 0
    if current_price > sma_20 > sma_50:
        trend_score = 70 + (current_price / sma_20 - 1) * 1000
    elif current_price < sma_20 < sma_50:
        trend_score = 30 - (sma_20 / current_price - 1) * 1000

    trend_score = max(0, min(100, trend_score))

    # 动量（最近10根K线的变化）
    momentum = (closes[-1] / closes[-10] - 1) * 100
    momentum_score = 50 + momentum * 5
    momentum_score = max(0, min(100, momentum_score))

    # 波动率（简化的ATR）
    atr = sum(highs[i] - lows[i] for i in range(-20, 0)) / 20

    # 成交量趋势
    vol_recent = sum(volumes[-5:]) / 5
    vol_baseline = sum(volumes) / len(volumes)
    volume_score = 50 + (vol_recent / vol_baseline - 1) * 50
    volume_score = max(0, min(100, volume_score))

    # RSI简化版
    gains = []
    losses = []
    for i in range(1, 15):
        change = closes[-i] - closes[-i-1]
        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / 14 if gains else 0.01
    avg_loss = sum(losses) / 14 if losses else 0.01
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return {
        'current_price': current_price,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'atr': atr,
        'trend_score': trend_score,
        'momentum_score': momentum_score,
        'volume_score': volume_score,
        'rsi': rsi,
        'price_change_pct': (current_price / closes[0] - 1) * 100
    }


def generate_signal_from_indicators(symbol: str, timestamp: datetime, indicators: Dict, rng: Random) -> Optional[Dict]:
    """
    基于指标生成信号

    Args:
        symbol: 币种
        timestamp: 时间戳
        indicators: 技术指标
        rng: 随机数生成器

    Returns:
        信号字典或None
    """
    # 判断方向（降低阈值以产生更多信号）
    side = None
    if indicators['trend_score'] > 55 and indicators['momentum_score'] > 52:
        side = 'long'
    elif indicators['trend_score'] < 45 and indicators['momentum_score'] < 48:
        side = 'short'
    else:
        # 增加随机信号的概率（模拟真实市场）
        if rng.random() < 0.15:  # 15%概率生成信号
            side = 'long' if rng.random() > 0.5 else 'short'
        else:
            return None  # 没有明确信号

    # 生成7维分数（基于指标）
    scores = {
        'T': int(indicators['trend_score']),
        'M': int(indicators['momentum_score']),
        'C': int(55 + rng.uniform(-15, 15)),  # Mock CVD
        'S': int(55 + rng.uniform(-15, 15)),  # Mock结构
        'V': int(indicators['volume_score']),
        'O': int(55 + rng.uniform(-15, 15)),  # Mock OI
        'E': int(55 + rng.uniform(-10, 10)),  # Mock环境
    }

    # 计算概率（基于分数）
    avg_score = sum(scores.values()) / len(scores)
    probability = 0.45 + (avg_score - 50) / 100 * 0.35
    probability = max(0.45, min(0.85, probability))

    # 判断是否Prime
    dims_ok = sum(1 for score in scores.values() if score >= 65)
    is_prime = probability >= 0.62 and dims_ok >= 4

    # 如果概率太低，不发布
    if probability < 0.58:
        return None

    # 生成止盈止损
    current_price = indicators['current_price']
    atr = indicators['atr']

    if side == 'long':
        entry_price = current_price
        stop_loss = entry_price - atr * 1.8
        take_profit_1 = entry_price + atr * 0.9
        take_profit_2 = entry_price + atr * 2.4
    else:  # short
        entry_price = current_price
        stop_loss = entry_price + atr * 1.8
        take_profit_1 = entry_price - atr * 0.9
        take_profit_2 = entry_price - atr * 2.4

    return {
        'symbol': symbol,
        'timestamp': timestamp,
        'entry_time': timestamp,
        'side': side,
        'probability': probability,
        'scores': scores,
        'is_prime': is_prime,
        'dims_ok': dims_ok,
        'entry_price': entry_price,
        'current_price': current_price,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'tp1': take_profit_1,
        'take_profit_2': take_profit_2,
        'tp2': take_profit_2,
    }


def generate_historical_signals(
    symbols: List[str],
    start_time: datetime,
    end_time: datetime,
    scan_interval_hours: int = 1,
    seed: int = 42,
    save_to_db: bool = False
) -> List[Dict]:
    """
    生成历史信号

    Args:
        symbols: 币种列表
        start_time: 开始时间
        end_time: 结束时间
        scan_interval_hours: 扫描间隔
        seed: 随机种子
        save_to_db: 是否保存到数据库

    Returns:
        信号列表
    """
    rng = Random(seed)
    signals = []

    print(f"🔍 生成历史信号...")
    print(f"   时间范围: {start_time.date()} 到 {end_time.date()}")
    print(f"   币种数: {len(symbols)}")
    print(f"   扫描间隔: {scan_interval_hours}小时")
    print()

    # 预加载所有币种的K线数据
    klines_data = {}
    print("📊 加载历史K线数据...")
    for symbol in symbols:
        klines = load_historical_klines(symbol, start_time, end_time)
        if klines and len(klines) >= 50:
            klines_data[symbol] = klines
            print(f"   ✅ {symbol}: {len(klines)} bars")
        else:
            print(f"   ⚠️  {symbol}: 数据不足，跳过")

    print()

    if not klines_data:
        print("❌ 没有可用的K线数据")
        return []

    print(f"✅ 已加载 {len(klines_data)} 个币种的数据")
    print()

    # 逐小时扫描
    current_time = start_time
    scan_count = 0
    prime_count = 0
    watch_count = 0

    print("🔄 开始逐小时扫描...")
    print()

    while current_time <= end_time:
        scan_count += 1

        # 每24小时显示进度
        if scan_count % 24 == 1:
            print(f"⏰ {current_time.strftime('%Y-%m-%d %H:%M')} | 已生成: {len(signals)} (⭐{prime_count} + 👀{watch_count})")

        # 扫描每个币种
        for symbol in klines_data.keys():
            klines = klines_data[symbol]

            # 找到当前时间点对应的K线索引
            bar_index = None
            for i, bar in enumerate(klines):
                if bar[0] >= current_time:
                    bar_index = i
                    break

            if bar_index is None or bar_index < 50:
                continue  # 数据不足

            # 计算指标（使用到当前时间点的所有历史数据）
            indicators = calculate_simple_indicators(klines[:bar_index+1])

            if not indicators:
                continue

            # 生成信号
            signal = generate_signal_from_indicators(symbol, current_time, indicators, rng)

            if signal:
                signals.append(signal)

                if signal['is_prime']:
                    prime_count += 1
                else:
                    watch_count += 1

                # 显示前几个信号的详情
                if len(signals) <= 10:
                    emoji = "⭐" if signal['is_prime'] else "👀"
                    print(f"  {emoji} 信号#{len(signals)}: {symbol} {signal['side'].upper()} "
                          f"@ {signal['current_price']:.4f} (Prob: {signal['probability']:.1%}, Dims: {signal['dims_ok']}/7)")

        # 前进到下一个时间点
        current_time += timedelta(hours=scan_interval_hours)

    print()
    print(f"✅ 信号生成完成！")
    print(f"   总计: {len(signals)}")
    print(f"   ⭐ Prime: {prime_count} ({prime_count/max(1,len(signals))*100:.1f}%)")
    print(f"   👀 Watch: {watch_count} ({watch_count/max(1,len(signals))*100:.1f}%)")
    print()

    # 保存到数据库（可选）
    if save_to_db and signals:
        print("💾 保存信号到数据库...")
        session = db.get_session()

        for sig in signals:
            signal_obj = Signal(
                symbol=sig['symbol'],
                timestamp=sig['timestamp'],
                side=sig['side'],
                probability=sig['probability'],
                scores=sig['scores'],
                entry_price=sig['entry_price'],
                current_price=sig['current_price'],
                stop_loss=sig['stop_loss'],
                take_profit_1=sig['take_profit_1'],
                take_profit_2=sig['take_profit_2'],
                is_prime=sig['is_prime'],
                is_watch=not sig['is_prime'],
                dims_ok=sig['dims_ok'],
                status='open'
            )
            session.add(signal_obj)

        session.commit()
        session.close()
        print(f"✅ 已保存 {len(signals)} 个信号到数据库")
        print()

    return signals


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='生成历史回测信号')

    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--days', type=int, help='最近N天（默认7）')
    time_group.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbols', nargs='+', help='币种列表')
    parser.add_argument('--interval', type=int, default=1, help='扫描间隔（小时）')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')
    parser.add_argument('--save-db', action='store_true', help='保存到数据库')

    args = parser.parse_args()

    # 时间范围
    if args.start:
        start_time = datetime.strptime(args.start, '%Y-%m-%d')
        end_time = datetime.strptime(args.end, '%Y-%m-%d') if args.end else datetime.utcnow()
    else:
        days = args.days or 7
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

    # 币种列表
    if args.symbols:
        symbols = args.symbols
    else:
        # 默认前10个主流币
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
                   'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'MATICUSDT', 'LINKUSDT']

    # 生成信号
    signals = generate_historical_signals(
        symbols=symbols,
        start_time=start_time,
        end_time=end_time,
        scan_interval_hours=args.interval,
        seed=args.seed,
        save_to_db=args.save_db
    )

    print(f"📊 生成完成，可以运行回测：")
    print(f"   python3 tools/run_backtest.py --days {args.days or 7}")
    print()


if __name__ == '__main__':
    main()
