# utils/rate_limiter.py
"""频率限制器"""

import asyncio
import time
from collections import defaultdict, deque

from config.logger import logger
from utils.exceptions import RateLimitException


class RateLimiter:
    """频率限制器"""

    def __init__(
        self, max_requests: int = 10, time_window: int = 60, max_concurrent: int = 3
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.max_concurrent = max_concurrent
        self.request_history: dict[str, deque] = defaultdict(deque)
        self.concurrent_requests = 0
        self.concurrent_lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> bool:
        """检查是否允许请求"""
        current_time = time.time()
        self._cleanup_expired_requests(client_ip, current_time)

        if len(self.request_history[client_ip]) >= self.max_requests:
            logger.warning(f"IP {client_ip} 超过频率限制")
            return False

        async with self.concurrent_lock:
            if self.concurrent_requests >= self.max_concurrent:
                logger.warning(f"并发请求数达到上限: {self.concurrent_requests}")
                return False

        return True

    async def acquire(self, client_ip: str) -> None:
        """获取请求令牌"""
        if not await self.is_allowed(client_ip):
            raise RateLimitException(
                f"请求频率过高，请 {self.time_window} 秒后重试", "RATE_LIMIT_EXCEEDED"
            )

        current_time = time.time()
        self.request_history[client_ip].append(current_time)

        async with self.concurrent_lock:
            self.concurrent_requests += 1

        logger.debug(
            f"为 IP {client_ip} 分配请求令牌，当前并发: {self.concurrent_requests}"
        )

    async def release(self) -> None:
        """释放请求令牌"""
        async with self.concurrent_lock:
            if self.concurrent_requests > 0:
                self.concurrent_requests -= 1

        logger.debug(f"释放请求令牌，当前并发: {self.concurrent_requests}")

    def _cleanup_expired_requests(self, client_ip: str, current_time: float) -> None:
        """清理过期的请求记录"""
        history = self.request_history[client_ip]
        cutoff_time = current_time - self.time_window

        while history and history[0] < cutoff_time:
            history.popleft()

    def get_stats(self) -> dict[str, int]:
        """获取统计信息"""
        return {
            "total_ips": len(self.request_history),
            "concurrent_requests": self.concurrent_requests,
            "total_requests": sum(
                len(history) for history in self.request_history.values()
            ),
        }


rate_limiter = RateLimiter()
