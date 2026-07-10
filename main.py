import asyncio
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.crawlerRequest import router
from config.logger import logger
from config.middleware import SimpleInterceptor
from utils.rate_limiter import rate_limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 GPT自动爬虫系统启动中...")

    logger.info("✅ 系统启动完成")

    yield

    # 关闭时执行
    logger.info("🛑 系统正在关闭...")
    logger.info("✅ 系统关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="GPT自动爬虫系统",
    description="基于Playwright的ChatGPT自动化交互系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求中间件
app.add_middleware(SimpleInterceptor)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """频率限制中间件"""
    client_ip = request.client.host

    try:
        await rate_limiter.acquire(client_ip)
        response = await call_next(request)
        return response

    except Exception as e:
        logger.error(f"频率限制中间件错误: {e}")
        return JSONResponse(
            status_code=429, content={"error": "rate_limit_exceeded", "message": str(e)}
        )

    finally:
        await rate_limiter.release()


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "gpt-auto-crawler",
        "version": "1.0.0",
        "timestamp": asyncio.get_event_loop().time(),
    }


@app.get("/stats")
async def get_stats():
    """获取系统统计信息"""
    return {
        "rate_limiter": rate_limiter.get_stats(),
        "system": {"python_version": sys.version, "platform": sys.platform},
    }


# 注册路由
app.include_router(router, prefix="/api/v1", tags=["crawler"])


def handle_shutdown(signum, frame):
    """处理关闭信号"""
    logger.info(f"收到关闭信号 {signum}")
    sys.exit(0)


if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("🚀 启动GPT自动爬虫系统...")

    try:
        uvicorn.run(
            app=app,
            host="0.0.0.0",
            port=8083,
            log_config=None,  # 使用自定义日志配置
            access_log=False,  # 禁用默认访问日志
        )
    except KeyboardInterrupt:
        logger.info("👋 应用被用户中断")
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        sys.exit(1)
