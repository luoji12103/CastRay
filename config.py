# 系统配置
import os
from pathlib import Path

# 基础配置
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"

# 服务器配置
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8001
DEFAULT_WORKERS = 4

# Ray配置
RAY_ADDRESS = os.getenv("RAY_ADDRESS", "auto")
RAY_DASHBOARD_PORT = 8265

# 网络配置
MULTICAST_GROUP = "224.1.1.1"
MULTICAST_PORT = 9999
BROADCAST_PORT = 9998

# 消息配置
MAX_MESSAGE_SIZE = 4096
MESSAGE_TIMEOUT = 30.0
MAX_RETRY_COUNT = 3

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 安全配置
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {".txt", ".json", ".csv", ".log", ".md"}

# 创建必要目录
STATIC_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
