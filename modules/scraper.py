# modules/scraper.py
"""
Improved scraper with incremental enhancements
Maintains backward compatibility while fixing core issues

改进说明 (2025-10-23):
1. 修复输入框选择问题
   - ChatGPT使用contenteditable div作为主要输入方式，而非textarea
   - textarea元素被隐藏(display: none)仅作为后备方案
   - 优先使用 #prompt-textarea[contenteditable="true"] 选择器
   - 如果找不到或不可见，则回退到textarea元素

2. 优化页面导航逻辑
   - 移除了 wait_for_load_state("networkidle") 等待
   - ChatGPT持续保持WebSocket连接和轮询请求，永远无法达到networkidle状态
   - 改用domcontentloaded + 固定等待时间(2秒)确保页面稳定

3. 改进响应完成检测
   - 使用停止按钮 button[data-testid="stop-button"] 作为生成状态指示器
   - 当停止按钮消失时，表示生成完成
   - 检测间隔缩短至0.5秒，提高响应速度
   - 移除了之前依赖的regenerate按钮和textarea状态检查

4. 增强错误处理和日志记录
   - 在关键步骤添加调试日志
   - 记录使用的输入方法(contenteditable vs textarea)
   - 记录生成状态(进行中 vs 已完成)
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Coroutine

from playwright.async_api import Page, Response, async_playwright

from config.logger import logger
from config.settings import settings
from utils.exceptions import BrowserException, LoginException, NetworkException
import base64


@dataclass
class QuestionResponse:
    """Track question-response correlation"""

    question_id: str
    question_text: str
    responses: list[dict[str, Any]] = field(default_factory=list)
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"  # pending, processing, completed, failed


class ImprovedResponseTracker:
    """Track responses and correlate them with questions"""

    def __init__(self):
        self.questions: dict[str, QuestionResponse] = {}
        self.current_question_id: str | None = None
        self.lock = asyncio.Lock()

    def create_question(self, question_text: str) -> str:
        """Create a new question tracking entry"""
        question_id = str(uuid.uuid4())
        self.questions[question_id] = QuestionResponse(
            question_id=question_id, question_text=question_text
        )
        return question_id

    async def add_response(self, response_data: dict[str, Any]):
        """Add response data to current question"""
        async with self.lock:
            if self.current_question_id and self.current_question_id in self.questions:
                self.questions[self.current_question_id].responses.append(response_data)

    def get_question(self, question_id: str) -> QuestionResponse | None:
        """Get question by ID"""
        return self.questions.get(question_id)


async def crawler(
    problem_list: list[str], click: bool, cookie: list, connector: str,task_id: str
) :
    """
    Improved crawler with better response tracking and error handling

    Improvements:
    1. Question-response correlation tracking
    2. Smart waiting based on page state
    3. Better error classification
    4. Proper timeout handling
    """
    tracker = ImprovedResponseTracker()
    arraylist = []
    return_result = {}
    async with async_playwright() as p:
        try:
            # Launch browser with proper error handling
            browser = await launch_browser(p)
            context = await create_browser_context(browser, cookie)
            page = await context.new_page()

            # Setup response interception with tracker
            page.on(
                "response",
                lambda response: asyncio.ensure_future(
                    handle_response(response, arraylist, task_id)
                ),
            )

            # Navigate with retry
            await navigate_with_retry(page, "https://chatgpt.com")

            # Verify login
            # await check_login(page)
            try:
                # 检查弹窗是否存在
                popup = await page.query_selector('div[data-testid="modal-free-trial-upsell"]')
                if popup:
                    # 弹窗存在，点击关闭按钮
                    close_button = await page.query_selector('button[data-testid="close-button"]')
                    if close_button:
                        await close_button.click()
                        logger.info("Trial popup closed successfully.")
                    else:
                        logger.warning("Close button not found in the popup.")
                else:
                    logger.info("No trial popup found.")
            except Exception as e:
                logger.error(f"Error while closing trial popup: {e}")

            try:
                # 检查弹窗是否存在
                close_button = await page.query_selector('button[data-testid="close-button"]')

                if close_button:
                    # 如果找到了关闭按钮，点击它关闭弹窗
                    await close_button.click()
                    logger.info("Popup closed successfully")
                else:
                    logger.info("No popup found")

            except Exception as e:
                logger.error(f"Error while closing popup: {e}")

                # 检查并关闭 Business 弹窗
            try:
                # 等待弹窗出现，并且确保弹窗处于打开状态
                popup = await page.query_selector('div#radix-_r_8_[data-state="open"]')
                if popup:
                    logger.info("Business popup found.")

                    # 等待并点击 "Maybe later" 按钮
                    maybe_later_button = await page.query_selector('button:has-text("Maybe later")')
                    if maybe_later_button:
                        # 确保按钮可点击
                        await maybe_later_button.scroll_into_view_if_needed()
                        await maybe_later_button.click()
                        logger.info("Business popup closed by clicking 'Maybe later'")
                    else:
                        logger.warning("'Maybe later' button not found in the popup")

                else:
                    logger.info("No Business popup found")
            except Exception as e:
                logger.error(f"Error while closing Business popup: {e}")

            # Configure web search if requested
            if click:
                # if not connector:
               await enable_web_search(page)
               # Process questions with improved tracking
               results = await process_questions(page, problem_list, tracker)
               await browser.close()
               return_result.update({"response": arraylist})
               return arraylist

                # else:
                #
                # #mcp选择未添加的应用
                #
                #    results = []
                #    for i, question in enumerate(problem_list):
                #        # Create question tracking
                #        question_id = tracker.create_question(question)
                #        tracker.current_question_id = question_id
                #
                #        logger.info(f"Processing question {i + 1}/{len(question)}: {question[:50]}...")
                #
                #        try:
                #            # Submit question
                #            #await submit_question(page, question)
                #            await page.type("textarea", "/")
                #            await asyncio.sleep(2)
                #            await page.get_by_text(connector, exact=True).click(timeout=10000)
                #            await asyncio.sleep(2)
                #            await page.type("textarea", question)
                #            await page.keyboard.press("Enter")
                #            tracker.questions[question_id].submitted_at = datetime.now()
                #            tracker.questions[question_id].status = "processing"
                #
                #            await asyncio.sleep(40)
                #            client = await context.new_cdp_session(page)
                #            result = await client.send("Page.captureSnapshot", {"format": "mhtml"})
                #            mhtml_data = result["data"]  # <-- 字符串
                #            raw_bytes = mhtml_data.encode("utf-8", "surrogateescape")
                #            b64_data = base64.b64encode(raw_bytes).decode("ascii")
                #            # Get collected responses
                #            q_response = tracker.get_question(question_id)
                #            if q_response:
                #                q_response.status = "completed"
                #                q_response.completed_at = datetime.now()
                #
                #                # Convert to expected format
                #                if q_response.responses:
                #                    results.append(q_response.responses[-1])
                #                else:
                #                    logger.warning(f"No responses captured for question {i + 1}")
                #                    results.append({"url": "", "body": "", "payload": ""})
                #            return_result.update({
                #                "response": results,
                #                "mhtml": b64_data
                #            })
                #            # Wait between questions
                #            if i < len(question) - 1:
                #                await asyncio.sleep(2)  # Short delay between questions
                #
                #        except Exception as e:
                #            logger.error(f"Failed to process question {i + 1}: {e}")
                #            tracker.questions[question_id].status = "failed"
                #            results.append({"url": "", "body": f"Error: {str(e)}", "payload": ""})
                #    await browser.close()
                #    return return_result

        except LoginException:
            raise  # Re-raise login exceptions
        except Exception as e:
            logger.error(f"Crawler failed: {e}", exc_info=True)
            raise BrowserException(f"Crawler operation failed: {e}", "CRAWLER_FAILED")


async def launch_browser(playwright):
    """Launch browser with proper configuration"""
    launch_options = {
        "headless": settings.browser.headless,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",  # Helps with memory issues
        ],
    }

    # Only add executable_path if specified
    if settings.browser.executable_path and settings.browser.executable_path.strip():
        launch_options["executable_path"] = settings.browser.executable_path

    try:
        browser = await playwright.chromium.launch(**launch_options)
        logger.info("Browser launched successfully")
        return browser
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        raise BrowserException(f"Browser launch failed: {e}", "BROWSER_LAUNCH_FAILED")


async def create_browser_context(browser, cookies: list[dict]):
    """Create browser context with anti-detection measures"""
    from utils.validators import CookieValidator

    context = await browser.new_context(
        user_agent=settings.browser.user_agent,
        viewport={
            "width": settings.browser.viewport_width,
            "height": settings.browser.viewport_height,
        },
        locale="en-US",
        timezone_id="America/New_York",
    )

    # Normalize and add cookies with proper Playwright format
    normalized_cookies = [
        CookieValidator.normalize_cookie_for_playwright(cookie) for cookie in cookies
    ]
    await context.add_cookies(normalized_cookies)

    # Inject anti-detection script
    await context.add_init_script("""
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock chrome object
        window.chrome = { runtime: {} };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)

    return context


async def navigate_with_retry(page: Page, url: str, max_retries: int = 3):
    """Navigate to URL with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            await page.goto(
                url, wait_until="domcontentloaded", timeout=settings.browser.timeout
            )
            # Wait for page to stabilize (ChatGPT never reaches networkidle due to continuous WebSocket/polling)
            await asyncio.sleep(2)  # Simple wait instead of networkidle
            logger.info(f"Successfully navigated to {url}")
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise NetworkException(
                    f"Failed to navigate after {max_retries} attempts: {e}",
                    "NAV_FAILED",
                )

            wait_time = 2**attempt  # Exponential backoff
            logger.warning(
                f"Navigation attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
            )
            await asyncio.sleep(wait_time)


async def check_login(page: Page):
    """Improved login verification with multiple checks"""
    await asyncio.sleep(3)  # Initial wait for page to settle

    # Multiple login indicators
    login_indicators = [
        'button:has-text("Log in")',
        'button:has-text("登录")',
        'button:has-text("Sign up")',
        '[data-testid="login-button"]',
    ]

    for selector in login_indicators:
        element = await page.query_selector(selector)
        if element and await element.is_visible():
            logger.error(f"Login required - found indicator: {selector}")
            raise LoginException(
                "Not logged in - cookie invalid or expired", "LOGIN_REQUIRED"
            )

    logger.info("Login verification successful")


async def enable_web_search(page: Page):
    """Enable web search with better error handling"""
    try:
        # Click plus button
        await page.get_by_test_id("composer-plus-btn").click(timeout=10000)
        await asyncio.sleep(1)
        logger.info("Clicked composer plus button")

        # Hover over more option
        more_button = page.get_by_role("menuitem", name="More", exact=True)
        await more_button.hover(timeout=10000)
        await asyncio.sleep(0.5)

        # Wait for web search option to appear
        await page.wait_for_selector('text="Web search"', timeout=5000)

        # Click web search
        await page.get_by_text("Web search", exact=True).click(timeout=10000)
        await asyncio.sleep(1)

        logger.info("Web search enabled successfully")
        return True

    except Exception as e:
        logger.warning(f"Failed to enable web search: {e}")
        # Don't fail the entire operation if web search can't be enabled
        return False


async def process_questions(
    page: Page, questions: list[str], tracker: ImprovedResponseTracker
) -> list[dict]:
    """Process questions with improved tracking and waiting"""
    results = []

    for i, question in enumerate(questions):
        # Create question tracking
        question_id = tracker.create_question(question)
        tracker.current_question_id = question_id

        logger.info(f"Processing question {i + 1}/{len(questions)}: {question[:50]}...")

        try:
            # Submit question
            await submit_question(page, question)
            tracker.questions[question_id].submitted_at = datetime.now()
            tracker.questions[question_id].status = "processing"

            # Smart wait for response
            # await wait_for_response_smart(page, tracker, question_id, timeout=60)
            await wait_for_response_smart(page)
            # Get collected responses
            q_response = tracker.get_question(question_id)
            if q_response:
                q_response.status = "completed"
                q_response.completed_at = datetime.now()

                # Convert to expected format
                if q_response.responses:
                    results.append(q_response.responses[-1])
                else:
                    logger.warning(f"No responses captured for question {i + 1}")
                    results.append({"url": "", "body": "", "payload": ""})

            # Wait between questions
            if i < len(questions) - 1:
                await asyncio.sleep(2)  # Short delay between questions

        except Exception as e:
            logger.error(f"Failed to process question {i + 1}: {e}")
            tracker.questions[question_id].status = "failed"
            results.append({"url": "", "body": f"Error: {str(e)}", "payload": ""})

    return results


async def submit_question(page: Page, question: str):
    """Submit a question to ChatGPT"""
    try:
        # Try to find the ProseMirror contenteditable div first (primary input method)
        editor = await page.query_selector('#prompt-textarea[contenteditable="true"]')

        if editor and await editor.is_visible():
            # Use the contenteditable div
            logger.debug("Using contenteditable div for input")
            await editor.click()  # Focus the editor
            await page.keyboard.press(
                "Meta+A"
                if page.context.browser.browser_type.name == "webkit"
                else "Control+A"
            )  # Select all
            await page.keyboard.press("Backspace")  # Clear existing content
            await editor.type(question)  # Type the question
        else:
            # Fallback to textarea (for mobile or accessibility mode)
            logger.debug("Contenteditable div not found, falling back to textarea")
            textarea = await page.wait_for_selector(
                "textarea[name='prompt-textarea']", state="attached", timeout=10000
            )

            # Check if textarea is visible
            if await textarea.is_visible():
                await textarea.fill(question)
            else:
                # If textarea is hidden, try to make it work anyway by focusing and typing
                await textarea.focus()
                await textarea.evaluate("(el) => el.value = ''")  # Clear via JS
                await textarea.type(question)

        await asyncio.sleep(0.5)

        # Press Enter to submit
        await page.keyboard.press("Enter")
        logger.debug(f"Submitted question: {question[:50]}...")

    except Exception as e:
        logger.error(f"Failed to submit question: {e}")
        raise

async def wait_for_response_smart(page: Page, timeout: int = 60):

    # 等待生成完成：
    # 检测 stop-button 按钮是否消失
    # 按钮消失后等待 3 秒再返回

    start_time = asyncio.get_event_loop().time()
    check_interval = 0.5  # 每0.5秒检查一次

    await asyncio.sleep(1)  # 初始等待

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            stop_btn = await page.query_selector('button[data-testid="stop-button"]')
            stop_visible = stop_btn and await stop_btn.is_visible()

            if not stop_visible:
                # 按钮消失，等待 3 秒再返回
                await asyncio.sleep(3)
                return

        except Exception as e:
            # 出错忽略，继续循环
            pass

        await asyncio.sleep(check_interval)

    # 超时
    logger.warning(f"Response wait timeout after {timeout}s")

# async def wait_for_response_smart(
#     page: Page, tracker: ImprovedResponseTracker, question_id: str, timeout: int = 60
# ):
#     """
#     Smart waiting that checks for response completion indicators
#     Waits for the stop button to disappear, indicating generation is complete
#     """
#     start_time = asyncio.get_event_loop().time()
#     check_interval = 0.5  # Check every 0.5 seconds for faster detection
#
#     # Wait a moment for generation to start
#     await asyncio.sleep(1)
#
#     while (asyncio.get_event_loop().time() - start_time) < timeout:
#         try:
#             # Check if stop button exists (indicates generation is in progress)
#             stop_btn = await page.query_selector('button[data-testid="stop-button"]')
#
#             if not stop_btn:
#                 # Stop button disappeared, generation is complete
#                 # Verify we have responses
#                 question = tracker.get_question(question_id)
#                 if question and question.responses:
#                     logger.info(
#                         "Response completion detected - stop button disappeared"
#                     )
#                     await asyncio.sleep(1)  # Brief wait for final data to be captured
#                     return
#                 else:
#                     # No responses yet, might be too early - continue waiting
#                     logger.debug(
#                         "Stop button not found but no responses yet, continuing to wait"
#                     )
#             else:
#                 logger.debug("Generation in progress - stop button still present")
#
#         except Exception as e:
#             logger.debug(f"Page state check error: {e}")
#
#         await asyncio.sleep(check_interval)
#
#     # Timeout reached
#     logger.warning(f"Response wait timeout after {timeout}s")
#     # Don't raise exception, return what we have


async def handle_response(response: Response, tracker: list,task_id:str):
    try:
        url = response.url
        if "conversation" in url and response.request.method == "POST":
            body = await response.text()
            payload = response.request.post_data

            tracker.append({
                "url": url,
                "body": body,
                "payload": payload,
                "timestamp": datetime.now().isoformat(),
            })

            # # 异步添加到 tracker
            # await tracker.append(response_data)


            # 打日志，包括任务ID
            logger.info(f"[Task:{task_id}] Captured response URL={url}, length={len(body)}")
            logger.info(f"[Task :{task_id}] Captured response for URL: {url}, length={len(body)}")

    except Exception as e:
        logger.warning(f"[Task {task_id}] Response handling error: {e}")

