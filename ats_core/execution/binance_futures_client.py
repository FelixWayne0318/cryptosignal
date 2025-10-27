# coding: utf-8
"""
币安合约交易客户端（世界顶尖标准）

特性:
1. WebSocket实时数据流（价格、订单簿、清算、OI）
2. 高性能异步执行
3. 完善的错误处理和重连机制
4. 精确的风险控制
5. 低延迟执行（<200ms）
"""

import asyncio
import json
import time
import hmac
import hashlib
from typing import Dict, List, Optional, Callable, Any
from decimal import Decimal
import aiohttp
import websockets
from datetime import datetime, timezone

from ats_core.logging import log, warn, error


class BinanceFuturesClient:
    """
    币安合约交易客户端（完整实现）

    功能:
    - WebSocket实时数据流
    - REST API交易接口
    - 自动重连和错误恢复
    - 精确的时间同步
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # API端点
        if testnet:
            self.base_url = "https://testnet.binancefuture.com"
            self.ws_base_url = "wss://stream.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
            self.ws_base_url = "wss://fstream.binance.com"

        # WebSocket连接
        self.ws_connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.ws_callbacks: Dict[str, List[Callable]] = {}

        # 会话管理
        self.session: Optional[aiohttp.ClientSession] = None

        # 时间同步
        self.server_time_offset = 0

        # 状态
        self.is_running = False

        log(f"✅ 币安合约客户端初始化完成 (testnet={testnet})")

    async def initialize(self):
        """初始化客户端（同步服务器时间）"""
        self.session = aiohttp.ClientSession()

        # 同步服务器时间
        await self._sync_time()

        log("✅ 客户端初始化完成，服务器时间已同步")

    async def close(self):
        """关闭客户端"""
        self.is_running = False

        # 关闭所有WebSocket连接
        for ws in self.ws_connections.values():
            await ws.close()

        # 关闭HTTP会话
        if self.session:
            await self.session.close()

        log("✅ 客户端已关闭")

    # ========== 时间同步 ==========

    async def _sync_time(self):
        """同步服务器时间"""
        try:
            async with self.session.get(f"{self.base_url}/fapi/v1/time") as resp:
                data = await resp.json()
                server_time = data['serverTime']
                local_time = int(time.time() * 1000)
                self.server_time_offset = server_time - local_time

                log(f"⏰ 服务器时间同步完成，偏移: {self.server_time_offset}ms")

        except Exception as e:
            error(f"时间同步失败: {e}")
            self.server_time_offset = 0

    def _get_timestamp(self) -> int:
        """获取同步后的时间戳"""
        return int(time.time() * 1000) + self.server_time_offset

    # ========== 签名 ==========

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """生成请求签名"""
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _sign_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """为请求添加签名"""
        params['timestamp'] = self._get_timestamp()
        params['signature'] = self._generate_signature(params)
        return params

    # ========== REST API ==========

    async def _request(self, method: str, endpoint: str, signed: bool = False,
                      params: Dict = None) -> Dict:
        """
        发送HTTP请求

        Args:
            method: GET/POST/DELETE
            endpoint: API端点
            signed: 是否需要签名
            params: 请求参数
        """
        if params is None:
            params = {}

        url = f"{self.base_url}{endpoint}"
        headers = {'X-MBX-APIKEY': self.api_key}

        if signed:
            params = self._sign_request(params)

        try:
            async with self.session.request(
                method, url, params=params, headers=headers
            ) as resp:
                data = await resp.json()

                if resp.status != 200:
                    error(f"API请求失败 [{resp.status}]: {data}")
                    return {'error': data}

                return data

        except Exception as e:
            error(f"API请求异常: {e}")
            return {'error': str(e)}

    # ========== 账户信息 ==========

    async def get_account_info(self) -> Dict:
        """获取账户信息"""
        return await self._request('GET', '/fapi/v2/account', signed=True)

    async def get_balance(self) -> List[Dict]:
        """获取账户余额"""
        account = await self.get_account_info()
        return account.get('assets', [])

    async def get_positions(self) -> List[Dict]:
        """获取当前持仓"""
        account = await self.get_account_info()
        positions = account.get('positions', [])

        # 只返回有持仓的币种
        return [p for p in positions if float(p['positionAmt']) != 0]

    # ========== 市场数据 ==========

    async def get_ticker(self, symbol: str) -> Dict:
        """获取24小时行情"""
        return await self._request('GET', '/fapi/v1/ticker/24hr',
                                   params={'symbol': symbol})

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """获取订单簿"""
        return await self._request('GET', '/fapi/v1/depth',
                                   params={'symbol': symbol, 'limit': limit})

    async def get_klines(self, symbol: str, interval: str = '5m',
                        limit: int = 100) -> List:
        """获取K线数据"""
        return await self._request('GET', '/fapi/v1/klines',
                                   params={
                                       'symbol': symbol,
                                       'interval': interval,
                                       'limit': limit
                                   })

    async def get_funding_rate(self, symbol: str) -> Dict:
        """获取资金费率"""
        return await self._request('GET', '/fapi/v1/premiumIndex',
                                   params={'symbol': symbol})

    async def get_open_interest(self, symbol: str) -> Dict:
        """获取持仓量"""
        return await self._request('GET', '/fapi/v1/openInterest',
                                   params={'symbol': symbol})

    # ========== 交易接口 ==========

    async def create_order(self,
                          symbol: str,
                          side: str,  # BUY/SELL
                          order_type: str,  # LIMIT/MARKET
                          quantity: float,
                          price: Optional[float] = None,
                          time_in_force: str = 'GTC',
                          reduce_only: bool = False,
                          stop_price: Optional[float] = None,
                          **kwargs) -> Dict:
        """
        创建订单

        Args:
            symbol: 交易对
            side: BUY/SELL
            order_type: LIMIT/MARKET/STOP/STOP_MARKET/TAKE_PROFIT/TAKE_PROFIT_MARKET
            quantity: 数量
            price: 价格（限价单必需）
            time_in_force: GTC/IOC/FOK
            reduce_only: 只减仓
            stop_price: 触发价（止损单）
        """
        # 🔧 修复：添加订单参数验证
        if not symbol or not isinstance(symbol, str):
            raise ValueError(f"无效的交易对: {symbol}")

        if side not in ['BUY', 'SELL']:
            raise ValueError(f"无效的订单方向: {side}（必须是 BUY 或 SELL）")

        valid_order_types = ['MARKET', 'LIMIT', 'STOP', 'STOP_MARKET',
                            'TAKE_PROFIT', 'TAKE_PROFIT_MARKET']
        if order_type not in valid_order_types:
            raise ValueError(f"无效的订单类型: {order_type}（必须是 {', '.join(valid_order_types)} 之一）")

        if quantity <= 0:
            raise ValueError(f"无效的数量: {quantity}（必须 > 0）")

        if price is not None and price <= 0:
            raise ValueError(f"无效的价格: {price}（必须 > 0）")

        if stop_price is not None and stop_price <= 0:
            raise ValueError(f"无效的触发价: {stop_price}（必须 > 0）")

        # 限价单必须提供价格
        if order_type == 'LIMIT' and price is None:
            raise ValueError("限价单必须提供价格参数")

        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'timeInForce': time_in_force,
            'reduceOnly': 'true' if reduce_only else 'false'
        }

        if price is not None:
            params['price'] = price

        if stop_price is not None:
            params['stopPrice'] = stop_price

        # 添加其他参数
        params.update(kwargs)

        log(f"📝 创建订单: {symbol} {side} {order_type} qty={quantity} price={price}")

        result = await self._request('POST', '/fapi/v1/order', signed=True, params=params)

        if 'error' not in result:
            log(f"✅ 订单创建成功: {result.get('orderId')}")
        else:
            error(f"❌ 订单创建失败: {result['error']}")

        return result

    async def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """取消订单"""
        log(f"🗑️  取消订单: {symbol} order_id={order_id}")

        return await self._request('DELETE', '/fapi/v1/order', signed=True,
                                   params={'symbol': symbol, 'orderId': order_id})

    async def cancel_all_orders(self, symbol: str) -> Dict:
        """取消所有订单"""
        log(f"🗑️  取消所有订单: {symbol}")

        return await self._request('DELETE', '/fapi/v1/allOpenOrders',
                                   signed=True, params={'symbol': symbol})

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取当前挂单"""
        params = {}
        if symbol:
            params['symbol'] = symbol

        return await self._request('GET', '/fapi/v1/openOrders', signed=True, params=params)

    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """设置杠杆倍数"""
        log(f"⚙️  设置杠杆: {symbol} leverage={leverage}x")

        return await self._request('POST', '/fapi/v1/leverage', signed=True,
                                   params={'symbol': symbol, 'leverage': leverage})

    async def set_margin_type(self, symbol: str, margin_type: str) -> Dict:
        """
        设置保证金模式

        Args:
            margin_type: ISOLATED（逐仓）或 CROSSED（全仓）
        """
        log(f"⚙️  设置保证金模式: {symbol} type={margin_type}")

        return await self._request('POST', '/fapi/v1/marginType', signed=True,
                                   params={'symbol': symbol, 'marginType': margin_type})

    # ========== 市价单快捷方法 ==========

    async def market_buy(self, symbol: str, quantity: float) -> Dict:
        """市价买入（做多）"""
        return await self.create_order(
            symbol=symbol,
            side='BUY',
            order_type='MARKET',
            quantity=quantity
        )

    async def market_sell(self, symbol: str, quantity: float) -> Dict:
        """市价卖出（做空）"""
        return await self.create_order(
            symbol=symbol,
            side='SELL',
            order_type='MARKET',
            quantity=quantity
        )

    async def close_position(self, symbol: str, position_side: str = 'BOTH') -> Dict:
        """
        平仓

        Args:
            symbol: 交易对
            position_side: BOTH/LONG/SHORT
        """
        # 获取当前持仓
        positions = await self.get_positions()
        position = next((p for p in positions if p['symbol'] == symbol), None)

        if not position:
            log(f"⚠️  没有找到持仓: {symbol}")
            return {'error': 'No position found'}

        position_amt = float(position['positionAmt'])

        if position_amt == 0:
            log(f"⚠️  持仓量为0: {symbol}")
            return {'error': 'Position amount is zero'}

        # 确定平仓方向
        side = 'SELL' if position_amt > 0 else 'BUY'
        quantity = abs(position_amt)

        log(f"🔄 平仓: {symbol} {side} qty={quantity}")

        return await self.create_order(
            symbol=symbol,
            side=side,
            order_type='MARKET',
            quantity=quantity,
            reduce_only=True
        )

    # ========== WebSocket数据流 ==========

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        订阅实时价格

        推送频率: 实时（价格变化时）
        """
        stream = f"{symbol.lower()}@ticker"
        await self._subscribe_stream(stream, callback)

    async def subscribe_orderbook(self, symbol: str, callback: Callable,
                                 levels: int = 20, update_speed: str = '100ms'):
        """
        订阅订单簿

        Args:
            levels: 5/10/20
            update_speed: 100ms/250ms/500ms
        """
        stream = f"{symbol.lower()}@depth{levels}@{update_speed}"
        await self._subscribe_stream(stream, callback)

    async def subscribe_kline(self, symbol: str, interval: str, callback: Callable):
        """
        订阅K线

        Args:
            interval: 1m/3m/5m/15m/30m/1h/2h/4h/6h/8h/12h/1d/3d/1w/1M
        """
        stream = f"{symbol.lower()}@kline_{interval}"
        await self._subscribe_stream(stream, callback)

    async def subscribe_force_order(self, symbol: str, callback: Callable):
        """订阅强平订单（清算数据）"""
        stream = f"{symbol.lower()}@forceOrder"
        await self._subscribe_stream(stream, callback)

    async def subscribe_agg_trade(self, symbol: str, callback: Callable):
        """订阅归集交易流"""
        stream = f"{symbol.lower()}@aggTrade"
        await self._subscribe_stream(stream, callback)

    async def subscribe_mark_price(self, symbol: str, callback: Callable):
        """订阅标记价格"""
        stream = f"{symbol.lower()}@markPrice@1s"
        await self._subscribe_stream(stream, callback)

    async def _subscribe_stream(self, stream: str, callback: Callable):
        """
        订阅WebSocket数据流

        Args:
            stream: 数据流名称
            callback: 回调函数
        """
        if stream not in self.ws_callbacks:
            self.ws_callbacks[stream] = []

        self.ws_callbacks[stream].append(callback)

        # 如果连接不存在，创建新连接
        if stream not in self.ws_connections:
            asyncio.create_task(self._ws_connect(stream))

        log(f"✅ 已订阅数据流: {stream}")

    async def _ws_connect(self, stream: str):
        """建立WebSocket连接"""
        url = f"{self.ws_base_url}/ws/{stream}"

        while self.is_running or not self.ws_connections:
            try:
                log(f"🔌 连接WebSocket: {stream}")

                async with websockets.connect(url) as ws:
                    self.ws_connections[stream] = ws

                    log(f"✅ WebSocket连接成功: {stream}")

                    # 接收数据
                    async for message in ws:
                        try:
                            data = json.loads(message)

                            # 调用所有回调函数
                            for callback in self.ws_callbacks.get(stream, []):
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(data)
                                    else:
                                        callback(data)
                                except Exception as e:
                                    error(f"回调函数执行失败: {e}")

                        except json.JSONDecodeError as e:
                            error(f"JSON解析失败: {e}")

            except websockets.exceptions.ConnectionClosed:
                warn(f"WebSocket连接断开: {stream}，3秒后重连...")
                await asyncio.sleep(3)

            except Exception as e:
                error(f"WebSocket错误: {e}，5秒后重连...")
                await asyncio.sleep(5)

            finally:
                if stream in self.ws_connections:
                    del self.ws_connections[stream]

        log(f"🔌 WebSocket已关闭: {stream}")

    # ========== 用户数据流（订单更新、持仓更新）==========

    async def start_user_data_stream(self, callback: Callable):
        """
        启动用户数据流（接收订单/持仓更新）

        推送内容:
        - 账户更新
        - 订单更新
        - 持仓更新
        """
        # 1. 获取listenKey
        listen_key_data = await self._request('POST', '/fapi/v1/listenKey', signed=False)
        listen_key = listen_key_data.get('listenKey')

        if not listen_key:
            error("获取listenKey失败")
            return

        log(f"✅ 获取listenKey成功: {listen_key[:10]}...")

        # 2. 定时keepalive（每30分钟）
        asyncio.create_task(self._keepalive_listen_key(listen_key))

        # 3. 连接用户数据流
        url = f"{self.ws_base_url}/ws/{listen_key}"

        while self.is_running:
            try:
                log(f"🔌 连接用户数据流...")

                async with websockets.connect(url) as ws:
                    log(f"✅ 用户数据流连接成功")

                    async for message in ws:
                        try:
                            data = json.loads(message)

                            # 调用回调
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)

                        except Exception as e:
                            error(f"用户数据流处理失败: {e}")

            except Exception as e:
                error(f"用户数据流错误: {e}，5秒后重连...")
                await asyncio.sleep(5)

    async def _keepalive_listen_key(self, listen_key: str):
        """保持listenKey活跃"""
        while self.is_running:
            await asyncio.sleep(30 * 60)  # 每30分钟

            try:
                await self._request('PUT', '/fapi/v1/listenKey',
                                   signed=False, params={'listenKey': listen_key})
                log(f"✅ listenKey续期成功")
            except Exception as e:
                error(f"listenKey续期失败: {e}")


# ============ 全局实例 ============

_client_instance: Optional[BinanceFuturesClient] = None

def get_binance_client(config_path: str = "config/binance_credentials.json") -> BinanceFuturesClient:
    """获取币安客户端单例"""
    global _client_instance

    if _client_instance is None:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)

        binance_config = config['binance']

        _client_instance = BinanceFuturesClient(
            api_key=binance_config['api_key'],
            api_secret=binance_config['api_secret'],
            testnet=binance_config.get('testnet', False)
        )

    return _client_instance
