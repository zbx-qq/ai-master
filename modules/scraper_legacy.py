import asyncio

from playwright.async_api import async_playwright

from config.logger import logger
from config.settings import settings


async def crawler(problem_list, click, cookie):
    """
    执行GPT爬虫任务

    Args:
        problem_list (list): 问题列表
        click (bool): 是否启用网页搜索
        cookie (list): Cookie数据列表 (从API请求传入)

    Returns:
        list: 响应结果列表
    """
    responses = []

    async with async_playwright() as p:
        launch_options = {
            "headless": settings.browser.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        }

        if (
            settings.browser.executable_path
            and settings.browser.executable_path.strip()
        ):
            launch_options["executable_path"] = settings.browser.executable_path

        browser = await p.chromium.launch(**launch_options)

        context = await browser.new_context(
            user_agent=settings.browser.user_agent,
            viewport={
                "width": settings.browser.viewport_width,
                "height": settings.browser.viewport_height,
            },
        )

        await context.add_cookies(cookie)
        page = await context.new_page()

        page.on(
            "response",
            lambda response: asyncio.ensure_future(
                handle_response(response, responses)
            ),
        )

        await page.goto(
            "https://chatgpt.com", wait_until="domcontentloaded", timeout=60000
        )
        await check_login(page)
        await asyncio.sleep(3)

        if click:
            async def click_plus():
                await page.get_by_test_id("composer-plus-btn").click(timeout=10000)
                logger.info("点击加号按钮成功")
                await asyncio.sleep(1)

            await retry(click_plus, action_name="点击加号按钮")

            async def hover_more():
                more_button = page.get_by_role("menuitem", name="更多", exact=True)
                await more_button.hover(timeout=10000)
                logger.info("悬停在“更多”成功")
                await page.wait_for_selector("text=网页搜索", timeout=5000)
                await asyncio.sleep(0.5)

            hover_success = await retry(hover_more, action_name="悬停‘更多’")
            if hover_success:
                async def click_web_search_btn():
                    await page.get_by_text("网页搜索", exact=True).click(timeout=10000)
                    logger.info("点击‘网页搜索’成功")
                    await asyncio.sleep(1)

                await retry(click_web_search_btn, action_name="点击‘网页搜索’")

        for q in problem_list:
            await page.type("textarea", q)
            await asyncio.sleep(1)
            await page.keyboard.press("Enter")
            await asyncio.sleep(30)

        await browser.close()
        return responses


async def handle_response(response, responses):
    try:
        url = response.url
        if "conversation" in url and response.request.method == "POST":
            body = await response.text()
            payload = response.request.post_data
            responses.append({"url": url, "body": body, "payload": payload})
    except Exception as e:
        print("响应处理出错：", e)


async def retry(action, retries=3, delay=1, action_name="操作"):
    """通用重试函数"""
    for attempt in range(1, retries + 1):
        try:
            await action()
            return True
        except Exception as e:
            logger.info("%s失败，第%d次尝试：%s", action_name, attempt, e)
            if attempt < retries:
                await asyncio.sleep(delay)
            else:
                logger.info("%s最终失败", action_name)
                return False


async def check_login(page):
    """检查是否登录"""
    login_button = await page.query_selector(
        'button:has-text("登录")'
    )
    if login_button:
        logger.error("检测到登录按钮，说明未登录或cookie无效")
        raise Exception("登录失败：cookie 无效或已过期")
    logger.info("未检测到登录弹窗，视为登录成功")
