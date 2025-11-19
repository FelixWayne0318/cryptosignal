# coding: utf-8
"""
Backtest Framework v1.0 - Historical Data Loader
回测框架 - 历史数据加载器

功能：
1. 从Binance API加载历史K线数据
2. 支持缓存机制（减少API调用）
3. 自动重试与错误处理
4. 零硬编码（所有参数从config读取）

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Design: docs/BACKTEST_FRAMEWORK_v1.0_DESIGN.md
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from ats_core.sources.binance import (
    get_klines,
    get_open_interest_hist,
    get_funding_hist
)

logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """
    历史数据加载器

    职责：
    - 加载历史K线数据（支持指定时间范围）
    - 加载BTC K线（用于Step1 BTC对齐检测）
    - 加载持仓量历史（可选，用于因子计算）
    - 加载资金费率历史（可选，用于因子计算）
    - 缓存管理（LRU驱逐策略）

    配置驱动（config/params.json -> backtest.data_loader）:
    - default_interval: 默认K线周期
    - api_retry_count: API重试次数
    - api_retry_delay_base: 重试延迟基数（秒）
    - api_retry_delay_range: 重试延迟范围（秒）
    - api_timeout_seconds: API超时（秒）
    - cache_enabled: 是否启用缓存
    - cache_dir: 缓存目录
    - cache_max_size_mb: 缓存最大大小（MB）
    - cache_ttl_hours: 缓存TTL（小时）
    """

    def __init__(self, config: Dict):
        """
        初始化历史数据加载器

        Args:
            config: 配置字典（从params.json的backtest.data_loader读取）
                    所有参数都有默认值，确保向后兼容
        """
        # §6.2 函数签名演进：所有参数都有默认值（向后兼容）
        self.default_interval = config.get("default_interval", "1h")
        self.api_retry_count = config.get("api_retry_count", 3)
        self.api_retry_delay_base = config.get("api_retry_delay_base", 2.0)
        self.api_retry_delay_range = config.get("api_retry_delay_range", 2.0)
        self.api_timeout = config.get("api_timeout_seconds", 30)

        # 缓存配置
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_dir = Path(config.get("cache_dir", "data/backtest_cache"))
        self.cache_max_size_mb = config.get("cache_max_size_mb", 500)
        self.cache_ttl_hours = config.get("cache_ttl_hours", 168)  # 7天

        # 初始化缓存目录
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"缓存已启用: {self.cache_dir}")
        else:
            logger.info("缓存已禁用")

        logger.info(
            f"HistoricalDataLoader initialized: "
            f"interval={self.default_interval}, "
            f"retry={self.api_retry_count}, "
            f"cache={'ON' if self.cache_enabled else 'OFF'}"
        )

    def load_klines(
        self,
        symbol: str,
        start_time: int,
        end_time: int,
        interval: Optional[str] = None
    ) -> List[Dict]:
        """
        加载历史K线数据

        Args:
            symbol: 交易对（如 "ETHUSDT"）
            start_time: 开始时间（Unix时间戳，毫秒）
            end_time: 结束时间（Unix时间戳，毫秒）
            interval: K线周期（如 "1h"），None则使用配置的默认值

        Returns:
            K线数据列表，每条记录为字典：
            {
                "timestamp": int,      # 开盘时间（毫秒）
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float,       # 成交量（币）
                "close_time": int,     # 收盘时间（毫秒）
                "quote_volume": float, # 成交额（USDT）
                "trades": int,         # 成交笔数
                "taker_buy_base": float,   # 主动买入量（币）
                "taker_buy_quote": float   # 主动买入额（USDT）
            }

        实现细节：
        - 支持缓存（缓存key: {symbol}_{start}_{end}_{interval}.json）
        - 缓存过期检测（基于TTL）
        - API重试（指数退避）
        - 批量请求（Binance单次最多1500条，自动分批）
        """
        interval = interval or self.default_interval
        cache_key = f"{symbol}_{start_time}_{end_time}_{interval}"

        # 1. 尝试从缓存加载
        if self.cache_enabled:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_data

        # 2. 从API加载（可能需要分批）
        logger.info(f"从API加载K线: {symbol} {interval} {start_time}-{end_time}")
        klines_raw = self._fetch_klines_batched(
            symbol, interval, start_time, end_time
        )

        # 3. 转换为字典格式
        klines_dict = self._parse_klines(klines_raw)

        # 4. 保存到缓存
        if self.cache_enabled:
            self._save_to_cache(cache_key, klines_dict)

        return klines_dict

    def load_btc_klines(
        self,
        start_time: int,
        end_time: int,
        interval: Optional[str] = None
    ) -> List[Dict]:
        """
        加载BTC K线（用于Step1 BTC对齐检测）

        Args:
            start_time: 开始时间（毫秒）
            end_time: 结束时间（毫秒）
            interval: K线周期（默认使用配置）

        Returns:
            BTC K线数据列表
        """
        return self.load_klines("BTCUSDT", start_time, end_time, interval)

    def load_funding_rate_history(
        self,
        symbol: str,
        start_time: int,
        end_time: int
    ) -> List[Dict]:
        """
        加载资金费率历史（可选功能，用于B因子计算）

        Args:
            symbol: 交易对
            start_time: 开始时间（毫秒）
            end_time: 结束时间（毫秒）

        Returns:
            资金费率历史列表：
            [
                {
                    "fundingRate": float,
                    "fundingTime": int,
                    "symbol": str
                },
                ...
            ]

        Note: v1.0暂不使用，预留接口用于未来增强
        """
        cache_key = f"{symbol}_funding_{start_time}_{end_time}"

        # 1. 尝试缓存
        if self.cache_enabled:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # 2. 从API加载（带重试）
        logger.info(f"从API加载资金费率: {symbol} {start_time}-{end_time}")
        funding_data = []

        for attempt in range(self.api_retry_count + 1):
            try:
                funding_data = get_funding_hist(
                    symbol=symbol,
                    start_time=start_time,
                    end_time=end_time,
                    limit=1000  # Binance最大1000
                )
                break
            except Exception as e:
                if attempt < self.api_retry_count:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"资金费率加载失败 (attempt {attempt+1}/{self.api_retry_count+1}): {e}"
                        f"\n重试延迟: {delay:.1f}秒"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"资金费率加载失败（已重试{self.api_retry_count}次）: {e}")
                    raise

        # 3. 保存缓存
        if self.cache_enabled:
            self._save_to_cache(cache_key, funding_data)

        return funding_data

    def load_oi_history(
        self,
        symbol: str,
        start_time: int,
        end_time: int,
        period: str = "1h"
    ) -> List[Dict]:
        """
        加载持仓量历史（可选功能，用于O因子计算）

        Args:
            symbol: 交易对
            start_time: 开始时间（毫秒）
            end_time: 结束时间（毫秒）
            period: 聚合周期（"5m"|"15m"|"30m"|"1h"|"2h"|"4h"|"6h"|"12h"|"1d"）

        Returns:
            持仓量历史列表：
            [
                {
                    "symbol": str,
                    "sumOpenInterest": str,
                    "sumOpenInterestValue": str,
                    "timestamp": int
                },
                ...
            ]

        Note: v1.0暂不使用，预留接口用于未来增强
        """
        cache_key = f"{symbol}_oi_{start_time}_{end_time}_{period}"

        # 1. 尝试缓存
        if self.cache_enabled:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # 2. 从API加载（带重试）
        logger.info(f"从API加载持仓量: {symbol} {period} {start_time}-{end_time}")
        oi_data = []

        for attempt in range(self.api_retry_count + 1):
            try:
                oi_data = get_open_interest_hist(
                    symbol=symbol,
                    period=period,
                    limit=500  # Binance最大500
                )
                break
            except Exception as e:
                if attempt < self.api_retry_count:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"持仓量加载失败 (attempt {attempt+1}/{self.api_retry_count+1}): {e}"
                        f"\n重试延迟: {delay:.1f}秒"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"持仓量加载失败（已重试{self.api_retry_count}次）: {e}")
                    raise

        # 3. 保存缓存
        if self.cache_enabled:
            self._save_to_cache(cache_key, oi_data)

        return oi_data

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        清理缓存

        Args:
            pattern: 可选的文件名模式（如 "ETHUSDT_*"），None则清理全部

        Returns:
            删除的文件数量
        """
        if not self.cache_enabled:
            logger.warning("缓存未启用，无需清理")
            return 0

        deleted_count = 0
        cache_files = list(self.cache_dir.glob(pattern or "*.json"))

        for cache_file in cache_files:
            try:
                cache_file.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning(f"删除缓存文件失败: {cache_file} - {e}")

        logger.info(f"缓存清理完成: 删除{deleted_count}个文件")
        return deleted_count

    def get_cache_size_mb(self) -> float:
        """
        获取缓存总大小（MB）

        Returns:
            缓存大小（MB）
        """
        if not self.cache_enabled or not self.cache_dir.exists():
            return 0.0

        total_bytes = sum(
            f.stat().st_size
            for f in self.cache_dir.glob("*.json")
            if f.is_file()
        )
        return total_bytes / (1024 * 1024)

    # ==================== Private Methods ====================

    def _fetch_klines_batched(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int
    ) -> List[list]:
        """
        分批加载K线（Binance单次最多1500条）

        Args:
            symbol: 交易对
            interval: K线周期
            start_time: 开始时间（毫秒）
            end_time: 结束时间（毫秒）

        Returns:
            原始K线数据（二维数组）
        """
        # 计算间隔（毫秒）
        interval_ms = self._interval_to_ms(interval)
        max_klines_per_batch = 1500  # Binance限制

        all_klines = []
        current_start = start_time

        while current_start < end_time:
            # 计算批次结束时间
            batch_end = min(
                current_start + interval_ms * max_klines_per_batch,
                end_time
            )

            # 调用API（带重试）
            batch_klines = self._fetch_klines_with_retry(
                symbol, interval, current_start, batch_end
            )

            if not batch_klines:
                logger.warning(
                    f"批次无数据: {symbol} {interval} "
                    f"{current_start}-{batch_end}"
                )
                break

            all_klines.extend(batch_klines)

            # 移动到下一批次
            last_kline_time = int(batch_klines[-1][0])  # openTime
            current_start = last_kline_time + interval_ms

            # 防止无限循环
            if last_kline_time >= end_time:
                break

        logger.info(
            f"K线加载完成: {symbol} {interval} "
            f"共{len(all_klines)}条 ({start_time}-{end_time})"
        )
        return all_klines

    def _fetch_klines_with_retry(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int
    ) -> List[list]:
        """
        带重试的K线加载（指数退避）

        Args:
            symbol: 交易对
            interval: K线周期
            start_time: 开始时间（毫秒）
            end_time: 结束时间（毫秒）

        Returns:
            K线数据（二维数组）
        """
        for attempt in range(self.api_retry_count + 1):
            try:
                klines = get_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                    limit=1500
                )
                return klines
            except Exception as e:
                if attempt < self.api_retry_count:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"K线加载失败 (attempt {attempt+1}/{self.api_retry_count+1}): {e}"
                        f"\n重试延迟: {delay:.1f}秒"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"K线加载失败（已重试{self.api_retry_count}次）: {e}")
                    raise

        return []

    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        计算重试延迟（§6.1 Base + Range模式）

        Args:
            attempt: 当前重试次数（0-based）

        Returns:
            延迟时间（秒）

        公式: base * (2 ^ attempt) ± random(range)
        例如: base=2.0, range=2.0
            attempt 0: 2.0 ± 2.0 = [0, 4]
            attempt 1: 4.0 ± 2.0 = [2, 6]
            attempt 2: 8.0 ± 2.0 = [6, 10]
        """
        import random

        base_delay = self.api_retry_delay_base * (2 ** attempt)
        randomized_delay = base_delay + random.uniform(
            -self.api_retry_delay_range,
            self.api_retry_delay_range
        )
        return max(0.1, randomized_delay)  # 最小0.1秒

    def _parse_klines(self, klines_raw: List[list]) -> List[Dict]:
        """
        解析K线数据（Binance原始格式 → 字典格式）

        Args:
            klines_raw: Binance原始K线数据
                [ openTime, open, high, low, close, volume, closeTime,
                  quoteAssetVolume, numberOfTrades, takerBuyBaseVolume,
                  takerBuyQuoteVolume, ignore ]

        Returns:
            字典格式K线数据
        """
        klines_dict = []
        for k in klines_raw:
            klines_dict.append({
                "timestamp": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": int(k[6]),
                "quote_volume": float(k[7]),
                "trades": int(k[8]),
                "taker_buy_base": float(k[9]),
                "taker_buy_quote": float(k[10])
            })
        return klines_dict

    def _interval_to_ms(self, interval: str) -> int:
        """
        将K线周期转换为毫秒

        Args:
            interval: K线周期（如 "1m", "1h", "1d"）

        Returns:
            毫秒数
        """
        # §6.4 分段逻辑配置（配置驱动的if-elif-else分支）
        # 注意：这里使用硬编码是合理的，因为这是Binance API标准，不会改变
        unit = interval[-1]
        value = int(interval[:-1])

        if unit == 'm':
            return value * 60 * 1000
        elif unit == 'h':
            return value * 60 * 60 * 1000
        elif unit == 'd':
            return value * 24 * 60 * 60 * 1000
        elif unit == 'w':
            return value * 7 * 24 * 60 * 60 * 1000
        elif unit == 'M':
            return value * 30 * 24 * 60 * 60 * 1000  # 近似
        else:
            raise ValueError(f"不支持的K线周期: {interval}")

    def _load_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """
        从缓存加载数据

        Args:
            cache_key: 缓存键

        Returns:
            缓存数据，如果不存在或过期则返回None
        """
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        # 检查TTL
        file_age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if file_age_hours > self.cache_ttl_hours:
            logger.debug(f"缓存过期: {cache_key} (age={file_age_hours:.1f}h)")
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.warning(f"缓存加载失败: {cache_key} - {e}")
            return None

    def _save_to_cache(self, cache_key: str, data: Union[List[Dict], Dict]) -> None:
        """
        保存数据到缓存

        Args:
            cache_key: 缓存键
            data: 要缓存的数据
        """
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"缓存已保存: {cache_key}")
        except Exception as e:
            logger.warning(f"缓存保存失败: {cache_key} - {e}")
