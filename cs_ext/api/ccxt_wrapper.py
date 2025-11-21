# cs_ext/api/ccxt_wrapper.py
"""
CCXT 统一封装

设计目标：
- 为 CryptoSignal 提供一个简化的交易所访问接口
- 底层使用 ccxt
- 支持：
  - 初始化 exchange
  - 获取 K 线
  - 查询余额
  - 市价/限价下单
  - 撤单

注意：
- 这里只提供通用骨架，具体参数（如是否逐仓/全仓、杠杆设置）需要你根据实际交易所规则扩展。
"""

from __future__ import annotations

import time
from typing import Optional, List, Dict, Any

import ccxt


class CcxtExchange:
    """
    CCXT 交易所封装。
    """

    def __init__(
        self,
        exchange_id: str,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        password: Optional[str] = None,
        enable_rate_limit: bool = True,
        testnet: bool = False,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        """
        :param exchange_id: 交易所标识，例如 "binance" / "binanceusdm" / "okx"
        :param api_key: API Key
        :param secret: API Secret
        :param password: 一些交易所需要（如 OKX passphrase）
        :param enable_rate_limit: 是否启用 ccxt 内置限速
        :param testnet: 是否使用测试网（如果交易所支持）
        :param extra_config: 额外配置，如 {"options": {...}, "urls": {...}}
        """
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"不支持的交易所 exchange_id={exchange_id}")

        exchange_class = getattr(ccxt, exchange_id)
        config: Dict[str, Any] = {
            "enableRateLimit": enable_rate_limit,
        }
        if api_key:
            config["apiKey"] = api_key
        if secret:
            config["secret"] = secret
        if password:
            config["password"] = password
        if extra_config:
            config.update(extra_config)

        self._exchange: ccxt.Exchange = exchange_class(config)

        # 部分交易所支持 testnet，需要单独设置（示例：binanceusdm）
        if testnet:
            urls = getattr(self._exchange, "urls", None)
            if urls and "test" in urls:
                self._exchange.urls["api"] = urls["test"]

    @property
    def raw(self) -> ccxt.Exchange:
        """
        暴露原始 ccxt exchange 对象，以便高级用法。
        """
        return self._exchange

    # -----------------------------
    # 公共接口
    # -----------------------------
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[List[Any]]:
        """
        获取历史K线：
        返回格式：[[timestamp, open, high, low, close, volume], ...]
        """
        params = params or {}
        return self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit, params=params)

    def fetch_balance(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        return self._exchange.fetch_balance(params=params)

    def fetch_ticker(self, symbol: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        return self._exchange.fetch_ticker(symbol, params=params)

    # -----------------------------
    # 下单/撤单接口（简化版）
    # -----------------------------
    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建订单（市价 or 限价）。

        :param symbol: "BTC/USDT"
        :param side: "buy" / "sell"
        :param order_type: "market" / "limit"
        :param amount: 数量
        :param price: 限价单价格（市价单可为 None）
        :param params: 交易所特定参数，例如 {"reduceOnly": True}
        """
        params = params or {}
        return self._exchange.create_order(symbol, order_type, side, amount, price, params)

    def cancel_order(self, order_id: str, symbol: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        return self._exchange.cancel_order(order_id, symbol, params)

    def fetch_open_orders(self, symbol: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        return self._exchange.fetch_open_orders(symbol, params=params)

    def fetch_positions(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        某些合约交易所支持 fetchPositions。
        """
        params = params or {}
        if hasattr(self._exchange, "fetch_positions"):
            return self._exchange.fetch_positions(params)
        raise NotImplementedError("当前 exchange 不支持 fetch_positions")

    # -----------------------------
    # 简单重试封装（示例）
    # -----------------------------
    def safe_fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> List[List[Any]]:
        """
        带简单重试的 K 线获取方法。
        """
        last_exc = None
        for _ in range(max_retries):
            try:
                return self.fetch_ohlcv(symbol, timeframe, since, limit, params)
            except Exception as e:
                last_exc = e
                print(f"[CcxtExchange] fetch_ohlcv 失败，重试中：{e}")
                time.sleep(retry_delay)
        raise last_exc
