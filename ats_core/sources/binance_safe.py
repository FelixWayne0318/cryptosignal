# coding: utf-8
"""
币安API访问（风控友好版本）

核心改进：
1. 完整的请求头（模拟浏览器）
2. 请求频率控制（rate limiter）
3. 权重追踪
4. 自动重试和降级
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union
from collections import deque
import threading

# 允许通过环境变量覆盖网关
BASE = os.environ.get("BINANCE_FAPI_BASE", "https://fapi.binance.com")

# ========== Rate Limiter（请求频率控制器）==========

class RateLimiter:
    """
    令牌桶算法实现请求频率控制

    币安限制：
    - IP限制：2400请求/分钟
    - 权重限制：6000权重/分钟

    为了安全，我们设置为：
    - 最大1200请求/分钟（50%余量）
    - 最大3000权重/分钟（50%余量）
    """

    def __init__(self, max_requests_per_minute=1200, max_weight_per_minute=3000):
        self.max_requests = max_requests_per_minute
        self.max_weight = max_weight_per_minute

        # 使用滑动窗口记录最近1分钟的请求
        self.request_times = deque()
        self.request_weights = deque()

        self.lock = threading.Lock()

    def wait_if_needed(self, weight: int = 1):
        """
        在请求前调用，如果超过限制则等待

        Args:
            weight: 本次请求的权重
        """
        with self.lock:
            now = time.time()
            cutoff = now - 60.0  # 1分钟前

            # 清理1分钟前的记录
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()
                self.request_weights.popleft()

            # 检查是否超过限制
            current_requests = len(self.request_times)
            current_weight = sum(self.request_weights)

            # 如果超过限制，等待到最早的请求过期
            if current_requests >= self.max_requests or current_weight + weight > self.max_weight:
                if self.request_times:
                    sleep_time = 60.0 - (now - self.request_times[0]) + 0.1
                    if sleep_time > 0:
                        print(f"⚠️  Rate limit reached, sleeping {sleep_time:.1f}s...")
                        time.sleep(sleep_time)
                        # 递归重试
                        return self.wait_if_needed(weight)

            # 记录本次请求
            self.request_times.append(now)
            self.request_weights.append(weight)

    def get_current_usage(self):
        """获取当前使用情况"""
        with self.lock:
            now = time.time()
            cutoff = now - 60.0

            # 清理过期记录
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()
                self.request_weights.popleft()

            return {
                'requests': len(self.request_times),
                'weight': sum(self.request_weights),
                'requests_limit': self.max_requests,
                'weight_limit': self.max_weight
            }

# 全局rate limiter实例
_rate_limiter = RateLimiter()

# ========== 改进的请求函数 ==========

def _get_safe(
    path_or_url: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 10.0,
    retries: int = 3,
    weight: int = 1,
) -> Any:
    """
    安全的GET请求，带完整请求头和频率控制

    Args:
        path_or_url: API路径或完整URL
        params: 查询参数
        timeout: 超时时间
        retries: 重试次数
        weight: 请求权重（用于rate limiting）

    Returns:
        API响应数据
    """
    # 等待rate limiter放行
    _rate_limiter.wait_if_needed(weight)

    # 构建URL
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = BASE + path_or_url

    q = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    full_url = f"{url}?{q}" if q else url

    # 构建完整的请求头（模拟浏览器）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.binance.com/",
        "Origin": "https://www.binance.com",
    }

    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(full_url, headers=headers)

            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 检查rate limit headers
                rate_limit_remaining = response.headers.get('X-MBX-USED-WEIGHT-1M')
                if rate_limit_remaining:
                    used_weight = int(rate_limit_remaining)
                    if used_weight > 5000:  # 接近6000限制
                        print(f"⚠️  Weight usage high: {used_weight}/6000")

                # 读取响应数据
                data = response.read()

                # 检查是否为gzip压缩（如果Content-Encoding是gzip）
                content_encoding = response.headers.get('Content-Encoding', '').lower()
                if content_encoding == 'gzip' or (len(data) >= 2 and data[:2] == b'\x1f\x8b'):
                    import gzip
                    data = gzip.decompress(data)

                # 解析JSON
                return json.loads(data)

        except urllib.error.HTTPError as e:
            last_err = e

            if e.code == 429:  # Rate limit exceeded
                # 币安返回429时，等待Retry-After指定的时间
                retry_after = e.headers.get('Retry-After', '60')
                sleep_time = int(retry_after)
                print(f"⚠️  Rate limit 429! Sleeping {sleep_time}s...")
                time.sleep(sleep_time)
                continue

            elif e.code == 403:  # Forbidden
                print(f"❌ 403 Forbidden - IP may be blocked by Binance")
                # 不重试，直接返回
                break

            elif e.code == 418:  # IP banned
                print(f"🚫 418 IP Banned - This IP is permanently blocked!")
                raise RuntimeError("IP banned by Binance, contact support")

            else:
                # 其他HTTP错误，等待后重试
                sleep_time = 2 ** attempt  # 指数退避
                time.sleep(sleep_time)

        except Exception as e:
            last_err = e
            # 网络错误等，等待后重试
            sleep_time = 2 ** attempt
            time.sleep(sleep_time)

    # 所有重试都失败
    if last_err:
        raise last_err
    raise RuntimeError("Unknown request error")


# ========== API 函数（使用安全版本）==========

def get_klines(
    symbol: str,
    interval: str,
    limit: int = 300,
    start_time: Optional[Union[int, float]] = None,
    end_time: Optional[Union[int, float]] = None,
) -> List[list]:
    """
    获取K线数据（风控友好版本）

    权重：根据limit计算
    - limit <= 100: weight=1
    - limit <= 500: weight=2
    - limit <= 1000: weight=5
    - limit > 1000: weight=10
    """
    symbol = symbol.upper()
    limit = int(max(1, min(int(limit), 1500)))

    # 计算权重
    if limit <= 100:
        weight = 1
    elif limit <= 500:
        weight = 2
    elif limit <= 1000:
        weight = 5
    else:
        weight = 10

    params: Dict[str, Any] = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    if start_time is not None:
        params["startTime"] = int(start_time)
    if end_time is not None:
        params["endTime"] = int(end_time)

    return _get_safe("/fapi/v1/klines", params, timeout=10.0, retries=3, weight=weight)


def get_open_interest_hist(symbol: str, period: str = "1h", limit: int = 200) -> List[dict]:
    """
    获取持仓量历史（权重=1）
    """
    symbol = symbol.upper()
    limit = int(max(1, min(int(limit), 500)))

    return _get_safe(
        "/futures/data/openInterestHist",
        {"symbol": symbol, "period": period, "limit": limit},
        timeout=8.0,
        retries=3,
        weight=1
    )


def get_funding_hist(
    symbol: str,
    limit: int = 120,
    start_time: Optional[Union[int, float]] = None,
    end_time: Optional[Union[int, float]] = None,
) -> List[dict]:
    """
    获取资金费率历史（权重=1）
    """
    symbol = symbol.upper()
    limit = int(max(1, min(int(limit), 1000)))

    params: Dict[str, Any] = {"symbol": symbol, "limit": limit}
    if start_time is not None:
        params["startTime"] = int(start_time)
    if end_time is not None:
        params["endTime"] = int(end_time)

    rows = _get_safe("/fapi/v1/fundingRate", params, timeout=8.0, retries=3, weight=1)
    return list(rows) if isinstance(rows, list) else []


def get_ticker_24h(symbol: Optional[str] = None):
    """
    获取24h统计
    权重：单个=1，全部=40
    """
    weight = 1 if symbol else 40
    params = {"symbol": symbol.upper()} if symbol else None

    return _get_safe("/fapi/v1/ticker/24hr", params, timeout=8.0, retries=3, weight=weight)


def get_rate_limiter_status():
    """获取当前rate limiter状态（用于监控）"""
    return _rate_limiter.get_current_usage()
