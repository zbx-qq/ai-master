# utils/exceptions.py
"""自定义异常类"""


class GPTCrawlerException(Exception):
    """爬虫基础异常"""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class BrowserException(GPTCrawlerException):
    """浏览器相关异常"""

    pass


class LoginException(GPTCrawlerException):
    """登录相关异常"""

    pass


class NetworkException(GPTCrawlerException):
    """网络相关异常"""

    pass


class ValidationException(GPTCrawlerException):
    """数据验证异常"""

    pass


class RateLimitException(GPTCrawlerException):
    """频率限制异常"""

    pass


class ConfigurationException(GPTCrawlerException):
    """配置异常"""

    pass
