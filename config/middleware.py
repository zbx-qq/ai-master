import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config.logger import logger


class SimpleInterceptor(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info(f"请求路径: {request.url.path}")
        logger.info(f"请求方法: {request.method}")
        body = await request.body()
        logger.debug(f"请求体: {body.decode('utf-8') if body else '无'}")

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"响应状态码: {response.status_code} | 处理耗时: {process_time:.4f}s"
        )

        return response
