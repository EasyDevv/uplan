import functools
import inspect
import json
import logging
import time
import traceback
import contextvars
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Union

# Pydantic import
from pydantic import BaseModel, Field, ValidationError

from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

# Rich 콘솔 및 트레이스백 핸들러 초기화
install_rich_traceback(show_locals=False)

# --- 설정 ---
DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_DIR = Path("logs")
CONSOLE_LOG_LEVEL = logging.INFO
FILE_LOG_LEVEL = logging.DEBUG

# 로그 디렉토리 생성
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 컨텍스트 변수
current_function_context = contextvars.ContextVar(
    "current_function_context", default=None
)


# --- Pydantic 모델 ---
class LogContext(BaseModel):
    """로그 이벤트에 대한 구조화된 컨텍스트 정보 (Pydantic 모델)."""

    event_type: str = Field(
        ..., description="로그 이벤트 유형 ('entry', 'exit', 'error')"
    )
    function_name: str = Field(..., description="실행된 함수의 이름")
    module_name: str = Field(..., description="함수가 정의된 모듈의 이름")
    is_async: bool = Field(..., description="함수가 비동기인지 여부")
    execution_time: Optional[float] = Field(None, description="함수 실행 시간 (초)")
    error_type: Optional[str] = Field(None, description="발생한 오류의 유형 이름")
    error_message: Optional[str] = Field(None, description="발생한 오류의 메시지")
    # 필요에 따라 다른 필드 추가 가능
    # 예: call_args: Optional[Dict[str, Any]] = None

    # Pydantic v2 이상에서는 model_config 사용
    class Config:
        # Pydantic v1: anystr_strip_whitespace = True
        # Pydantic v2: str_strip_whitespace = True
        # 필요한 경우 다른 설정 추가
        pass


# --- JSON 직렬화 헬퍼 ---
def pydantic_encoder(obj: Any) -> Any:
    """JSON 직렬화를 위한 Pydantic 모델 인코더."""
    if isinstance(obj, BaseModel):
        # exclude_none=True: None 값 필드는 JSON에서 제외
        return obj.model_dump(mode="json", exclude_none=True)
    # datetime 객체 등 다른 타입 처리 가능
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Path 객체를 문자열로 변환
    if isinstance(obj, Path):
        return str(obj)
    # 기본적으로 처리할 수 없는 타입은 문자열로 변환 시도
    try:
        # 시도 후 실패하면 에러 대신 문자열 표현 반환
        return str(obj)
    except Exception:
        return f"<unserializable type: {type(obj).__name__}>"


# --- 로깅 설정 ---
def setup_logging() -> logging.Logger:
    """콘솔 및 파일 핸들러로 로깅을 설정합니다."""
    logger = logging.getLogger("uplan")
    if logger.hasHandlers():
        return logger

    logger.setLevel(min(CONSOLE_LOG_LEVEL, FILE_LOG_LEVEL))

    # 콘솔 핸들러 (Rich)
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=True,
        show_level=True,
        show_time=True,
        level=CONSOLE_LOG_LEVEL,
    )

    logger.addHandler(console_handler)

    return logger


# --- 로거 인스턴스 ---
_logger = setup_logging()


def get_logger() -> logging.Logger:
    """설정된 uplan 로거 인스턴스를 반환합니다."""
    return _logger


# --- 로깅 데코레이터 ---
def trace(func: Callable) -> Callable:
    """
    함수/메서드의 시작, 종료, 예외 발생을 로깅하는 데코레이터 (동기/비동기 지원, Pydantic 사용).
    """
    func_name = func.__name__
    module_name = func.__module__
    is_async = inspect.iscoroutinefunction(func)
    logger = get_logger()

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        token = current_function_context.set(func_name)
        start_time = time.perf_counter()

        # Pydantic 모델로 컨텍스트 생성 및 로깅
        try:
            entry_context = LogContext(
                event_type="entry",
                function_name=func_name,
                module_name=module_name,
                is_async=True,
            )
            logger.debug(
                f"▶️ Entering async {func_name}", extra={"log_context": entry_context}
            )
        except ValidationError as e:
            logger.error(
                f"Pydantic validation error on entry context: {e}",
                extra={"function_name": func_name},
            )

        try:
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            try:
                exit_context = LogContext(
                    event_type="exit",
                    function_name=func_name,
                    module_name=module_name,
                    is_async=True,
                    execution_time=elapsed,
                )
                logger.debug(
                    f"✅ Exited async {func_name} in {elapsed:.4f}s",
                    extra={"log_context": exit_context},
                )
            except ValidationError as e:
                logger.error(
                    f"Pydantic validation error on exit context: {e}",
                    extra={"function_name": func_name},
                )
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            try:
                error_context = LogContext(
                    event_type="error",
                    function_name=func_name,
                    module_name=module_name,
                    is_async=True,
                    execution_time=elapsed,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                logger.error(
                    f"❌ Error in async {func_name} after {elapsed:.4f}s: {e}",
                    exc_info=True,
                    extra={"log_context": error_context},
                )
            except ValidationError as ve:
                logger.error(
                    f"Pydantic validation error on error context: {ve}",
                    extra={"function_name": func_name},
                )
                # Pydantic 오류 시에도 원본 오류는 로깅 시도
                logger.error(
                    f"❌ Error in async {func_name} after {elapsed:.4f}s: {e} (Context validation failed)",
                    exc_info=True,
                    extra={"original_error": str(e)},
                )
            raise
        finally:
            current_function_context.reset(token)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        token = current_function_context.set(func_name)
        start_time = time.perf_counter()

        try:
            entry_context = LogContext(
                event_type="entry",
                function_name=func_name,
                module_name=module_name,
                is_async=False,
            )
            logger.debug(
                f"▶️ Entering sync {func_name}", extra={"log_context": entry_context}
            )
        except ValidationError as e:
            logger.error(
                f"Pydantic validation error on entry context: {e}",
                extra={"function_name": func_name},
            )

        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            try:
                exit_context = LogContext(
                    event_type="exit",
                    function_name=func_name,
                    module_name=module_name,
                    is_async=False,
                    execution_time=elapsed,
                )
                logger.debug(
                    f"✅ Exited sync {func_name} in {elapsed:.4f}s",
                    extra={"log_context": exit_context},
                )
            except ValidationError as e:
                logger.error(
                    f"Pydantic validation error on exit context: {e}",
                    extra={"function_name": func_name},
                )
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            try:
                error_context = LogContext(
                    event_type="error",
                    function_name=func_name,
                    module_name=module_name,
                    is_async=False,
                    execution_time=elapsed,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                logger.error(
                    f"❌ Error in sync {func_name} after {elapsed:.4f}s: {e}",
                    exc_info=True,
                    extra={"log_context": error_context},
                )
            except ValidationError as ve:
                logger.error(
                    f"Pydantic validation error on error context: {ve}",
                    extra={"function_name": func_name},
                )
                logger.error(
                    f"❌ Error in sync {func_name} after {elapsed:.4f}s: {e} (Context validation failed)",
                    exc_info=True,
                    extra={"original_error": str(e)},
                )
            raise
        finally:
            current_function_context.reset(token)

    return async_wrapper if is_async else sync_wrapper


# --- 예제 사용 ---
if __name__ == "__main__":
    logger = get_logger()

    logger.info("로깅 시스템 시작됨 (Pydantic 적용).")

    # 예제 Pydantic 모델
    class UserInfo(BaseModel):
        user_id: int
        username: str
        roles: list[str] = []

    @trace
    def process_data(data: dict, user: UserInfo):
        logger.info(f"데이터 처리 중: {data}", extra={"user_details": user})
        time.sleep(0.1)
        if not data.get("valid"):
            raise ValueError("유효하지 않은 데이터")
        return {"status": "processed", **data}

    @trace
    async def fetch_remote_config(url: str):
        logger.info(f"설정 가져오는 중: {url}")
        # import asyncio # 비동기 함수 내에서만 import 가능
        await asyncio.sleep(0.2)
        if "error" in url:
            raise ConnectionError("원격 서버 연결 실패")
        return {"config_version": "1.2.3", "url": url}

    # 동기 함수 호출
    logger.info("-" * 20)
    current_user = UserInfo(user_id=101, username="alice", roles=["admin", "dev"])
    valid_data = {"id": "xyz", "value": 100, "valid": True}
    result_sync = process_data(valid_data, user=current_user)
    logger.info(f"동기 함수 결과: {result_sync}")

    try:
        invalid_data = {"id": "abc", "valid": False}
        process_data(invalid_data, user=current_user)
    except ValueError as e:
        # 에러 로그는 데코레이터에서 자동으로 찍힘
        logger.warning(f"동기 함수에서 예상된 오류 처리 완료.")

    # 비동기 함수 호출 (asyncio 필요)
    import asyncio

    async def main():
        logger.info("-" * 20)
        config = await fetch_remote_config("https://config.example.com")
        logger.info(f"비동기 함수 결과: {config}", extra={"source": "remote"})

        try:
            await fetch_remote_config("https://error.example.com")
        except ConnectionError as e:
            logger.warning(f"비동기 함수에서 예상된 오류 처리 완료.")

        # 직접 로그 메시지 (Pydantic 객체 포함)
        logger.info(
            "작업 완료",
            extra={"final_user": UserInfo(user_id=999, username="final_user")},
        )

        # 직접 로그 메시지 (일반 dict 포함)
        logger.debug("디버그 정보", extra={"raw_data": {"a": 1, "b": datetime.now()}})

    asyncio.run(main())

    logger.info("로깅 시스템 종료됨.")
