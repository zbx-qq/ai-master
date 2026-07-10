# config/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

# 日志目录
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 创建 logger
logger = logging.getLogger("gptAutoCrawling")
logger.setLevel(logging.INFO)

# 日志格式
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 文件处理器（滚动文件，最多保留5个，每个最大1MB）
file_handler = RotatingFileHandler(
    f"{LOG_DIR}/app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(console_handler)
logger.addHandler(file_handler)
