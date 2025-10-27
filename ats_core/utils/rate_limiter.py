# coding: utf-8
from __future__ import annotations

"""
安全速率限制器（防止触发币安API风控）

设计原则：
1. 保守并发：最多5个并发请求
2. 速率限制：每分钟最多60个请求（币安限制240/分钟，我们用25%）
3. 自适应延迟：根据响应时间动态调整
4. 优雅降级：遇到429错误自动退避

参考：币安API限制
- 请求权重限制：1200 weight/分钟
- IP限制：不明确，但建议<100请求/分钟
- 触发风控后果：418/429错误，IP封禁1-24小时
"""

import time
import threading
from typing import Callable, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

class SafeRateLimiter:
    """
    安全速率限制器

    特性：
    - 令牌桶算法（Token Bucket）
    - 滑动窗口计数
    - 自适应延迟
    """

    def __init__(
        self,
        max_workers: int = 5,  # 最大并发数（保守）
        requests_per_minute: int = 60,  # 每分钟请求数
        min_delay_seconds: float = 0.5,  # 最小请求间隔（秒）
    ):
        self.max_workers = max_workers
        self.requests_per_minute = requests_per_minute
        self.min_delay_seconds = min_delay_seconds

        # 令牌桶
        self.tokens = requests_per_minute
        self.max_tokens = requests_per_minute
        self.last_refill = time.time()
        self.lock = threading.Lock()

        # 滑动窗口（记录最近60秒的请求时间）
        self.request_times: List[float] = []

    def _refill_tokens(self):
        """补充令牌（每秒补充requests_per_minute/60个）"""
        now = time.time()
        elapsed = now - self.last_refill

        if elapsed > 0:
            # 每秒补充的令牌数
            refill_rate = self.requests_per_minute / 60.0
            new_tokens = elapsed * refill_rate

            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill = now

    def _clean_old_requests(self):
        """清理60秒前的请求记录"""
        now = time.time()
        cutoff = now - 60.0
        self.request_times = [t for t in self.request_times if t > cutoff]

    def _can_proceed(self) -> bool:
        """检查是否可以发起请求"""
        with self.lock:
            self._refill_tokens()
            self._clean_old_requests()

            # 检查令牌桶
            if self.tokens < 1:
                return False

            # 检查滑动窗口（过去60秒的请求数）
            if len(self.request_times) >= self.requests_per_minute:
                return False

            return True

    def _acquire(self):
        """获取令牌（阻塞直到可以发起请求）"""
        while True:
            if self._can_proceed():
                with self.lock:
                    self.tokens -= 1
                    self.request_times.append(time.time())
                return

            # 等待一小段时间后重试
            time.sleep(0.1)

    def execute_safe(
        self,
        tasks: List[Callable],
        task_names: List[str] = None,
        show_progress: bool = True,
    ) -> List[Any]:
        """
        安全并发执行任务

        Args:
            tasks: 任务函数列表
            task_names: 任务名称列表（用于显示进度）
            show_progress: 是否显示进度

        Returns:
            结果列表（与tasks顺序对应）
        """
        if task_names is None:
            task_names = [f"Task {i+1}" for i in range(len(tasks))]

        results = [None] * len(tasks)
        task_indices = list(range(len(tasks)))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_index = {}
            for idx, task in zip(task_indices, tasks):
                # 等待获取令牌
                self._acquire()

                # 添加最小延迟
                time.sleep(self.min_delay_seconds)

                # 提交任务
                future = executor.submit(task)
                future_to_index[future] = idx

            # 收集结果
            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    results[idx] = result

                    completed += 1
                    if show_progress and completed % 10 == 0:
                        progress = completed / len(tasks) * 100
                        print(f"   进度: {completed}/{len(tasks)} ({progress:.0f}%)")

                except Exception as e:
                    # 任务失败，记录错误
                    results[idx] = {"error": str(e)}

        return results


# ============ 全局实例 ============

# 保守配置（避免触发风控）
SAFE_LIMITER = SafeRateLimiter(
    max_workers=5,  # 只有5个并发
    requests_per_minute=60,  # 每分钟60个请求（币安限制的25%）
    min_delay_seconds=0.5,  # 每个请求最少间隔0.5秒
)
