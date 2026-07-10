# config/settings.py

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class BrowserSettings(BaseSettings):
    """浏览器配置"""

    executable_path: str | None = Field(
        default="",
        description="Chrome浏览器可执行文件路径，留空则使用Playwright默认浏览器",
    )
    headless: bool = Field(default=False, description="是否无头模式运行")
    viewport_width: int = Field(default=1280, description="视口宽度")
    viewport_height: int = Field(default=743, description="视口高度")
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        description="用户代理字符串",
    )
    timeout: int = Field(default=60000, description="页面加载超时时间(毫秒)")

    class Config:
        env_file = ".env"
        env_prefix = "BROWSER_"


class CrawlerSettings(BaseSettings):
    """爬虫配置"""

    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: int = Field(default=1, description="重试延迟(秒)")
    question_delay: int = Field(default=30, description="问题间隔时间(秒)")
    operation_timeout: int = Field(default=10000, description="操作超时时间(毫秒)")
    max_questions_per_session: int = Field(default=10, description="单次会话最大问题数")

    class Config:
        env_file = ".env"
        env_prefix = "CRAWLER_"


class APISettings(BaseSettings):
    """API配置"""

    host: str = Field(default="0.0.0.0", description="服务主机")
    port: int = Field(default=8083, description="服务端口")
    debug: bool = Field(default=False, description="调试模式")
    base_url: str = Field(default='', description="scheduler API URL")
    api_key: str = Field(default='', description="scheduler API Key")
    max_request_size: int = Field(
        default=10 * 1024 * 1024, description="最大请求大小(字节)"
    )

    class Config:
        env_file = ".env"
        env_prefix = "API_"


class TimeZone(BaseSettings):
    run_start_hour: int = Field(default=8, description="运行时间")
    run_end_hour: int = Field(default=20, description="结束时间")
    run_timezone: str = "Asia/Shanghai"

    class Config:
        env_file = ".env"
        env_prefix = "TIMEZONE_"


class LogSettings(BaseSettings):
    """日志配置"""

    level: str = Field(default="INFO", description="日志级别")
    log_dir: str = Field(default="logs", description="日志目录")
    max_bytes: int = Field(default=1_000_000, description="单个日志文件最大大小")
    backup_count: int = Field(default=5, description="日志文件备份数量")

    class Config:
        env_file = ".env"
        env_prefix = "LOG_"


class Settings(BaseSettings):
    """应用设置"""

    browser: BrowserSettings = BrowserSettings()
    crawler: CrawlerSettings = CrawlerSettings()
    api: APISettings = APISettings()
    log: LogSettings = LogSettings()
    timezone: TimeZone = TimeZone()
    environment: str = Field(default="development", description="运行环境")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
