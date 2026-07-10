# utils/browser_manager.py
"""浏览器管理器"""

from contextlib import asynccontextmanager
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from config.logger import logger
from utils.exceptions import BrowserException


class BrowserManager:
    """浏览器管理器"""

    def __init__(
        self,
        executable_path: str = "/data/opt/google/chrome/chrome",
        headless: bool = False,
        user_agent: str = None,
        viewport: dict[str, int] = None,
    ):
        self.executable_path = executable_path
        self.headless = headless
        self.user_agent = (
            user_agent
            or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        )
        self.viewport = viewport or {"width": 1280, "height": 743}
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    @asynccontextmanager
    async def get_browser_session(self, cookies: list[dict[str, Any]] = None):
        """获取浏览器会话的上下文管理器"""
        playwright = None
        try:
            playwright = await async_playwright().start()

            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.executable_path,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            logger.info("浏览器启动成功")

            self.context = await self.browser.new_context(
                user_agent=self.user_agent,
                viewport=self.viewport,
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                },
            )

            if cookies:
                await self.context.add_cookies(cookies)
                logger.info(f"已添加 {len(cookies)} 个Cookie")

            self.page = await self.context.new_page()
            await self._inject_stealth_scripts()
            yield self

        except Exception as e:
            logger.error(f"浏览器会话创建失败: {e}")
            raise BrowserException(f"浏览器会话创建失败: {e}", "BROWSER_SESSION_FAILED")

        finally:
            await self._cleanup()
            if playwright:
                await playwright.stop()

    async def _inject_stealth_scripts(self):
        """注入反检测脚本"""
        try:
            stealth_script = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            window.chrome = {
                runtime: {},
            };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """
            await self.page.add_init_script(stealth_script)
            logger.debug("反检测脚本注入成功")
        except Exception as e:
            logger.warning(f"反检测脚本注入失败: {e}")

    async def navigate_to(self, url: str, timeout: int = 60000):
        """导航到指定URL"""
        if not self.page:
            raise BrowserException("页面未初始化", "PAGE_NOT_INITIALIZED")

        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            logger.info(f"成功导航到: {url}")
        except Exception as e:
            logger.error(f"导航失败: {e}")
            raise BrowserException(f"导航到 {url} 失败: {e}", "NAVIGATION_FAILED")

    async def wait_for_load_state(
        self, state: str = "networkidle", timeout: int = 30000
    ):
        """等待页面加载状态"""
        if not self.page:
            raise BrowserException("页面未初始化", "PAGE_NOT_INITIALIZED")

        try:
            await self.page.wait_for_load_state(state, timeout=timeout)
            logger.debug(f"页面加载状态达到: {state}")
        except Exception as e:
            logger.warning(f"等待加载状态失败: {e}")

    async def _cleanup(self):
        """清理资源"""
        try:
            if self.page:
                await self.page.close()
                logger.debug("页面已关闭")

            if self.context:
                await self.context.close()
                logger.debug("浏览器上下文已关闭")

            if self.browser:
                await self.browser.close()
                logger.info("浏览器已关闭")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")

        finally:
            self.page = None
            self.context = None
            self.browser = None
