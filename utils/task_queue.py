# utils/task_queue.py
"""任务队列管理器"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from config.logger import logger


class TaskStatus(Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CrawlerTask:
    """爬虫任务数据类"""

    task_id: str
    problems: list[str]
    click: bool
    cookies: list[dict[str, Any]]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any | None = None
    error: str | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class TaskQueue:
    """异步任务队列"""

    def __init__(self, max_concurrent_tasks: int = 3, max_queue_size: int = 100):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_queue_size = max_queue_size
        self.pending_tasks: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.running_tasks: dict[str, CrawlerTask] = {}
        self.completed_tasks: dict[str, CrawlerTask] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.worker_tasks: list[asyncio.Task] = []
        self.is_running = False

    async def start(self):
        """启动任务队列"""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"启动任务队列，最大并发数: {self.max_concurrent_tasks}")

        for i in range(self.max_concurrent_tasks):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)

    async def stop(self):
        """停止任务队列"""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("正在停止任务队列...")

        for task in self.worker_tasks:
            task.cancel()

        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()

        logger.info("任务队列已停止")

    async def submit_task(
        self, problems: list[str], click: bool, cookies: list[dict[str, Any]]
    ) -> str:
        """提交任务到队列"""
        if self.pending_tasks.qsize() >= self.max_queue_size:
            raise asyncio.QueueFull("任务队列已满")

        task_id = str(uuid.uuid4())
        task = CrawlerTask(
            task_id=task_id, problems=problems, click=click, cookies=cookies
        )

        await self.pending_tasks.put(task)
        logger.info(f"任务 {task_id} 已提交到队列")

        return task_id

    async def get_task_status(self, task_id: str) -> CrawlerTask | None:
        """获取任务状态"""
        if task_id in self.running_tasks:
            return self.running_tasks[task_id]

        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]

        pending_list = []
        while not self.pending_tasks.empty():
            try:
                task = self.pending_tasks.get_nowait()
                pending_list.append(task)
                if task.task_id == task_id:
                    for t in pending_list:
                        await self.pending_tasks.put(t)
                    return task
            except asyncio.QueueEmpty:
                break

        for task in pending_list:
            await self.pending_tasks.put(task)

        return None

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            logger.warning(f"任务 {task_id} 正在运行，无法取消")
            return False

        if task_id in self.completed_tasks:
            logger.warning(f"任务 {task_id} 已完成，无需取消")
            return False

        pending_list = []
        found = False

        while not self.pending_tasks.empty():
            try:
                task = self.pending_tasks.get_nowait()
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self.completed_tasks[task_id] = task
                    found = True
                    logger.info(f"任务 {task_id} 已取消")
                else:
                    pending_list.append(task)
            except asyncio.QueueEmpty:
                break

        for task in pending_list:
            await self.pending_tasks.put(task)

        return found

    async def _worker(self, worker_name: str):
        """工作协程"""
        logger.info(f"工作协程 {worker_name} 启动")

        try:
            while self.is_running:
                try:
                    task = await asyncio.wait_for(self.pending_tasks.get(), timeout=1.0)
                    await self._execute_task(task, worker_name)

                except TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"工作协程 {worker_name} 异常: {e}")

        except asyncio.CancelledError:
            logger.info(f"工作协程 {worker_name} 被取消")

        logger.info(f"工作协程 {worker_name} 退出")

    async def _execute_task(self, task: CrawlerTask, worker_name: str):
        """执行单个任务"""
        task_id = task.task_id

        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self.running_tasks[task_id] = task

            logger.info(f"工作协程 {worker_name} 开始执行任务 {task_id}")

            from modules.scraper import crawler

            result = await crawler(task.problems, task.click, task.cookies)

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result

            logger.info(f"任务 {task_id} 执行成功")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)

            logger.error(f"任务 {task_id} 执行失败: {e}")

        finally:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

            self.completed_tasks[task_id] = task

    def get_queue_stats(self) -> dict[str, Any]:
        """获取队列统计信息"""
        return {
            "pending_count": self.pending_tasks.qsize(),
            "running_count": len(self.running_tasks),
            "completed_count": len(self.completed_tasks),
            "max_concurrent": self.max_concurrent_tasks,
            "max_queue_size": self.max_queue_size,
            "is_running": self.is_running,
        }


task_queue = TaskQueue()
