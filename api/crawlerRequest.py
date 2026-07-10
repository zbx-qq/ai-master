import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator

from config.logger import logger
from modules.scraper import crawler
from utils.exceptions import (
    BrowserException,
    GPTCrawlerException,
    LoginException,
    NetworkException,
    RateLimitException,
    ValidationException,
)
from utils.validators import RequestValidator


class CookieModel(BaseModel):
    """Cookie数据模型"""

    name: str = Field(..., description="Cookie名称")
    value: str = Field(..., description="Cookie值")
    domain: str = Field(..., description="Cookie域名")
    path: str = Field(..., description="Cookie路径")
    secure: bool | None = Field(None, description="是否为安全Cookie")
    httpOnly: bool | None = Field(None, description="是否为HttpOnly Cookie")
    sameSite: str | None = Field(None, description="SameSite属性: Strict, Lax, None")


class CrawlerRequest(BaseModel):
    """爬虫请求模型"""

    problem: list[str] = Field(..., description="问题列表", min_items=1, max_items=10)
    click: bool = Field(default=False, description="是否启用网页搜索功能")
    cookie: list[CookieModel] = Field(..., description="Cookie数据", min_items=1)

    @validator("problem")
    def validate_problems(cls, v):
        """验证问题列表"""
        RequestValidator.validate_problems(v)
        return v

    @validator("cookie")
    def validate_cookies(cls, v):
        """验证Cookie数据"""
        cookie_dicts = [
            cookie.dict() if hasattr(cookie, "dict") else cookie for cookie in v
        ]
        RequestValidator.validate_cookies(cookie_dicts)
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "problem": ["推荐一款游戏电脑", "Python编程入门建议"],
                "click": True,
                "cookie": [
                    {
                        "name": "session_token",
                        "value": "your_session_token_value",
                        "domain": ".chatgpt.com",
                        "path": "/",
                    }
                ],
            }
        }


class CrawlerResponse(BaseModel):
    """爬虫响应模型"""

    question: str = Field(..., description="问题内容")
    time: str = Field(..., description="处理时间")
    payload: dict[str, Any] = Field(..., description="请求载荷")
    answer: list[dict[str, Any]] = Field(..., description="响应数据")
    message_content: str | None = Field(None, description="提取的消息内容")


class ErrorResponse(BaseModel):
    """错误响应模型"""

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    error_code: str | None = Field(None, description="错误代码")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="错误时间"
    )


router = APIRouter()


@router.post(
    "/crawler",
    response_model=list[CrawlerResponse],
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        401: {"model": ErrorResponse, "description": "认证失败"},
        429: {"model": ErrorResponse, "description": "请求频率过高"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
async def run_crawler(request: CrawlerRequest):
    """
    执行GPT爬虫任务

    - **problem**: 问题列表，支持1-10个问题
    - **click**: 是否启用网页搜索功能
    - **cookie**: 有效的ChatGPT登录Cookie
    """
    try:
        logger.info(f"收到爬虫请求，问题数量: {len(request.problem)}")

        cookie_data = [
            cookie.dict() if hasattr(cookie, "dict") else cookie
            for cookie in request.cookie
        ]

        for i, cookie in enumerate(cookie_data):
            logger.debug(
                f"Cookie {i + 1}: name={cookie.get('name')}, domain={cookie.get('domain')}, secure={cookie.get('secure')}"
            )

        result = await crawler(request.problem, request.click, cookie_data)
        logger.info(f"爬虫任务完成，获得响应数量: {len(result)}")

    except ValidationException as e:
        logger.warning(f"请求验证失败: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="validation_error", message=e.message, error_code=e.error_code
            ).dict(),
        )

    except LoginException as e:
        logger.error(f"登录验证失败: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error="login_failed", message=e.message, error_code=e.error_code
            ).dict(),
        )

    except RateLimitException as e:
        logger.warning(f"频率限制: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error="rate_limit_exceeded", message=e.message, error_code=e.error_code
            ).dict(),
        )

    except (BrowserException, NetworkException) as e:
        logger.error(f"技术异常: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="technical_error",
                message="服务暂时不可用，请稍后重试",
                error_code=e.error_code,
            ).dict(),
        )

    except GPTCrawlerException as e:
        logger.error(f"爬虫异常: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="crawler_error", message=e.message, error_code=e.error_code
            ).dict(),
        )

    except Exception as e:
        logger.error(f"未预期的异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="internal_error", message="服务器内部错误，请联系管理员"
            ).dict(),
        )

    filtered = [
        item
        for item in result
        if item["url"] == "https://chatgpt.com/backend-api/f/conversation"
    ]

    response_data = []

    for i, item in enumerate(filtered):
        question_text = (
            request.problem[i] if i < len(request.problem) else f"question_{i + 1}"
        )
        body = item.get("body", "")
        payload = json.loads(item.get("payload", ""))
        lines = body.splitlines()
        parsed = []
        current_event = None

        for line in lines:
            line = line.strip()
            if line.startswith("event:"):
                current_event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:") :].strip()
                if data_str == "[DONE]":
                    continue
                try:
                    data_value = json.loads(data_str)
                except json.JSONDecodeError:
                    data_value = data_str
                parsed.append({"event": current_event, "data": data_value})

        response_data.append(
            {
                "question": question_text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "payload": payload,
                "answer": parsed,
            }
        )

    return response_data
