import asyncio
import json
from playwright.async_api import async_playwright
from config.logger import logger
cookieIndex = 0

# ---- 加载 cookies（一次性） ----
with open('data/cookies.json', 'r', encoding='utf-8') as f:
    ALL_COOKIES = json.load(f)
    for cookie in ALL_COOKIES:
        cookie["value"] = cookie["value"].replace("\t", "").replace("\n", "")


async def crawler(problem_list,click):
    global cookieIndex
    responses = []

    async with async_playwright() as p:


        browser = await p.chromium.launch(
            headless=False,
            executable_path="C:\Program Files\Google\Chrome\Application\chrome.exe",  # 本地 Chrome 路径
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ]
        #设置代理
        # args = [
        #     "--no-sandbox",
        #     "--disable-setuid-sandbox",
        #     "--disable-blink-features=AutomationControlled",
        #     "--proxy-server=https://131.0.0.1:7890"
        # ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 743},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        )

        cookie = ALL_COOKIES[cookieIndex % len(ALL_COOKIES)]
        cookieIndex += 1
        logger.info(f"当前使用第 {cookieIndex} 个 Cookie")
        await context.add_cookies([cookie])

        page = await context.new_page()
        page.on("response", lambda response: asyncio.ensure_future(handle_response(response, responses)))
        await page.goto("https://chatgpt.com", wait_until="networkidle")

        await page.type("textarea", "北京旅游指南推荐")
        await asyncio.sleep(1)
        await page.keyboard.press("Enter")
        await asyncio.sleep(25)
        await page.type("textarea", "南京旅游指南推荐")
        await asyncio.sleep(1)
        await page.keyboard.press("Enter")
        await asyncio.sleep(25)
        await browser.close()
        return responses


async def handle_response(response, responses):
    try:
        url = response.url
        if "conversation" in url and response.request.method == "POST":
            body = await response.text()
            responses.append({"url": url, "body": body})
    except Exception as e:
        logger.info("响应处理出错", e)


async def main():
    """主函数：启动爬虫"""
    logger.info("===== 开始执行 ChatGPT 爬虫任务 =====")
    try:
        result = await crawler("北京旅游指南推荐",0)
        logger.info(f"===== 任务完成，捕获到 {len(result)} 条响应数据 =====")

        if result:
            logger.info("首条响应内容预览：")
            logger.info(result[0]["body"][:500] + "...")

    except Exception as e:
        logger.error(f"爬虫运行失败：{str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
