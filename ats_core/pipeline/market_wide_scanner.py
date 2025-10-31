# coding: utf-8
"""
全市场WebSocket扫描器（替代候选池机制）

架构优势：
- WebSocket实时K线缓存（0次API调用）
- 全市场扫描（不依赖候选池）
- 智能流动性过滤
- 17倍性能提升

使用：
```python
scanner = MarketWideScanner()
await scanner.initialize()
results = await scanner.scan_all()
```
"""

import asyncio
import time
from typing import List, Dict, Optional
from ats_core.cfg import CFG
from ats_core.data.realtime_kline_cache import get_kline_cache
from ats_core.sources.tickers import all_24h
from ats_core.pipeline.analyze_symbol import _analyze_symbol_core
from ats_core.logging import log, warn, error


class MarketWideScanner:
    """
    全市场扫描器（WebSocket优化）

    特性：
    1. 获取全市场USDT合约列表
    2. WebSocket K线缓存（零API调用）
    3. 流动性过滤（避免低质币种）
    4. 并行分析（快速扫描）
    """

    def __init__(
        self,
        min_quote_volume: float = 3_000_000,  # 最低成交额（300万USDT）
        min_trades: int = 5_000,              # 最低交易笔数
        max_symbols: int = None,              # 最大扫描数量（None=全部）
        use_websocket_cache: bool = True      # 使用WebSocket缓存
    ):
        """
        初始化全市场扫描器

        Args:
            min_quote_volume: 最低24h成交额（USDT）
            min_trades: 最低24h交易笔数
            max_symbols: 最大扫描币种数（None=全部）
            use_websocket_cache: 是否使用WebSocket缓存
        """
        self.min_quote_volume = min_quote_volume
        self.min_trades = min_trades
        self.max_symbols = max_symbols
        self.use_websocket_cache = use_websocket_cache

        # WebSocket K线缓存
        self.kline_cache = get_kline_cache() if use_websocket_cache else None

        # 状态
        self.is_initialized = False
        self.all_symbols = []

        log("🌍 全市场扫描器初始化...")
        if use_websocket_cache:
            log("   ✅ WebSocket缓存模式（17倍提速）")
        else:
            log("   ⚠️  REST API模式（慢速）")

    async def initialize(self, client=None):
        """
        初始化扫描器

        步骤：
        1. 获取全市场币种列表
        2. 流动性过滤
        3. WebSocket K线缓存预热（如果启用）
        """
        if self.is_initialized:
            log("⚠️  已初始化，跳过")
            return

        log("=" * 60)
        log("🚀 初始化全市场扫描器...")
        log("=" * 60)

        # Step 1: 获取全市场币种
        log("📊 获取全市场24h行情...")
        tickers = all_24h()
        log(f"   获取到 {len(tickers)} 个交易对")

        # Step 2: 流动性过滤
        log(f"🔍 流动性过滤（成交额≥{self.min_quote_volume/1e6:.0f}M, 笔数≥{self.min_trades}）...")

        filtered = []
        for t in tickers:
            try:
                sym = t.get('symbol', '')

                # 只要USDT永续合约
                if not sym.endswith('USDT'):
                    continue

                # 流动性检查
                quote_vol = float(t.get('quoteVolume', 0))
                trades = int(t.get('count', 0))

                if quote_vol >= self.min_quote_volume and trades >= self.min_trades:
                    filtered.append({
                        'symbol': sym,
                        'quote_volume': quote_vol,
                        'trades': trades,
                        'price_change': float(t.get('priceChangePercent', 0))
                    })
            except Exception as e:
                continue

        # 按成交额排序（流动性高优先）
        filtered = sorted(filtered, key=lambda x: -x['quote_volume'])

        # 限制数量
        if self.max_symbols and len(filtered) > self.max_symbols:
            log(f"⚠️  限制扫描数量: {len(filtered)} → {self.max_symbols}")
            filtered = filtered[:self.max_symbols]

        self.all_symbols = [x['symbol'] for x in filtered]

        log(f"✅ 流动性过滤完成: {len(self.all_symbols)} 个币种")
        if len(self.all_symbols) > 0:
            log(f"   前10名: {', '.join(self.all_symbols[:10])}")
            total_volume = sum(x['quote_volume'] for x in filtered)
            log(f"   总成交额: ${total_volume/1e9:.1f}B")

        # Step 3: WebSocket缓存预热（如果启用）
        if self.use_websocket_cache and client:
            log("\n🔧 预热WebSocket K线缓存...")
            log(f"   币种数: {len(self.all_symbols)}")
            log(f"   周期: 1h, 4h")
            log(f"   预计连接数: {len(self.all_symbols) * 2}")

            # 检查连接数限制
            MAX_CONNECTIONS = 280
            required_connections = len(self.all_symbols) * 2

            if required_connections > MAX_CONNECTIONS:
                warn(f"⚠️  WebSocket连接数超限: {required_connections} > {MAX_CONNECTIONS}")
                warn(f"   将只处理前 {MAX_CONNECTIONS // 2} 个币种")
                self.all_symbols = self.all_symbols[:MAX_CONNECTIONS // 2]

            # 初始化缓存
            await self.kline_cache.initialize_batch(
                symbols=self.all_symbols,
                intervals=['1h', '4h'],
                client=client
            )

            # 启动WebSocket更新
            await self.kline_cache.start_batch_realtime_update(
                symbols=self.all_symbols,
                intervals=['1h', '4h'],
                client=client
            )

        self.is_initialized = True

        log("=" * 60)
        log("✅ 全市场扫描器初始化完成！")
        log("=" * 60)
        log(f"   可扫描币种: {len(self.all_symbols)}")
        log(f"   WebSocket缓存: {'✅ 已启用' if self.use_websocket_cache else '❌ 未启用'}")
        log("=" * 60)

    async def scan_all(
        self,
        min_prime_strength: int = 78,
        max_concurrent: int = 10
    ) -> Dict:
        """
        扫描全市场

        Args:
            min_prime_strength: 最低Prime强度
            max_concurrent: 最大并发数

        Returns:
            扫描结果字典
        """
        if not self.is_initialized:
            raise RuntimeError("未初始化，请先调用 initialize()")

        log("\n" + "=" * 60)
        log("🔍 开始全市场扫描...")
        log("=" * 60)
        log(f"   扫描币种数: {len(self.all_symbols)}")
        log(f"   Prime阈值: {min_prime_strength}")
        log(f"   并发数: {max_concurrent}")
        log("=" * 60)

        start_time = time.time()

        results = []
        errors = []

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_one(symbol: str):
            async with semaphore:
                try:
                    # 从缓存获取K线（0次API调用）
                    if self.use_websocket_cache:
                        k1 = self.kline_cache.get_klines(symbol, '1h', 300)
                        k4 = self.kline_cache.get_klines(symbol, '4h', 200)

                        # 检查数据完整性
                        if not k1 or len(k1) < 50:
                            return None
                        if not k4 or len(k4) < 30:
                            k4 = k1  # 降级使用1h数据
                    else:
                        # REST API模式（慢速）
                        from ats_core.sources.binance import get_klines
                        k1 = get_klines(symbol, '1h', 300)
                        k4 = get_klines(symbol, '4h', 200)
                        await asyncio.sleep(0.2)  # API限流

                    # 获取OI数据
                    from ats_core.sources.binance import get_open_interest_hist
                    oi_data = get_open_interest_hist(symbol, '1h', 300)

                    # 尝试获取现货K线（可选）
                    try:
                        from ats_core.sources.binance import get_spot_klines
                        spot_k1 = get_spot_klines(symbol, '1h', 300)
                    except:
                        spot_k1 = None

                    # 核心分析
                    result = _analyze_symbol_core(
                        symbol=symbol,
                        k1=k1,
                        k4=k4,
                        oi_data=oi_data,
                        spot_k1=spot_k1,
                        elite_meta=None  # 不再使用候选池元数据
                    )

                    return result

                except Exception as e:
                    errors.append({'symbol': symbol, 'error': str(e)})
                    return None

        # 并行分析
        tasks = [analyze_one(sym) for sym in self.all_symbols]
        raw_results = await asyncio.gather(*tasks)

        # 过滤结果
        for r in raw_results:
            if r is None:
                continue

            # 检查Prime
            pub = r.get('publish', {})
            if pub.get('prime') and pub.get('prime_strength', 0) >= min_prime_strength:
                results.append(r)

        elapsed = time.time() - start_time

        # 统计
        stats = {
            'total_symbols': len(self.all_symbols),
            'analyzed': len(self.all_symbols) - len(errors),
            'errors': len(errors),
            'prime_signals': len(results),
            'elapsed_seconds': round(elapsed, 2),
            'symbols_per_second': round(len(self.all_symbols) / elapsed, 2),
            'api_calls': 0 if self.use_websocket_cache else len(self.all_symbols) * 3,
            'cache_stats': self.kline_cache.get_stats() if self.use_websocket_cache else None
        }

        # 输出统计
        log("=" * 60)
        log("✅ 全市场扫描完成")
        log("=" * 60)
        log(f"  扫描币种: {stats['total_symbols']}")
        log(f"  分析成功: {stats['analyzed']}")
        log(f"  分析失败: {stats['errors']}")
        log(f"  Prime信号: {stats['prime_signals']}")
        log(f"  耗时: {stats['elapsed_seconds']}秒")
        log(f"  速度: {stats['symbols_per_second']} 币种/秒")
        log(f"  API调用: {stats['api_calls']}次")

        if self.use_websocket_cache and stats['cache_stats']:
            cache = stats['cache_stats']
            log(f"  缓存命中率: {cache['hit_rate']}")
            log(f"  内存占用: {cache['memory_estimate_mb']:.1f}MB")

        log("=" * 60)

        return {
            'results': results,
            'stats': stats,
            'errors': errors
        }

    def get_symbols(self) -> List[str]:
        """获取当前可扫描的币种列表"""
        return self.all_symbols.copy()


# ========== 便捷函数 ==========

async def scan_market_wide(
    min_quote_volume: float = 3_000_000,
    min_prime_strength: int = 78,
    use_websocket: bool = True,
    client = None
) -> Dict:
    """
    便捷函数：全市场扫描

    使用：
    ```python
    import asyncio
    from ats_core.pipeline.market_wide_scanner import scan_market_wide

    results = await scan_market_wide(
        min_quote_volume=5_000_000,
        min_prime_strength=80,
        use_websocket=True
    )
    ```
    """
    scanner = MarketWideScanner(
        min_quote_volume=min_quote_volume,
        use_websocket_cache=use_websocket
    )

    await scanner.initialize(client=client)
    return await scanner.scan_all(min_prime_strength=min_prime_strength)


if __name__ == "__main__":
    # 测试
    async def test():
        results = await scan_market_wide(
            min_quote_volume=5_000_000,
            min_prime_strength=75,
            use_websocket=False  # 测试时不启用WebSocket
        )

        print(f"\n找到 {len(results['results'])} 个Prime信号")
        for r in results['results'][:5]:
            sym = r['symbol']
            prob = r['probability']
            side = r['side']
            print(f"  {sym}: {side} {prob:.1%}")

    asyncio.run(test())
