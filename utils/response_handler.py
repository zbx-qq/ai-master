# utils/response_handler.py
"""响应处理器"""

import asyncio
import json
from datetime import datetime
from typing import Any

from config.logger import logger
from utils.exceptions import NetworkException


class ResponseHandler:
    """响应处理器"""

    def __init__(self):
        self.responses: list[dict[str, Any]] = []
        self.response_lock = asyncio.Lock()

    async def handle_response(self, response) -> None:
        """处理HTTP响应"""
        try:
            url = response.url
            if self._is_target_response(url, response.request.method):
                await self._process_response(response)
        except Exception as e:
            logger.error(f"响应处理出错: {e}")

    def _is_target_response(self, url: str, method: str) -> bool:
        """判断是否为目标响应"""
        return (
            "conversation" in url
            and method == "POST"
            and "backend-api/f/conversation" in url
        )

    async def _process_response(self, response) -> None:
        """处理目标响应"""
        try:
            body = await response.text()
            payload = response.request.post_data

            async with self.response_lock:
                self.responses.append(
                    {
                        "url": response.url,
                        "body": body,
                        "payload": payload,
                        "timestamp": datetime.now(),
                        "status_code": response.status,
                        "headers": dict(response.headers),
                    }
                )

            logger.debug(f"成功处理响应: {response.url}")

        except Exception as e:
            logger.error(f"处理响应内容失败: {e}")
            raise NetworkException(
                f"处理响应内容失败: {e}", "RESPONSE_PROCESSING_FAILED"
            )

    async def get_responses(self) -> list[dict[str, Any]]:
        """获取所有响应"""
        async with self.response_lock:
            return self.responses.copy()

    async def clear_responses(self) -> None:
        """清空响应列表"""
        async with self.response_lock:
            self.responses.clear()

    def get_response_count(self) -> int:
        """获取响应数量"""
        return len(self.responses)


class SSEParser:
    """服务器发送事件解析器"""

    @staticmethod
    def parse_sse_data(body: str) -> list[dict[str, Any]]:
        """解析SSE数据"""
        if not body:
            return []

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

                parsed.append(
                    {
                        "event": current_event,
                        "data": data_value,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return parsed

    @staticmethod
    def extract_message_content(parsed_data: list[dict[str, Any]]) -> str:
        """从解析数据中提取消息内容"""
        content_parts = []

        for item in parsed_data:
            if isinstance(item.get("data"), dict):
                data = item["data"]

                if "message" in data and "content" in data["message"]:
                    message_content = data["message"]["content"]
                    if isinstance(message_content, dict) and "parts" in message_content:
                        content_parts.extend(message_content["parts"])
                    elif isinstance(message_content, str):
                        content_parts.append(message_content)

        return "".join(content_parts) if content_parts else ""
