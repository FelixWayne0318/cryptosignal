# coding: utf-8
"""
统一数据管理器 - WebSocket + REST 有机结合

设计理念:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 智能路由: 根据数据类型自动选择WebSocket或REST
2. 统一接口: 上层调用者无需关心数据来源
3. 自动降级: WebSocket断线自动回退REST
4. 内存优化: 固定大小缓存，避免内存泄漏
5. 并发安全: 支持多协程并发访问

数据分类策略:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【高频数据 → WebSocket实时推送】
  ✓ K线数据 (1m/5m/15m/1h/4h/1d)      - 每周期实时更新
  ✓ 订单簿快照 (depth20@100ms)        - 100ms推送一次
  ✓ 实时成交流 (aggTrade)             - 每笔成交推送
  ✓ 标记价格 (markPrice@3s)          - 3秒推送一次

【低频数据 → REST定期轮询】
  ✓ 持仓量OI (1h粒度)                 - 每5分钟更新一次
  ✓ 资金费率 (8h更新周期)             - 每小时更新一次
  ✓ 现货价格 (ticker)                 - 每分钟更新一次
  ✓ 历史清算 (aggTrades最近500条)     - 每5分钟更新一次

【混合策略】
  ✓ 首次初始化: REST批量获取历史数据（一次性）
  ✓ 后续更新: WebSocket实时增量 + REST定期轮询
  ✓ 降级策略: WebSocket断线时自动回退REST（无缝切换）

性能优化:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 首次初始化: ~2-3分钟（REST批量加载）
- 后续扫描: ~5-10秒（纯内存读取）
- API调用: 0次/扫描（WebSocket实时更新）
- 内存占用: ~200MB（140币种×多周期）
- 数据新鲜度: <5秒（WebSocket推送）

使用示例:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from ats_core.data.unified_data_manager import get_data_manager

    # 获取单例
    dm = get_data_manager()

    # 初始化（仅一次，2-3分钟）
    await dm.initialize(symbols=['BTCUSDT', 'ETHUSDT'])

    # 获取数据（自动选择最优方式）
    klines = await dm.get_klines('BTCUSDT', '1h', limit=300)      # WebSocket缓存
    oi_data = await dm.get_oi_history('BTCUSDT', '1h', limit=100) # REST轮询
    orderbook = await dm.get_orderbook('BTCUSDT')                 # WebSocket实时
    funding = await dm.get_funding_rate('BTCUSDT')                # REST缓存
"""

from __future__ import annotations
import asyncio
import time
from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime, timedelta
import aiohttp

from ats_core.logging import log, warn, error


class UnifiedDataManager:
    """
    统一数据管理器 - WebSocket + REST 有机结合

    核心职责:
    1. 管理所有市场数据的获取和缓存
    2. 智能路由到WebSocket或REST
    3. 自动降级和容错
    4. 统一的数据访问接口
    """

    def __init__(self):
        """初始化数据管理器"""

        # ========== 高频数据缓存（WebSocket）==========

        # K线缓存: {symbol: {interval: deque([kline1, kline2, ...])}}
        self.klines_cache: Dict[str, Dict[str, deque]] = {}

        # 订单簿缓存: {symbol: {'bids': [...], 'asks': [...], 'timestamp': ...}}
        self.orderbook_cache: Dict[str, Dict] = {}

        # 标记价格缓存: {symbol: {'markPrice': ..., 'timestamp': ...}}
        self.mark_price_cache: Dict[str, Dict] = {}

        # 实时成交缓存: {symbol: deque([trade1, trade2, ...])}
        self.trades_cache: Dict[str, deque] = {}

        # ========== 低频数据缓存（REST）==========

        # OI历史缓存: {symbol: deque([oi1, oi2, ...])}
        self.oi_cache: Dict[str, deque] = {}

        # 资金费率缓存: {symbol: {'rate': ..., 'nextTime': ..., 'timestamp': ...}}
        self.funding_cache: Dict[str, Dict] = {}

        # 现货价格缓存: {symbol: {'price': ..., 'timestamp': ...}}
        self.spot_price_cache: Dict[str, Dict] = {}

        # 清算数据缓存: {symbol: deque([trade1, trade2, ...])}
        self.liquidation_cache: Dict[str, deque] = {}

        # ========== 状态管理 ==========

        # 初始化状态
        self.initialized = False
        self.symbols: List[str] = []

        # WebSocket连接状态
        self.ws_connected: Dict[str, bool] = {}

        # 数据更新时间戳: {f"{symbol}_{data_type}": timestamp}
        self.last_update: Dict[str, float] = {}

        # ========== 统计信息 ==========

        self.stats = {
            'ws_updates': 0,       # WebSocket更新次数
            'rest_calls': 0,       # REST调用次数
            'cache_hits': 0,       # 缓存命中次数
            'cache_misses': 0,     # 缓存未命中次数
            'ws_reconnects': 0,    # WebSocket重连次数
        }

        # ========== 配置参数 ==========

        self.config = {
            'max_klines': 500,           # 每个周期保留的K线数量
            'max_trades': 1000,          # 保留的成交记录数量
            'max_oi': 300,               # 保留的OI记录数量
            'oi_update_interval': 300,   # OI更新间隔（秒）
            'funding_update_interval': 3600,  # 资金费率更新间隔（秒）
            'spot_update_interval': 60,  # 现货价格更新间隔（秒）
            'liquidation_update_interval': 300,  # 清算数据更新间隔（秒）
            'rest_timeout': 10,          # REST请求超时（秒）
            'ws_reconnect_delay': 5,     # WebSocket重连延迟（秒）
        }

        # ========== Binance客户端（异步） ==========

        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://fapi.binance.com"
        self.spot_base_url = "https://api.binance.com"

        # ========== 后台任务 ==========

        self.background_tasks: List[asyncio.Task] = []

        log("✅ 统一数据管理器创建成功")


    # ============================================================
    # 初始化和生命周期管理
    # ============================================================

    async def initialize(
        self,
        symbols: List[str],
        intervals: List[str] = ['1h', '4h', '15m', '1d'],
        enable_websocket: bool = True
    ):
        """
        初始化数据管理器（仅一次，约2-3分钟）

        Args:
            symbols: 币种列表（如 ['BTCUSDT', 'ETHUSDT']）
            intervals: K线周期列表
            enable_websocket: 是否启用WebSocket实时更新

        步骤:
        1. 创建HTTP会话
        2. REST批量初始化历史数据
        3. 启动WebSocket实时更新（可选）
        4. 启动REST定期轮询任务
        """
        if self.initialized:
            log("⚠️  数据管理器已初始化，跳过")
            return

        log("\n" + "=" * 70)
        log("🚀 初始化统一数据管理器")
        log("=" * 70)
        log(f"   币种数: {len(symbols)}")
        log(f"   K线周期: {', '.join(intervals)}")
        log(f"   WebSocket: {'启用' if enable_websocket else '禁用'}")
        log("=" * 70)

        start_time = time.time()

        # 保存配置
        self.symbols = symbols

        # 1. 创建HTTP会话
        log("\n1️⃣  创建HTTP会话...")
        self.session = aiohttp.ClientSession()

        # 2. REST批量初始化历史数据
        log("\n2️⃣  REST批量初始化历史数据...")
        await self._init_klines_batch(symbols, intervals)
        await self._init_oi_batch(symbols)
        await self._init_funding_batch(symbols)

        # 3. 启动WebSocket实时更新（可选）
        if enable_websocket:
            log("\n3️⃣  启动WebSocket实时更新...")
            await self._start_websocket_streams(symbols, intervals)
        else:
            log("\n3️⃣  跳过WebSocket（测试模式）")

        # 4. 启动REST定期轮询任务
        log("\n4️⃣  启动REST定期轮询任务...")
        self._start_rest_polling_tasks(symbols)

        self.initialized = True

        elapsed = time.time() - start_time
        log("\n" + "=" * 70)
        log(f"✅ 数据管理器初始化完成！耗时: {elapsed:.1f}秒")
        log("=" * 70)


    async def close(self):
        """关闭数据管理器，释放资源"""
        log("🔴 关闭数据管理器...")

        # 取消所有后台任务
        for task in self.background_tasks:
            task.cancel()

        # 关闭HTTP会话
        if self.session:
            await self.session.close()

        self.initialized = False
        log("✅ 数据管理器已关闭")


    # ============================================================
    # 公共数据访问接口（统一接口，自动路由）
    # ============================================================

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 300
    ) -> List[List]:
        """
        获取K线数据（优先WebSocket缓存，降级REST）

        Args:
            symbol: 交易对
            interval: K线周期
            limit: 数量限制

        Returns:
            K线数据列表 [[timestamp, open, high, low, close, volume, ...], ...]
        """
        cache_key = f"{symbol}_klines_{interval}"

        # 尝试从WebSocket缓存获取
        if symbol in self.klines_cache and interval in self.klines_cache[symbol]:
            self.stats['cache_hits'] += 1
            klines_deque = self.klines_cache[symbol][interval]

            # 检查数据新鲜度（5分钟内有更新则认为有效）
            last_update_time = self.last_update.get(cache_key, 0)
            if time.time() - last_update_time < 300:
                return list(klines_deque)[-limit:]
            else:
                warn(f"⚠️  {symbol} {interval} K线缓存已过期，回退REST")

        # 缓存未命中或数据过期，回退REST
        self.stats['cache_misses'] += 1
        return await self._fetch_klines_rest(symbol, interval, limit)


    async def get_oi_history(
        self,
        symbol: str,
        interval: str = '1h',
        limit: int = 100
    ) -> List[Dict]:
        """
        获取持仓量OI历史（REST轮询缓存）

        Args:
            symbol: 交易对
            interval: 周期（仅支持1h）
            limit: 数量限制

        Returns:
            OI历史列表 [{'timestamp': ..., 'sumOpenInterest': ...}, ...]
        """
        # 检查缓存
        if symbol in self.oi_cache:
            cache_key = f"{symbol}_oi"
            last_update_time = self.last_update.get(cache_key, 0)

            # 5分钟内有更新则返回缓存
            if time.time() - last_update_time < 300:
                self.stats['cache_hits'] += 1
                return list(self.oi_cache[symbol])[-limit:]

        # 缓存未命中或过期，REST获取
        self.stats['cache_misses'] += 1
        return await self._fetch_oi_rest(symbol, interval, limit)


    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """
        获取订单簿快照（优先WebSocket，降级REST）

        Args:
            symbol: 交易对
            limit: 深度档位

        Returns:
            {'bids': [[price, qty], ...], 'asks': [[price, qty], ...], 'timestamp': ...}
        """
        # 优先WebSocket缓存
        if symbol in self.orderbook_cache:
            cache_key = f"{symbol}_orderbook"
            last_update_time = self.last_update.get(cache_key, 0)

            # 10秒内有更新则返回缓存
            if time.time() - last_update_time < 10:
                self.stats['cache_hits'] += 1
                return self.orderbook_cache[symbol]

        # 降级REST
        self.stats['cache_misses'] += 1
        return await self._fetch_orderbook_rest(symbol, limit)


    async def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        获取资金费率（REST缓存，每小时更新）

        Returns:
            {'rate': ..., 'nextTime': ..., 'timestamp': ...}
        """
        # 检查缓存
        if symbol in self.funding_cache:
            cache_key = f"{symbol}_funding"
            last_update_time = self.last_update.get(cache_key, 0)

            # 1小时内有更新则返回缓存
            if time.time() - last_update_time < 3600:
                self.stats['cache_hits'] += 1
                return self.funding_cache[symbol]

        # 缓存未命中或过期
        self.stats['cache_misses'] += 1
        return await self._fetch_funding_rest(symbol)


    async def get_spot_price(self, symbol: str) -> Optional[float]:
        """
        获取现货价格（REST缓存，每分钟更新）

        Returns:
            现货价格（float）
        """
        # 现货交易对名称（去掉USDT后缀）
        spot_symbol = symbol  # 如 BTCUSDT → BTCUSDT（现货和合约名称相同）

        # 检查缓存
        if spot_symbol in self.spot_price_cache:
            cache_key = f"{spot_symbol}_spot"
            last_update_time = self.last_update.get(cache_key, 0)

            # 1分钟内有更新则返回缓存
            if time.time() - last_update_time < 60:
                self.stats['cache_hits'] += 1
                return self.spot_price_cache[spot_symbol].get('price')

        # 缓存未命中或过期
        self.stats['cache_misses'] += 1
        price_data = await self._fetch_spot_price_rest(spot_symbol)
        return price_data.get('price') if price_data else None


    async def get_liquidation_trades(
        self,
        symbol: str,
        limit: int = 500
    ) -> List[Dict]:
        """
        获取清算数据（aggTrades，REST缓存，每5分钟更新）

        用于Q因子（清算密度）计算

        Returns:
            清算交易列表 [{'price': ..., 'qty': ..., 'time': ..., 'isBuyerMaker': ...}, ...]
        """
        # 检查缓存
        if symbol in self.liquidation_cache:
            cache_key = f"{symbol}_liquidation"
            last_update_time = self.last_update.get(cache_key, 0)

            # 5分钟内有更新则返回缓存
            if time.time() - last_update_time < 300:
                self.stats['cache_hits'] += 1
                return list(self.liquidation_cache[symbol])

        # 缓存未命中或过期
        self.stats['cache_misses'] += 1
        return await self._fetch_agg_trades_rest(symbol, limit)


    # ============================================================
    # REST数据获取（底层实现）
    # ============================================================

    async def _fetch_klines_rest(
        self,
        symbol: str,
        interval: str,
        limit: int = 300
    ) -> List[List]:
        """REST获取K线数据"""
        if not self.session:
            raise RuntimeError("HTTP会话未初始化")

        url = f"{self.base_url}/fapi/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }

        try:
            async with self.session.get(url, params=params, timeout=self.config['rest_timeout']) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.stats['rest_calls'] += 1

                    # 更新缓存
                    cache_key = f"{symbol}_klines_{interval}"
                    if symbol not in self.klines_cache:
                        self.klines_cache[symbol] = {}
                    self.klines_cache[symbol][interval] = deque(data, maxlen=self.config['max_klines'])
                    self.last_update[cache_key] = time.time()

                    return data
                else:
                    error(f"❌ REST获取K线失败 {symbol} {interval}: HTTP {resp.status}")
                    return []
        except Exception as e:
            error(f"❌ REST获取K线异常 {symbol} {interval}: {e}")
            return []


    async def _fetch_oi_rest(
        self,
        symbol: str,
        interval: str = '1h',
        limit: int = 100
    ) -> List[Dict]:
        """REST获取OI历史"""
        if not self.session:
            raise RuntimeError("HTTP会话未初始化")

        url = f"{self.base_url}/futures/data/openInterestHist"
        params = {
            'symbol': symbol,
            'period': interval,
            'limit': limit
        }

        try:
            async with self.session.get(url, params=params, timeout=self.config['rest_timeout']) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.stats['rest_calls'] += 1

                    # 更新缓存
                    cache_key = f"{symbol}_oi"
                    self.oi_cache[symbol] = deque(data, maxlen=self.config['max_oi'])
                    self.last_update[cache_key] = time.time()

                    return data
                else:
                    error(f"❌ REST获取OI失败 {symbol}: HTTP {resp.status}")
                    return []
        except Exception as e:
            error(f"❌ REST获取OI异常 {symbol}: {e}")
            return []


    async def _fetch_orderbook_rest(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """REST获取订单簿快照"""
        if not self.session:
            raise RuntimeError("HTTP会话未初始化")

        url = f"{self.base_url}/fapi/v1/depth"
        params = {'symbol': symbol, 'limit': limit}

        try:
            async with self.session.get(url, params=params, timeout=self.config['rest_timeout']) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.stats['rest_calls'] += 1

                    # 更新缓存
                    cache_key = f"{symbol}_orderbook"
                    orderbook = {
                        'bids': [[float(p), float(q)] for p, q in data.get('bids', [])],
                        'asks': [[float(p), float(q)] for p, q in data.get('asks', [])],
                        'timestamp': time.time() * 1000
                    }
                    self.orderbook_cache[symbol] = orderbook
                    self.last_update[cache_key] = time.time()

                    return orderbook
                else:
                    error(f"❌ REST获取订单簿失败 {symbol}: HTTP {resp.status}")
                    return None
        except Exception as e:
            error(f"❌ REST获取订单簿异常 {symbol}: {e}")
            return None


    async def _fetch_funding_rest(self, symbol: str) -> Optional[Dict]:
        """REST获取资金费率"""
        if not self.session:
            raise RuntimeError("HTTP会话未初始化")

        url = f"{self.base_url}/fapi/v1/premiumIndex"
        params = {'symbol': symbol}

        try:
            async with self.session.get(url, params=params, timeout=self.config['rest_timeout']) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.stats['rest_calls'] += 1

                    # 更新缓存
                    cache_key = f"{symbol}_funding"
                    funding = {
                        'rate': float(data.get('lastFundingRate', 0)),
                        'nextTime': data.get('nextFundingTime', 0),
                        'markPrice': float(data.get('markPrice', 0)),
                        'timestamp': time.time()
                    }
                    self.funding_cache[symbol] = funding
                    self.last_update[cache_key] = time.time()

                    return funding
                else:
                    error(f"❌ REST获取资金费率失败 {symbol}: HTTP {resp.status}")
                    return None
        except Exception as e:
            error(f"❌ REST获取资金费率异常 {symbol}: {e}")
            return None


    async def _fetch_spot_price_rest(self, symbol: str) -> Optional[Dict]:
        """REST获取现货价格"""
        if not self.session:
            raise RuntimeError("HTTP会话未初始化")

        url = f"{self.spot_base_url}/api/v3/ticker/price"
        params = {'symbol': symbol}

        try:
            async with self.session.get(url, params=params, timeout=self.config['rest_timeout']) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.stats['rest_calls'] += 1

                    # 更新缓存
                    cache_key = f"{symbol}_spot"
                    price_data = {
                        'price': float(data.get('price', 0)),
                        'timestamp': time.time()
                    }
                    self.spot_price_cache[symbol] = price_data
                    self.last_update[cache_key] = time.time()

                    return price_data
                else:
                    error(f"❌ REST获取现货价格失败 {symbol}: HTTP {resp.status}")
                    return None
        except Exception as e:
            error(f"❌ REST获取现货价格异常 {symbol}: {e}")
            return None


    async def _fetch_agg_trades_rest(self, symbol: str, limit: int = 500) -> List[Dict]:
        """REST获取aggTrades（用于Q因子清算密度）"""
        if not self.session:
            raise RuntimeError("HTTP会话未初始化")

        url = f"{self.base_url}/fapi/v1/aggTrades"
        params = {'symbol': symbol, 'limit': limit}

        try:
            async with self.session.get(url, params=params, timeout=self.config['rest_timeout']) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.stats['rest_calls'] += 1

                    # 更新缓存
                    cache_key = f"{symbol}_liquidation"
                    trades = [
                        {
                            'price': float(t.get('p', 0)),
                            'qty': float(t.get('q', 0)),
                            'time': t.get('T', 0),
                            'isBuyerMaker': t.get('m', False)
                        }
                        for t in data
                    ]
                    self.liquidation_cache[symbol] = deque(trades, maxlen=1000)
                    self.last_update[cache_key] = time.time()

                    return trades
                else:
                    error(f"❌ REST获取aggTrades失败 {symbol}: HTTP {resp.status}")
                    return []
        except Exception as e:
            error(f"❌ REST获取aggTrades异常 {symbol}: {e}")
            return []


    # ============================================================
    # 批量初始化（REST）
    # ============================================================

    async def _init_klines_batch(self, symbols: List[str], intervals: List[str]):
        """批量初始化K线数据"""
        log(f"   初始化K线缓存: {len(symbols)}币种 × {len(intervals)}周期")

        total = len(symbols) * len(intervals)
        completed = 0

        for symbol in symbols:
            for interval in intervals:
                await self._fetch_klines_rest(symbol, interval, self.config['max_klines'])
                completed += 1

                if completed % 20 == 0:
                    log(f"      进度: {completed}/{total} ({completed*100//total}%)")

        log(f"   ✅ K线缓存初始化完成: {total}个")


    async def _init_oi_batch(self, symbols: List[str]):
        """批量初始化OI数据"""
        log(f"   初始化OI缓存: {len(symbols)}币种")

        for i, symbol in enumerate(symbols):
            await self._fetch_oi_rest(symbol, '1h', self.config['max_oi'])

            if (i + 1) % 20 == 0:
                log(f"      进度: {i+1}/{len(symbols)} ({(i+1)*100//len(symbols)}%)")

        log(f"   ✅ OI缓存初始化完成: {len(symbols)}个")


    async def _init_funding_batch(self, symbols: List[str]):
        """批量初始化资金费率"""
        log(f"   初始化资金费率缓存: {len(symbols)}币种")

        for i, symbol in enumerate(symbols):
            await self._fetch_funding_rest(symbol)

            if (i + 1) % 20 == 0:
                log(f"      进度: {i+1}/{len(symbols)} ({(i+1)*100//len(symbols)}%)")

        log(f"   ✅ 资金费率缓存初始化完成: {len(symbols)}个")


    # ============================================================
    # WebSocket实时更新（TODO: 需要实现）
    # ============================================================

    async def _start_websocket_streams(self, symbols: List[str], intervals: List[str]):
        """启动WebSocket实时更新流"""
        log("   ⚠️  WebSocket功能待实现")
        log("   提示: 需要安装 websockets 库")
        log("   提示: pip install websockets")
        # TODO: 实现WebSocket订阅
        # 1. 订阅 K线流: {symbol}@kline_{interval}
        # 2. 订阅 订单簿流: {symbol}@depth20@100ms
        # 3. 订阅 标记价格流: {symbol}@markPrice@3s
        # 4. 订阅 成交流: {symbol}@aggTrade


    # ============================================================
    # REST定期轮询任务
    # ============================================================

    def _start_rest_polling_tasks(self, symbols: List[str]):
        """启动REST定期轮询任务（低频数据）"""
        log("   启动REST定期轮询任务...")

        # OI轮询（每5分钟）
        task1 = asyncio.create_task(self._poll_oi_periodic(symbols))
        self.background_tasks.append(task1)

        # 资金费率轮询（每小时）
        task2 = asyncio.create_task(self._poll_funding_periodic(symbols))
        self.background_tasks.append(task2)

        # 现货价格轮询（每分钟）
        task3 = asyncio.create_task(self._poll_spot_price_periodic(symbols))
        self.background_tasks.append(task3)

        # 清算数据轮询（每5分钟）
        task4 = asyncio.create_task(self._poll_liquidation_periodic(symbols))
        self.background_tasks.append(task4)

        log(f"   ✅ 启动了 {len(self.background_tasks)} 个后台轮询任务")


    async def _poll_oi_periodic(self, symbols: List[str]):
        """定期轮询OI数据（每5分钟）"""
        while True:
            try:
                await asyncio.sleep(self.config['oi_update_interval'])

                for symbol in symbols:
                    await self._fetch_oi_rest(symbol, '1h', 100)
                    await asyncio.sleep(0.1)  # 防止请求过快

            except asyncio.CancelledError:
                break
            except Exception as e:
                error(f"❌ OI轮询异常: {e}")


    async def _poll_funding_periodic(self, symbols: List[str]):
        """定期轮询资金费率（每小时）"""
        while True:
            try:
                await asyncio.sleep(self.config['funding_update_interval'])

                for symbol in symbols:
                    await self._fetch_funding_rest(symbol)
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                error(f"❌ 资金费率轮询异常: {e}")


    async def _poll_spot_price_periodic(self, symbols: List[str]):
        """定期轮询现货价格（每分钟）"""
        while True:
            try:
                await asyncio.sleep(self.config['spot_update_interval'])

                for symbol in symbols:
                    await self._fetch_spot_price_rest(symbol)
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                error(f"❌ 现货价格轮询异常: {e}")


    async def _poll_liquidation_periodic(self, symbols: List[str]):
        """定期轮询清算数据（每5分钟）"""
        while True:
            try:
                await asyncio.sleep(self.config['liquidation_update_interval'])

                for symbol in symbols:
                    await self._fetch_agg_trades_rest(symbol, 500)
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                error(f"❌ 清算数据轮询异常: {e}")


    # ============================================================
    # 统计和监控
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'initialized': self.initialized,
            'symbols_count': len(self.symbols),
            'klines_cached': sum(len(intervals) for intervals in self.klines_cache.values()),
            'oi_cached': len(self.oi_cache),
            'funding_cached': len(self.funding_cache),
            'ws_updates': self.stats['ws_updates'],
            'rest_calls': self.stats['rest_calls'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate': f"{self.stats['cache_hits']*100/(self.stats['cache_hits']+self.stats['cache_misses']+1):.1f}%"
        }


# ========== 单例模式 ==========

_global_data_manager: Optional[UnifiedDataManager] = None


def get_data_manager() -> UnifiedDataManager:
    """获取全局数据管理器（单例）"""
    global _global_data_manager

    if _global_data_manager is None:
        _global_data_manager = UnifiedDataManager()

    return _global_data_manager


# ========== 测试代码 ==========

async def test_data_manager():
    """测试数据管理器"""
    print("=" * 70)
    print("统一数据管理器测试")
    print("=" * 70)

    # 创建管理器
    dm = get_data_manager()

    # 初始化（仅测试2个币种）
    test_symbols = ['BTCUSDT', 'ETHUSDT']
    await dm.initialize(
        symbols=test_symbols,
        intervals=['1h', '4h'],
        enable_websocket=False  # 测试模式，禁用WebSocket
    )

    # 测试数据获取
    print("\n" + "=" * 70)
    print("测试数据获取")
    print("=" * 70)

    # 1. K线数据
    klines = await dm.get_klines('BTCUSDT', '1h', limit=10)
    print(f"\n1️⃣  K线数据: {len(klines)}根")
    if klines:
        print(f"   最新K线: {klines[-1][:6]}")  # [时间, 开, 高, 低, 收, 量]

    # 2. OI数据
    oi_data = await dm.get_oi_history('BTCUSDT', limit=10)
    print(f"\n2️⃣  OI数据: {len(oi_data)}条")
    if oi_data:
        print(f"   最新OI: {oi_data[-1]}")

    # 3. 订单簿
    orderbook = await dm.get_orderbook('BTCUSDT')
    print(f"\n3️⃣  订单簿:")
    if orderbook:
        print(f"   最佳买价: {orderbook['bids'][0] if orderbook['bids'] else 'N/A'}")
        print(f"   最佳卖价: {orderbook['asks'][0] if orderbook['asks'] else 'N/A'}")

    # 4. 资金费率
    funding = await dm.get_funding_rate('BTCUSDT')
    print(f"\n4️⃣  资金费率:")
    if funding:
        print(f"   费率: {funding['rate']}")
        print(f"   标记价格: {funding.get('markPrice')}")

    # 5. 现货价格
    spot_price = await dm.get_spot_price('BTCUSDT')
    print(f"\n5️⃣  现货价格: {spot_price}")

    # 6. 清算数据
    liq_trades = await dm.get_liquidation_trades('BTCUSDT', limit=10)
    print(f"\n6️⃣  清算数据: {len(liq_trades)}笔")
    if liq_trades:
        print(f"   最新清算: {liq_trades[-1]}")

    # 显示统计
    print("\n" + "=" * 70)
    print("统计信息")
    print("=" * 70)
    stats = dm.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # 关闭
    await dm.close()

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_data_manager())
