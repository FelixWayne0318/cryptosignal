# coding: utf-8
"""
回测数据加载器

功能：
1. 从数据库加载历史信号
2. 从币安API获取历史K线数据
3. 缓存数据以提高回测速度
"""
import os
import sys
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.sources.binance_safe import get_klines


class BacktestDataLoader:
    """
    回测数据加载器

    提供回测所需的所有数据：
    - 历史信号（从数据库）
    - 历史价格（从API或缓存）
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        初始化数据加载器

        Args:
            cache_dir: 缓存目录（默认data/backtest/cache）
        """
        if cache_dir is None:
            project_root = Path(__file__).parent.parent
            cache_dir = project_root / "data" / "backtest" / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_signals_from_database(
        self,
        start_time: datetime,
        end_time: datetime,
        symbols: Optional[List[str]] = None,
        min_probability: Optional[float] = None
    ) -> List[Dict]:
        """
        从数据库加载历史信号

        Args:
            start_time: 开始时间
            end_time: 结束时间
            symbols: 币种过滤（可选）
            min_probability: 最小概率过滤（可选）

        Returns:
            信号列表
        """
        try:
            from ats_core.database.models import db, Signal
            from sqlalchemy import and_

            session = db.get_session()

            # 构建查询
            query = session.query(Signal).filter(
                and_(
                    Signal.timestamp >= start_time,
                    Signal.timestamp <= end_time
                )
            )

            # 币种过滤
            if symbols:
                query = query.filter(Signal.symbol.in_(symbols))

            # 概率过滤
            if min_probability:
                query = query.filter(Signal.probability >= min_probability)

            # 执行查询
            db_signals = query.order_by(Signal.timestamp).all()

            # 转换为字典格式
            signals = []
            for s in db_signals:
                signals.append({
                    'id': s.id,
                    'symbol': s.symbol,
                    'timestamp': s.timestamp,
                    'entry_time': s.timestamp,
                    'side': s.side,
                    'entry_price': s.entry_price or s.current_price,
                    'current_price': s.current_price,
                    'stop_loss': s.stop_loss,
                    'sl': s.stop_loss,
                    'take_profit_1': s.take_profit_1,
                    'tp1': s.take_profit_1,
                    'take_profit_2': s.take_profit_2,
                    'tp2': s.take_profit_2,
                    'probability': s.probability,
                    'scores': s.scores,
                    'is_prime': s.is_prime,
                })

            session.close()

            print(f"✅ Loaded {len(signals)} signals from database")
            return signals

        except ImportError:
            print("⚠️  Database not available, cannot load signals")
            return []
        except Exception as e:
            print(f"❌ Failed to load signals from database: {e}")
            import traceback
            traceback.print_exc()
            return []

    def load_price_data(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        interval: str = '1h',
        use_cache: bool = True
    ) -> Dict[str, List]:
        """
        加载价格数据

        Args:
            symbols: 币种列表
            start_time: 开始时间
            end_time: 结束时间
            interval: K线周期
            use_cache: 是否使用缓存

        Returns:
            价格数据字典 {symbol: [(timestamp, open, high, low, close, volume), ...]}
        """
        price_data = {}

        for symbol in symbols:
            print(f"📊 Loading price data for {symbol}...")

            # 检查缓存
            if use_cache:
                cached = self._load_from_cache(symbol, start_time, end_time, interval)
                if cached:
                    price_data[symbol] = cached
                    print(f"   ✅ Loaded from cache ({len(cached)} bars)")
                    continue

            # 从API获取
            try:
                start_ms = int(start_time.timestamp() * 1000)
                end_ms = int(end_time.timestamp() * 1000)

                klines = get_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=1500,
                    start_time=start_ms,
                    end_time=end_ms
                )

                if klines:
                    # 转换为简化格式：(timestamp_datetime, open, high, low, close, volume)
                    bars = []
                    for k in klines:
                        timestamp = datetime.fromtimestamp(int(k[0]) / 1000)
                        open_price = float(k[1])
                        high = float(k[2])
                        low = float(k[3])
                        close = float(k[4])
                        volume = float(k[5])

                        bars.append((timestamp, open_price, high, low, close, volume))

                    price_data[symbol] = bars

                    # 保存到缓存
                    if use_cache:
                        self._save_to_cache(symbol, start_time, end_time, interval, bars)

                    print(f"   ✅ Loaded from API ({len(bars)} bars)")
                else:
                    print(f"   ⚠️  No data returned from API")

            except Exception as e:
                print(f"   ❌ Failed to load: {e}")

        return price_data

    def _get_cache_filename(self, symbol: str, start_time: datetime, end_time: datetime, interval: str) -> Path:
        """
        获取缓存文件名

        Args:
            symbol: 币种
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期

        Returns:
            缓存文件路径
        """
        start_str = start_time.strftime('%Y%m%d')
        end_str = end_time.strftime('%Y%m%d')
        filename = f"{symbol}_{interval}_{start_str}_{end_str}.json"
        return self.cache_dir / filename

    def _load_from_cache(self, symbol: str, start_time: datetime, end_time: datetime, interval: str) -> Optional[List]:
        """
        从缓存加载数据

        Args:
            symbol: 币种
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期

        Returns:
            价格数据或None
        """
        cache_file = self._get_cache_filename(symbol, start_time, end_time, interval)

        if not cache_file.exists():
            return None

        try:
            # 尝试检测是否为 gzip 压缩文件
            import gzip

            # 读取前两个字节检测是否为 gzip 文件（魔术字节：0x1f 0x8b）
            with open(cache_file, 'rb') as f:
                magic = f.read(2)

            if magic == b'\x1f\x8b':
                # gzip 压缩文件
                with gzip.open(cache_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # 普通 JSON 文件
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # 转换回datetime对象
            bars = []
            for bar in data:
                timestamp = datetime.fromisoformat(bar[0])
                bars.append((timestamp, bar[1], bar[2], bar[3], bar[4], bar[5]))

            return bars

        except Exception as e:
            print(f"   ⚠️  Cache read error: {e}, deleting corrupted cache file")
            # 删除损坏的缓存文件
            try:
                cache_file.unlink()
            except:
                pass
            return None

    def _save_to_cache(self, symbol: str, start_time: datetime, end_time: datetime, interval: str, bars: List):
        """
        保存数据到缓存

        Args:
            symbol: 币种
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期
            bars: 价格数据
        """
        cache_file = self._get_cache_filename(symbol, start_time, end_time, interval)

        try:
            # 转换datetime为字符串
            data = []
            for bar in bars:
                timestamp_str = bar[0].isoformat()
                data.append([timestamp_str, bar[1], bar[2], bar[3], bar[4], bar[5]])

            with open(cache_file, 'w') as f:
                json.dump(data, f)

        except Exception as e:
            print(f"   ⚠️  Cache write error: {e}")

    def prepare_backtest_data(
        self,
        start_time: datetime,
        end_time: datetime,
        symbols: Optional[List[str]] = None,
        min_probability: Optional[float] = None,
        use_cache: bool = True
    ) -> tuple:
        """
        准备回测所需的所有数据

        Args:
            start_time: 回测开始时间
            end_time: 回测结束时间
            symbols: 币种过滤（可选，如果不指定则从信号中提取）
            min_probability: 最小概率过滤
            use_cache: 是否使用缓存

        Returns:
            (signals, price_data) 元组
        """
        print("="*70)
        print("  Preparing Backtest Data")
        print("="*70)
        print(f"Period: {start_time.date()} to {end_time.date()}")
        print()

        # 1. 加载历史信号
        signals = self.load_signals_from_database(
            start_time=start_time,
            end_time=end_time,
            symbols=symbols,
            min_probability=min_probability
        )

        if not signals:
            print("\n⚠️  No signals found for this period")
            return signals, {}

        # 2. 提取需要的币种（如果未指定）
        if not symbols:
            symbols = list(set(s['symbol'] for s in signals))
            print(f"\n📊 Extracted {len(symbols)} unique symbols from signals")

        # 3. 加载价格数据
        print(f"\n📈 Loading price data for {len(symbols)} symbols...")
        price_data = self.load_price_data(
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            interval='1h',
            use_cache=use_cache
        )

        print()
        print("="*70)
        print(f"✅ Data preparation completed")
        print(f"   Signals: {len(signals)}")
        print(f"   Symbols: {len(price_data)}")
        print("="*70)
        print()

        return signals, price_data
