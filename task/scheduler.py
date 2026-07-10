#!/usr/bin/env python3
"""
爬虫任务调度器
持续从API拉取任务并使用爬虫处理它们
Crawler Task Scheduler
Continuously pulls tasks from the API and processes them using the crawler.
"""
import asyncio
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.logger import logger
from modules.scraper import crawler

API_BASE_URL = os.getenv("API_BASE_URL", "https://scheduler-api-714429769595.asia-southeast1.run.app/api/v1")
API_KEY = os.getenv("API_KEY", "")
SLEEP_INTERVAL = 60
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2


def create_session_with_retries() -> requests.Session:
    """创建带有重试逻辑的HTTP会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def pull_task(session: requests.Session) -> Optional[Dict[str, Any]]:
    """从API拉取一个任务"""
    url = f"{API_BASE_URL}/tasks/crawler/pull"
    params = {"ai_agent": "chatgpt"}
    headers = {"X-API-Key": API_KEY}

    try:
        logger.info(f"从API拉取任务: {url}")
        response = session.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        task_data = response.json()

        required_fields = ["task_id", "question_id", "prompts", "cookie"]
        missing_fields = [field for field in required_fields if field not in task_data]

        if missing_fields:
            logger.error(f"任务缺少必需字段: {missing_fields}")
            return None

        logger.info(f"成功拉取任务: {task_data['task_id']}")
        return task_data

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug("暂无可用任务")
        else:
            logger.error(f"拉取任务时HTTP错误: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"拉取任务时网络错误: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"解析任务响应失败: {e}")
    except Exception as e:
        logger.error(f"拉取任务时发生意外错误: {e}", exc_info=True)

    return None


async def process_task(task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """处理一个爬虫任务"""
    task_id = task_data["task_id"]
    prompts = task_data.get("prompts", [])
    cookie_data = task_data.get("cookie", {})
    websearch_required = task_data.get("websearch_required", False)

    if not prompts:
        logger.error(f"任务 {task_id} 没有prompts")
        return None

    cookies_dict = cookie_data.get("cookies", {})

    if not cookies_dict:
        logger.error(f"任务 {task_id} 的Cookie数据为空")
        logger.error(f"收到的Cookie数据: {cookie_data}")
        return None

    cookies_list = []
    for cookie_name, cookie_value in cookies_dict.items():
        cookie_obj = {
            "name": cookie_name,
            "value": cookie_value,
            "domain": ".chatgpt.com",
            "path": "/"
        }
        cookies_list.append(cookie_obj)

    logger.info(f"处理任务 {task_id}，包含 {len(prompts)} 个prompt，{len(cookies_list)} 个cookie")

    try:
        start_time = time.time()
        result = await crawler(prompts, websearch_required, cookies_list)
        execution_time = time.time() - start_time

        if not result:
            logger.warning(f"任务 {task_id} 返回空结果")
            return None

        filtered = [
            item for item in result
            if item.get("url") == "https://chatgpt.com/backend-api/f/conversation"
        ]

        if not filtered:
            logger.warning(f"任务 {task_id} 没有对话API响应")
            return None

        logger.info(f"任务 {task_id} 找到 {len(filtered)} 个对话响应")
        response_item = filtered[0]
        body = response_item.get("body", "")
        payload = json.loads(response_item.get("payload", "{}"))

        result_data = {
            "task_id": task_id,
            "question_id": task_data.get("question_id"),
            "prompts": prompts,
            "payload": payload,
            "raw_response": body,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"任务 {task_id} 处理成功，耗时 {execution_time:.2f}秒")
        return result_data

    except json.JSONDecodeError as e:
        logger.error(f"任务 {task_id} JSON解析失败: {e}")
    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {e}", exc_info=True)

    return None


def submit_task_result(session: requests.Session, task_id: str,
                       success: bool, answer_content: Optional[str] = None,
                       error_message: Optional[str] = None,
                       execution_time: Optional[float] = None) -> bool:
    """提交任务结果到API"""
    url = f"{API_BASE_URL}/tasks/crawler/submit"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "task_id": task_id,
        "success": success
    }

    if success and answer_content:
        payload["answer_content"] = answer_content
        payload["metadata"] = {
            "model": "gpt-4",
            "execution_time": execution_time or 0,
            "processed_at": datetime.now().isoformat()
        }
    else:
        payload["error_message"] = error_message or "Unknown error"

    try:
        logger.info(f"提交任务 {task_id} 的结果 (成功={success})")
        response = session.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        logger.info(f"成功提交任务 {task_id} 的结果")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"提交任务 {task_id} 的结果失败: {e}")
    except Exception as e:
        logger.error(f"提交任务 {task_id} 的结果时发生意外错误: {e}", exc_info=True)

    return False


async def process_and_submit_task(session: requests.Session, task_data: Dict[str, Any]) -> None:
    """处理任务并提交结果"""
    task_id = task_data["task_id"]

    try:
        result_data = await process_task(task_data)

        if result_data:
            answer_content = result_data.get("raw_response", "")
            submit_task_result(
                session=session,
                task_id=task_id,
                success=True,
                answer_content=answer_content,
                execution_time=result_data.get("execution_time")
            )
        else:
            cookie_data = task_data.get("cookie", {})
            cookies_dict = cookie_data.get("cookies", {})

            if not cookies_dict:
                error_msg = "Invalid cookie format: missing 'cookies' field in cookie data. Backend should return {'cookies': {'cookie-name': 'cookie-value'}}."
            else:
                error_msg = "Failed to process task: No valid results"

            submit_task_result(
                session=session,
                task_id=task_id,
                success=False,
                error_message=error_msg
            )

    except Exception as e:
        logger.error(f"任务 {task_id} 处理流程出错: {e}", exc_info=True)
        submit_task_result(
            session=session,
            task_id=task_id,
            success=False,
            error_message=f"Exception: {str(e)}"
        )


async def main_loop():
    """主循环：持续拉取并处理任务"""
    logger.info("启动爬虫任务调度器")
    session = create_session_with_retries()

    while True:
        try:
            task_data = pull_task(session)

            if task_data:
                await process_and_submit_task(session, task_data)
            else:
                logger.debug(f"无可用任务，睡眠 {SLEEP_INTERVAL} 秒")
                await asyncio.sleep(SLEEP_INTERVAL)

        except KeyboardInterrupt:
            logger.info("收到中断信号，正在优雅关闭")
            break
        except Exception as e:
            logger.error(f"主循环发生意外错误: {e}", exc_info=True)
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("调度器已被用户停止")
    except Exception as e:
        logger.error(f"致命错误: {e}", exc_info=True)
