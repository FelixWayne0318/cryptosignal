# coding: utf-8
"""
V8 Backtest Data Loader - 使用CCXT+Cryptostore
V8回测数据加载器

功能：
1. 使用CCXT获取历史K线数据
2. 使用Cryptostore适配器缓存数据
3. 支持多交易对批量加载
4. 配置驱动（无硬编码）

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Architecture: V8 六层架构
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ats_core.config.threshold_config import get_thresholds

logger = logging.getLogger(__name__)


class V8BacktestDataLoader:
    """
    V8回测数据加载器

    使用CCXT统一API获取数据，Cryptostore缓存落盘

    配置来源: config/signal_thresholds.json -> v8_integration.backtest
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化V8回测数据加载器

        Args:
            config: 可选的配置覆盖，默认从v8_integration.backtest读取
        """
        # 加载配置
        thresholds = get_thresholds()
        v8_config = thresholds.get_all().get("v8_integration", {})
        backtest_config = v8_config.get("backtest", {})

        # 合并用户配置
        if config:
            self._merge_config(backtest_config, config)

        self.config = backtest_config

        # 数据源配置
        ds_config = self.config.get("data_source", {})
        self.exchange_id = ds_config.get("exchange_id", "binanceusdm")
        self.testnet = ds_config.get("testnet", False)
        self.rate_limit = ds_config.get("rate_limit_enabled", True)
        self.max_retries = ds_config.get("max_retries", 3)
        self.retry_delay_base = ds_config.get("retry_delay_base", 2.0)
        self.retry_delay_range = ds_config.get("retry_delay_range", 2.0)
        self.timeout = ds_config.get("timeout_seconds", 30)

        # 缓存配置
        cache_config = self.config.get("cache", {})
        self.cache_enabled = cache_config.get("enabled", True)
        self.cache_path = Path(cache_config.get("storage_path", "data/v8_backtest_cache"))
        self.cache_format = cache_config.get("format", "parquet")
        self.cache_ttl_hours = cache_config.get("ttl_hours", 168)

        # 引擎配置
        engine_config = self.config.get("engine", {})
        self.default_timeframe = engine_config.get("default_timeframe", "1h")
        self.lookback_bars = engine_config.get("lookback_bars", 300)

        # 初始化CCXT交易所
        self._exchange = None
        self._init_exchange()

        # 初始化缓存目录
        if self.cache_enabled:
            self.cache_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"V8缓存已启用: {self.cache_path}")

        logger.info(
            f"V8BacktestDataLoader initialized: "
            f"exchange={self.exchange_id}, "
            f"timeframe={self.default_timeframe}, "
            f"cache={'ON' if self.cache_enabled else 'OFF'}"
        )

    def _merge_config(self, base: Dict, override: Dict) -> None:
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _init_exchange(self) -> None:
        """初始化CCXT交易所连接"""
        try:
            from cs_ext.api.ccxt_wrapper import CcxtExchange

            self._exchange = CcxtExchange(
                exchange_id=self.exchange_id,
                enable_rate_limit=self.rate_limit,
                testnet=self.testnet
            )
            logger.info(f"CCXT交易所初始化成功: {self.exchange_id}")

        except ImportError as e:
            logger.warning(f"CCXT导入失败，回退到传统API: {e}")
            self._exchange = None
        except Exception as e:
            logger.error(f"CCXT初始化失败: {e}")
            self._exchange = None

    def _convert_symbol_format(self, symbol: str) -> str:
        """
        转换交易对格式

        旧格式: BTCUSDT
        CCXT格式: BTC/USDT:USDT (永续合约)
        """
        symbol = symbol.upper()

        # 如果已经是CCXT格式
        if "/" in symbol:
            return symbol

        # 常见USDT永续合约
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            return f"{base}/USDT:USDT"

        # 其他格式保持不变
        return symbol

    def _get_cache_file(self, symbol: str, timeframe: str, start_ts: int, end_ts: int) -> Path:
        """获取缓存文件路径"""
        # 标准化symbol作为文件名
        safe_symbol = symbol.replace("/", "_").replace(":", "_")
        filename = f"{safe_symbol}_{timeframe}_{start_ts}_{end_ts}.json"
        return self.cache_path / filename

    def _load_from_cache(self, cache_file: Path) -> Optional[List[List]]:
        """从缓存加载数据"""
        if not cache_file.exists():
            return None

        # 检查TTL
        file_age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if file_age_hours > self.cache_ttl_hours:
            logger.debug(f"缓存已过期: {cache_file}")
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            logger.debug(f"从缓存加载: {cache_file}, {len(data)}条K线")
            return data
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
            return None

    def _save_to_cache(self, cache_file: Path, data: List[List]) -> None:
        """保存数据到缓存"""
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"已缓存: {cache_file}, {len(data)}条K线")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        since: Optional[int] = None,
        until: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List]:
        """
        获取历史K线数据

        Args:
            symbol: 交易对 (支持BTCUSDT或BTC/USDT:USDT格式)
            timeframe: K线周期 (默认从配置读取)
            since: 开始时间戳(毫秒)
            until: 结束时间戳(毫秒)
            limit: 数量限制

        Returns:
            [[timestamp, open, high, low, close, volume], ...]
        """
        timeframe = timeframe or self.default_timeframe
        ccxt_symbol = self._convert_symbol_format(symbol)

        # 尝试从缓存加载
        if self.cache_enabled and since and until:
            cache_file = self._get_cache_file(ccxt_symbol, timeframe, since, until)
            cached_data = self._load_from_cache(cache_file)
            if cached_data:
                return cached_data

        # 使用CCXT获取数据
        if self._exchange is None:
            logger.error("CCXT未初始化，无法获取数据")
            return []

        all_data = []
        current_since = since

        try:
            # 分批获取数据
            while True:
                logger.debug(f"CCXT获取K线: {ccxt_symbol} {timeframe} since={current_since}")

                batch = self._exchange.safe_fetch_ohlcv_with_retry(
                    symbol=ccxt_symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=limit or 1000,
                    max_retries=self.max_retries,
                    retry_delay=self.retry_delay_base
                )

                if not batch:
                    break

                all_data.extend(batch)

                # 检查是否到达结束时间
                last_ts = batch[-1][0]
                if until and last_ts >= until:
                    # 过滤超出范围的数据
                    all_data = [k for k in all_data if k[0] <= until]
                    break

                # 如果返回数量少于请求，说明没有更多数据
                if len(batch) < (limit or 1000):
                    break

                # 更新起始时间继续获取
                current_since = last_ts + 1

                # 避免过快请求
                time.sleep(0.1)

            logger.info(f"CCXT获取完成: {ccxt_symbol} {timeframe}, {len(all_data)}条K线")

            # 保存到缓存
            if self.cache_enabled and since and until and all_data:
                cache_file = self._get_cache_file(ccxt_symbol, timeframe, since, until)
                self._save_to_cache(cache_file, all_data)

            return all_data

        except Exception as e:
            logger.error(f"CCXT K线获取失败: {ccxt_symbol} - {e}")
            return []

    def preload_data(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: Optional[str] = None
    ) -> Dict[str, List[List]]:
        """
        批量预加载多个交易对的数据

        Args:
            symbols: 交易对列表
            start_time: 开始时间
            end_time: 结束时间
            timeframe: K线周期

        Returns:
            {symbol: [[timestamp, o, h, l, c, v], ...], ...}
        """
        timeframe = timeframe or self.default_timeframe

        # 转换为毫秒时间戳
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)

        # 添加lookback
        timeframe_ms = self._timeframe_to_ms(timeframe)
        lookback_ms = self.lookback_bars * timeframe_ms
        adjusted_start = start_ts - lookback_ms

        logger.info(
            f"V8预加载数据: symbols={symbols}, "
            f"time_range={start_time.isoformat()}-{end_time.isoformat()}, "
            f"timeframe={timeframe}, lookback_bars={self.lookback_bars}"
        )

        result = {}
        for symbol in symbols:
            data = self.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=adjusted_start,
                until=end_ts
            )

            if data:
                result[symbol] = data
                logger.info(f"预加载成功: {symbol}, {len(data)}条K线")
            else:
                logger.warning(f"预加载失败: {symbol}")

        total_klines = sum(len(v) for v in result.values())
        logger.info(f"V8预加载完成: {len(result)}个交易对, 共{total_klines}条K线")

        return result

    def _timeframe_to_ms(self, timeframe: str) -> int:
        """将K线周期转换为毫秒"""
        multipliers = {
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000,
            'w': 7 * 24 * 60 * 60 * 1000,
        }

        unit = timeframe[-1].lower()
        value = int(timeframe[:-1])

        return value * multipliers.get(unit, 60 * 60 * 1000)

    def get_status(self) -> Dict[str, Any]:
        """获取数据加载器状态"""
        return {
            "exchange": self.exchange_id,
            "ccxt_initialized": self._exchange is not None,
            "cache_enabled": self.cache_enabled,
            "cache_path": str(self.cache_path),
            "default_timeframe": self.default_timeframe,
            "lookback_bars": self.lookback_bars
        }


# 便捷函数
def create_v8_data_loader(config: Optional[Dict[str, Any]] = None) -> V8BacktestDataLoader:
    """创建V8回测数据加载器实例"""
    return V8BacktestDataLoader(config)
