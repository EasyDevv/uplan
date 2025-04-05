import logging
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# --- 환경 변수 로드 ---
LOG_DETAIL = os.getenv("LOG_DETAIL", "false").lower()

# --- 설정 ---
DEFAULT_LOG_LEVEL = logging.DEBUG  # 기본 트레이스 레벨을 DEBUG로 변경
FILE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_DIR = Path("logs")
JSON_LOG_FILENAME_FORMAT = "{timestamp}.log"
CONSOLE_LOG_LEVEL = logging.DEBUG
JSON_LOG_LEVEL = logging.DEBUG
LOGGER_NAME = "tracer"

if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
