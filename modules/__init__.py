from .scraper import crawler


class AppContext:
    async def run(self):
        await crawler()


def create():
    return AppContext()
