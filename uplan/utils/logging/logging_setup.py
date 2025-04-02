import logging
from datetime import datetime

# Rich imports
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

# 내부 임포트
from .logging_config import (
    CONSOLE_LOG_LEVEL,
    JSON_LOG_FILENAME_FORMAT,
    JSON_LOG_LEVEL,
    LOG_DIR,
    LOGGER_NAME,
)
from .logging_formatter import JsonFormatter

# Rich 트레이스백 핸들러 초기화 (애플리케이션 시작 시 한 번만 호출되도록 고려)
# 여기보다는 애플리케이션 진입점(예: app.py 또는 __main__.py)에서 호출하는 것이 더 적합할 수 있습니다.
# 하지만 원래 위치를 유지합니다.
install_rich_traceback(show_locals=False)


# --- 로깅 설정 ---
def setup_logging() -> logging.Logger:
    """
    애플리케이션 로거를 설정하고 반환합니다.

    콘솔 핸들러(RichHandler)와 JSON 파일 핸들러를 설정합니다.
    이미 핸들러가 설정된 경우 기존 로거를 반환합니다.

    Returns:
        설정된 logging.Logger 인스턴스.
    """
    logger = logging.getLogger(LOGGER_NAME)
    # 이미 핸들러가 설정되어 있다면 중복 설정을 방지합니다.
    if logger.hasHandlers():
        return logger

    # 콘솔과 파일 로그 레벨 중 더 낮은 레벨(더 상세한 레벨)을 로거의 기본 레벨로 설정합니다.
    effective_level = min(CONSOLE_LOG_LEVEL, JSON_LOG_LEVEL)
    logger.setLevel(effective_level)

    # 콘솔 핸들러 설정 (RichHandler 사용)
    console_handler = RichHandler(
        level=CONSOLE_LOG_LEVEL,
        rich_tracebacks=True,  # Rich 트레이스백 활성화
        markup=True,  # Rich 마크업 활성화
        show_path=True,  # 로그 메시지에 파일 경로 표시
        enable_link_path=True,  # 파일 경로에 터미널 링크 활성화 (터미널 지원 시)
        show_level=True,  # 로그 레벨 표시
        show_time=True,  # 시간 표시
        log_time_format="[%Y-%m-%d %H:%M:%S.%f]",  # 시간 형식 지정
        tracebacks_show_locals=False,  # 트레이스백에 지역 변수 표시 안 함
    )
    logger.addHandler(console_handler)

    # JSON 파일 핸들러 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_log_filename = LOG_DIR / JSON_LOG_FILENAME_FORMAT.format(timestamp=timestamp)
    try:
        json_file_handler = logging.FileHandler(json_log_filename, encoding="utf-8")
        json_file_handler.setLevel(JSON_LOG_LEVEL)
        json_formatter = JsonFormatter()
        json_file_handler.setFormatter(json_formatter)
        logger.addHandler(json_file_handler)
    except OSError as e:
        # 파일 핸들러 생성 실패 시 콘솔에 에러 로깅 (기본 로거 사용)
        logging.error(f"Failed to create log file handler for {json_log_filename}: {e}")

    # 로그 메시지가 루트 로거로 전파되지 않도록 설정합니다.
    logger.propagate = False
    return logger


# --- 로거 인스턴스 ---
# 모듈 로드 시 로거를 설정하고 인스턴스를 생성합니다.
_logger = setup_logging()


def get_logger() -> logging.Logger:
    """
    설정된 로거 인스턴스를 반환합니다.

    Returns:
        미리 설정된 logging.Logger 인스턴스.
    """
    return _logger
