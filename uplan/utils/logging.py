import functools
import inspect
import json
import logging
import time
import traceback
import contextvars
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

# Pydantic import
from pydantic import BaseModel, Field, ValidationError, field_validator

# Rich imports
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback
from rich.json import JSON
from rich.pretty import pretty_repr

# Rich 콘솔 및 트레이스백 핸들러 초기화
# show_locals=False: 로컬 변수 표시 안 함 (보안 및 가독성)
install_rich_traceback(show_locals=False)

# --- 설정 ---
DEFAULT_LOG_LEVEL = logging.INFO
# RichHandler는 자체 포맷을 사용하므로, 파일 핸들러용 포맷 정의
FILE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_LOG_FORMAT = '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": %(message)s, "module": "%(module)s", "funcName": "%(funcName)s", "lineno": %(lineno)d}'  # 기본 필드
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_DIR = Path("logs")
LOG_FILENAME_FORMAT = "app_{timestamp}.log"
JSON_LOG_FILENAME_FORMAT = "app_structured_{timestamp}.log"
CONSOLE_LOG_LEVEL = logging.DEBUG  # 콘솔에는 더 자세한 정보 표시 가능
FILE_LOG_LEVEL = logging.INFO  # 파일에는 INFO 레벨 이상 저장
JSON_LOG_LEVEL = logging.DEBUG  # JSON 파일에는 DEBUG 레벨 이상 저장

# 로그 디렉토리 생성
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- 컨텍스트 변수 ---
# 현재 실행 중인 함수의 이름을 추적하여 중첩된 호출 시 유용
current_function_context = contextvars.ContextVar[Optional[str]](
    "current_function_context", default=None
)


# --- Pydantic 모델 ---
class LogContext(BaseModel):
    """로그 이벤트에 대한 구조화된 컨텍스트 정보."""

    event_type: str = Field(
        ...,
        description="로그 이벤트 유형 ('entry', 'exit', 'error', 'info', 'debug', etc.)",
    )
    function_name: Optional[str] = Field(
        None, description="실행된 함수의 이름 (해당하는 경우)"
    )
    module_name: Optional[str] = Field(
        None, description="함수가 정의된 모듈의 이름 (해당하는 경우)"
    )
    is_async: Optional[bool] = Field(
        None, description="함수가 비동기인지 여부 (해당하는 경우)"
    )
    execution_time_seconds: Optional[float] = Field(
        None, description="함수 실행 시간 (초, 해당하는 경우)"
    )
    error_type: Optional[str] = Field(
        None, description="발생한 오류의 유형 이름 (해당하는 경우)"
    )
    error_message: Optional[str] = Field(
        None, description="발생한 오류의 메시지 (해당하는 경우)"
    )
    # 추가적인 사용자 정의 데이터
    details: Optional[Dict[str, Any]] = Field(
        None, description="로그 이벤트와 관련된 추가 상세 정보"
    )

    # Pydantic v2 이상에서는 model_config 사용
    class Config:
        # Pydantic v1: anystr_strip_whitespace = True
        # Pydantic v2: str_strip_whitespace = True
        str_strip_whitespace = True
        # Python 타입을 JSON으로 직렬화할 때 인코더 사용
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v),
            # 다른 필요한 타입 추가 가능
        }
        # V1에서는: arbitrary_types_allowed = True (필요시)
        # V2에서는 기본적으로 허용되거나 validate_assignment 등으로 처리

    # execution_time을 소수점 4자리까지 반올림 (선택 사항)
    @field_validator("execution_time_seconds", mode="before")
    @classmethod
    def round_execution_time(cls, v):
        if isinstance(v, (float, int)):
            return round(v, 4)
        return v


# --- JSON 직렬화 헬퍼 ---
def safe_serialize(obj: Any) -> Any:
    """JSON 직렬화를 위한 안전한 인코더 (Pydantic 모델 및 일반 객체 처리)."""
    if isinstance(obj, BaseModel):
        # exclude_none=True: None 값 필드는 JSON에서 제외
        # mode='json': Pydantic 모델 내 json_encoders 사용
        return obj.model_dump(mode="json", exclude_none=True)
    if isinstance(obj, (datetime, Path)):
        # Pydantic 모델 내 json_encoders와 유사하게 처리
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
    # 기본적으로 처리할 수 없는 타입은 문자열로 변환 시도
    try:
        # 시도 후 실패하면 에러 대신 타입 정보 반환
        json.dumps(obj)  # 직렬화 가능성 테스트
        return obj  # 직렬화 가능하면 원본 반환 (json.dumps가 처리하도록)
    except (TypeError, OverflowError):
        try:
            return repr(obj)  # repr()은 보통 더 많은 정보를 제공
        except Exception:
            return f"<unserializable type: {type(obj).__name__}>"


class JsonFormatter(logging.Formatter):
    """
    로그 레코드를 JSON 문자열로 포맷하는 Formatter.
    'extra' 딕셔너리의 내용을 JSON 객체에 포함시킵니다.
    """

    def __init__(self, fmt_keys: Optional[Dict[str, str]] = None):
        super().__init__()
        self.fmt_keys = fmt_keys or {
            "level": "levelname",
            "message": "message",
            "timestamp": "asctime",
            "logger": "name",
            "module": "module",
            "function": "funcName",
            "line": "lineno",
            "thread_name": "threadName",
        }
        # ISO 8601 형식 사용
        self.default_time_format = "%Y-%m-%dT%H:%M:%S"
        self.default_msec_format = "%s.%03dZ"  # 밀리초 및 UTC 표시

    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            # UTC 시간 사용 권장
            utc_ct = datetime.utcfromtimestamp(record.created)
            t = utc_ct.strftime(self.default_time_format)
            s = self.default_msec_format % (t, record.msecs)
        return s

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 문자열로 포맷합니다."""
        message_dict = {}
        # 기본 record 속성 추가
        for key, val_key in self.fmt_keys.items():
            val = getattr(record, val_key, None)
            if val is not None:
                message_dict[key] = val

        # 시간 포맷팅
        message_dict["timestamp"] = self.formatTime(record)

        # 기본 메시지 처리
        # 메시지가 이미 dict나 list인 경우 직접 사용, 아니면 문자열로
        if isinstance(record.msg, (dict, list)):
            message_dict["message"] = record.msg
        else:
            message_dict["message"] = record.getMessage()  # 포맷 문자열 처리

        # 'extra' 딕셔너리 내용 병합 (기존 키 덮어쓰기 가능)
        if hasattr(record, "log_context") and isinstance(
            record.log_context, LogContext
        ):
            # Pydantic 모델을 안전하게 직렬화된 dict로 변환하여 병합
            log_context_dict = record.log_context.model_dump(
                mode="json", exclude_none=True
            )
            message_dict.update(log_context_dict)
        elif record.args and isinstance(record.args, dict):
            # logger.info("message", extra=some_dict) 형태 처리
            message_dict.update(record.args)

        # extra의 다른 내용들도 추가 (log_context 제외)
        standard_attrs = list(logging.LogRecord.__dict__.keys()) + [
            "message",
            "asctime",
            "relativeCreated",
            "log_context",
        ]
        extra_attrs = {
            k: v
            for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }
        if extra_attrs:
            # 'details' 필드가 LogContext에 있으므로 거기에 병합하거나 별도 필드로 추가
            if "details" not in message_dict:
                message_dict["details"] = {}
            # extra_attrs의 내용을 안전하게 직렬화하여 details에 추가
            safe_extra = {k: safe_serialize(v) for k, v in extra_attrs.items()}
            message_dict["details"].update(safe_extra)

        # 예외 정보 추가
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            message_dict["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                # 상세 트레이스백은 용량이 크므로 필요한 경우에만 포함
                # "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback)
            }
        if record.exc_text:
            message_dict["exception_text"] = record.exc_text
        if record.stack_info:
            message_dict["stack_info"] = record.stack_info

        # JSON으로 직렬화 (safe_serialize 사용)
        # indent=None으로 한 줄로 출력, 필요시 indent=2 등으로 변경
        return json.dumps(message_dict, default=safe_serialize, ensure_ascii=False)


# --- 로깅 설정 ---
def setup_logging() -> logging.Logger:
    """콘솔(Rich) 및 JSON 파일 핸들러로 로깅을 설정합니다."""
    # 루트 로거 대신 특정 이름의 로거 사용 권장
    logger = logging.getLogger("uplan_tracer")
    # 핸들러 중복 추가 방지
    if logger.hasHandlers():
        # 이미 설정되었다면 기존 로거 반환 (선택적: 재설정 필요 시 핸들러 제거 후 진행)
        # logger.handlers.clear()
        return logger

    # 로거의 기본 레벨 설정 (모든 핸들러 레벨 중 가장 낮은 것)
    effective_level = min(
        CONSOLE_LOG_LEVEL, JSON_LOG_LEVEL
    )  # FILE_LOG_LEVEL 포함 시 추가
    logger.setLevel(effective_level)

    # 1. 콘솔 핸들러 (RichHandler)
    console_handler = RichHandler(
        level=CONSOLE_LOG_LEVEL,
        rich_tracebacks=True,  # Rich의 예쁜 트레이스백 사용
        markup=True,  # 로그 메시지 내 Rich 마크업 사용 가능
        show_path=True,  # 로그 발생 위치 경로 표시
        show_level=True,
        show_time=True,
        log_time_format="[%Y-%m-%d %H:%M:%S.%f]",  # 시간 형식 지정
        tracebacks_show_locals=False,  # 보안 및 간결성을 위해 로컬 변수 숨김
    )
    # RichHandler는 자체 포매터를 사용하므로 별도 설정 불필요
    logger.addHandler(console_handler)

    # 2. JSON 파일 핸들러
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_log_filename = LOG_DIR / JSON_LOG_FILENAME_FORMAT.format(timestamp=timestamp)

    json_file_handler = logging.FileHandler(json_log_filename, encoding="utf-8")
    json_file_handler.setLevel(JSON_LOG_LEVEL)

    # JsonFormatter 사용
    json_formatter = JsonFormatter()
    json_file_handler.setFormatter(json_formatter)
    logger.addHandler(json_file_handler)

    # (선택적) 일반 텍스트 파일 핸들러
    # log_filename = LOG_DIR / LOG_FILENAME_FORMAT.format(timestamp=timestamp)
    # file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    # file_handler.setLevel(FILE_LOG_LEVEL)
    # file_formatter = logging.Formatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT)
    # file_handler.setFormatter(file_formatter)
    # logger.addHandler(file_handler)

    # 기본 라이브러리 로거 전파 방지 (선택적)
    # logger.propagate = False

    return logger


# --- 로거 인스턴스 ---
_logger = setup_logging()


def get_logger() -> logging.Logger:
    """설정된 'uplan_tracer' 로거 인스턴스를 반환합니다."""
    return _logger


# --- 로깅 데코레이터 ---
def trace(_func: Optional[Callable] = None, *, level: int = logging.DEBUG) -> Callable:
    """
    함수/메서드의 시작, 종료, 예외 발생을 로깅하는 데코레이터 (동기/비동기 지원, Pydantic 사용).

    Args:
        _func: 데코레이터가 적용될 함수 (직접 호출 시 사용됨).
        level: 진입/종료 로그 레벨 (기본값: DEBUG). 오류는 항상 ERROR 레벨로 로깅됨.
    """

    def decorator(func: Callable) -> Callable:
        func_name = func.__name__
        module_name = func.__module__
        is_async = inspect.iscoroutinefunction(func)
        logger = get_logger()  # 설정된 로거 가져오기

        # 인자 로깅을 위한 함수 (직렬화 가능한 형태로 변환)
        def format_args(args, kwargs):
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()
            # Pydantic 모델 등 복잡한 객체를 위해 pretty_repr 사용 시도
            # 너무 길어질 수 있으므로 주의 필요
            # return {k: pretty_repr(v, max_length=100) for k, v in bound_args.arguments.items()}
            # 간단하게 문자열로 변환 (더 안전)
            return {k: repr(v) for k, v in bound_args.arguments.items()}

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            parent_context = current_function_context.get()
            token = current_function_context.set(
                f"{parent_context} -> {func_name}" if parent_context else func_name
            )
            start_time = time.perf_counter()
            log_context_details = {"call_args": format_args(args, kwargs)}

            try:
                entry_context = LogContext(
                    event_type="entry",
                    function_name=func_name,
                    module_name=module_name,
                    is_async=True,
                    details=log_context_details,
                )
                # 로그 레벨은 데코레이터 인자로 설정 가능
                logger.log(
                    level,
                    f"▶️ Entering async [bold cyan]{func_name}[/]",
                    extra={"log_context": entry_context},
                )
            except ValidationError as e:
                logger.error(
                    f"Pydantic validation error on entry context for {func_name}: {e}",
                    extra={"function_name": func_name},  # 기본 정보만 포함
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
                        execution_time_seconds=elapsed,
                        # 결과 로깅은 선택사항 (크거나 민감할 수 있음)
                        # details={"result": repr(result)[:200]} # 예시: 결과 일부 로깅
                    )
                    logger.log(
                        level,
                        f"✅ Exited async [bold cyan]{func_name}[/] in {elapsed:.4f}s",
                        extra={"log_context": exit_context},
                    )
                except ValidationError as e:
                    logger.error(
                        f"Pydantic validation error on exit context for {func_name}: {e}",
                        extra={"function_name": func_name},
                    )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                # exc_info=True를 통해 트레이스백 자동 로깅 (RichHandler가 처리)
                try:
                    error_context = LogContext(
                        event_type="error",
                        function_name=func_name,
                        module_name=module_name,
                        is_async=True,
                        execution_time_seconds=elapsed,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        details=log_context_details,  # 에러 발생 시 인자 정보 포함 유용
                    )
                    # Rich 마크업 사용 예시
                    logger.error(
                        f"❌ Error in async [bold red]{func_name}[/] after {elapsed:.4f}s: [red]{type(e).__name__}: {e}[/]",
                        exc_info=True,  # 트레이스백 포함
                        extra={"log_context": error_context},
                    )
                except ValidationError as ve:
                    logger.error(
                        f"Pydantic validation error on error context for {func_name}: {ve}",
                        extra={"function_name": func_name},
                    )
                    # Pydantic 오류 시에도 원본 오류는 로깅 시도
                    logger.error(
                        f"❌ Error in async [bold red]{func_name}[/] after {elapsed:.4f}s: [red]{type(e).__name__}: {e}[/] (Context validation failed)",
                        exc_info=True,
                        extra={"original_error": repr(e), "function_name": func_name},
                    )
                raise  # 원본 예외 다시 발생
            finally:
                current_function_context.reset(token)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            parent_context = current_function_context.get()
            token = current_function_context.set(
                f"{parent_context} -> {func_name}" if parent_context else func_name
            )
            start_time = time.perf_counter()
            log_context_details = {"call_args": format_args(args, kwargs)}

            try:
                entry_context = LogContext(
                    event_type="entry",
                    function_name=func_name,
                    module_name=module_name,
                    is_async=False,
                    details=log_context_details,
                )
                logger.log(
                    level,
                    f"▶️ Entering sync [bold green]{func_name}[/]",
                    extra={"log_context": entry_context},
                )
            except ValidationError as e:
                logger.error(
                    f"Pydantic validation error on entry context for {func_name}: {e}",
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
                        execution_time_seconds=elapsed,
                        # details={"result": repr(result)[:200]}
                    )
                    logger.log(
                        level,
                        f"✅ Exited sync [bold green]{func_name}[/] in {elapsed:.4f}s",
                        extra={"log_context": exit_context},
                    )
                except ValidationError as e:
                    logger.error(
                        f"Pydantic validation error on exit context for {func_name}: {e}",
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
                        execution_time_seconds=elapsed,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        details=log_context_details,
                    )
                    logger.error(
                        f"❌ Error in sync [bold red]{func_name}[/] after {elapsed:.4f}s: [red]{type(e).__name__}: {e}[/]",
                        exc_info=True,
                        extra={"log_context": error_context},
                    )
                except ValidationError as ve:
                    logger.error(
                        f"Pydantic validation error on error context for {func_name}: {ve}",
                        extra={"function_name": func_name},
                    )
                    logger.error(
                        f"❌ Error in sync [bold red]{func_name}[/] after {elapsed:.4f}s: [red]{type(e).__name__}: {e}[/] (Context validation failed)",
                        exc_info=True,
                        extra={"original_error": repr(e), "function_name": func_name},
                    )
                raise
            finally:
                current_function_context.reset(token)

        return async_wrapper if is_async else sync_wrapper

    # 데코레이터를 @trace 또는 @trace() 형태로 사용할 수 있도록 처리
    if _func is None:
        return decorator  # @trace() 처럼 호출된 경우
    else:
        return decorator(_func)  # @trace 처럼 직접 호출된 경우


# --- 예제 사용 ---
# 예제 실행을 위해 asyncio 임포트
import asyncio


# 예제 Pydantic 모델
class UserInfo(BaseModel):
    user_id: int
    username: str
    signup_ts: datetime = Field(default_factory=datetime.now)
    roles: list[str] = []


# --- 로거 가져오기 ---
# 스크립트 최상단 또는 필요한 곳에서 로거를 가져옵니다.
logger = get_logger()


# --- 데코레이터 적용 예제 함수 ---
@trace(level=logging.INFO)  # INFO 레벨로 진입/종료 로깅
def process_data(data: dict, user: UserInfo, *, dry_run: bool = False):
    """동기 함수 예제: 데이터를 처리하고 결과를 반환합니다."""
    logger.info(
        f"데이터 처리 중: data_id={data.get('id')}, user={user.username}",
        extra={
            "user_details": user.model_dump(mode="json"),
            "process_mode": "dry" if dry_run else "live",
        },
    )
    time.sleep(0.1)
    if not data.get("valid"):
        # 사용자 정의 예외를 발생시키는 것이 더 좋을 수 있습니다.
        raise ValueError(f"유효하지 않은 데이터 발견: id={data.get('id')}")
    processed_result = {
        "status": "processed",
        "original_id": data.get("id"),
        "processed_at": datetime.now(),
    }
    logger.debug("세부 처리 완료", extra={"intermediate_result": processed_result})
    return processed_result


@trace  # 기본 DEBUG 레벨로 진입/종료 로깅
async def fetch_remote_config(url: str, timeout: int = 5):
    """비동기 함수 예제: 원격 설정을 가져옵니다."""
    logger.info(f"설정 가져오는 중: {url} (timeout: {timeout}s)")
    await asyncio.sleep(0.2)  # 실제 네트워크 호출 시뮬레이션
    if "error" in url:
        raise ConnectionError(f"원격 서버 연결 실패: {url}")
    config_data = {"config_version": "1.2.3", "url": url, "fetched_at": datetime.now()}
    logger.debug(
        f"설정 데이터 수신 완료 from {url}", extra={"received_config": config_data}
    )
    return config_data


@trace
def nested_sync_call(level: int):
    """중첩된 동기 호출 예제."""
    logger.info(f"Nested sync call level {level}")
    if level < 2:
        nested_sync_call(level + 1)
    time.sleep(0.05)
    return f"Completed level {level}"


@trace
async def nested_async_call(level: int):
    """중첩된 비동기 호출 예제."""
    logger.info(f"Nested async call level {level}")
    if level < 2:
        await nested_async_call(level + 1)
    await asyncio.sleep(0.05)
    return f"Completed async level {level}"


# --- 메인 실행 로직 ---
async def main():
    """예제 코드를 실행하는 메인 비동기 함수."""
    logger.info(
        "[bold magenta]로깅 시스템 시작됨 (Rich Console & JSON File)[/]",
        extra={"system_event": "start", "log_dir": str(LOG_DIR)},
    )

    # --- 동기 함수 테스트 ---
    logger.info("-" * 30, extra={"section": "sync_tests"})
    current_user = UserInfo(user_id=101, username="alice", roles=["admin", "dev"])
    valid_data = {"id": "xyz789", "value": 100, "valid": True}
    invalid_data = {"id": "abc123", "value": 50, "valid": False}

    logger.info("동기 함수 호출 (성공 케이스)")
    try:
        result_sync = process_data(valid_data, user=current_user, dry_run=False)
        # JSON 직렬화 가능한 형태로 로깅 (Rich의 JSON 사용)
        logger.info(
            "동기 함수 성공 결과:", extra={"result": JSON.from_data(result_sync)}
        )
    except Exception as e:
        logger.exception(
            "동기 함수 실행 중 예상치 못한 오류 발생"
        )  # exc_info=True와 동일

    logger.info("동기 함수 호출 (실패 케이스)")
    try:
        process_data(invalid_data, user=current_user)
    except ValueError as e:
        # 데코레이터가 이미 에러를 ERROR 레벨로 로깅했음
        logger.warning(
            f"동기 함수에서 예상된 오류 처리 완료: {e}"
        )  # 추가 정보 로깅 가능

    logger.info("중첩된 동기 함수 호출")
    nested_sync_result = nested_sync_call(0)
    logger.info(f"중첩 동기 호출 결과: {nested_sync_result}")

    # --- 비동기 함수 테스트 ---
    logger.info("-" * 30, extra={"section": "async_tests"})
    logger.info("비동기 함수 호출 (성공 케이스)")
    try:
        config = await fetch_remote_config("https://config.example.com", timeout=10)
        logger.info(
            "비동기 함수 성공 결과:", extra={"config_data": JSON.from_data(config)}
        )
    except Exception as e:
        logger.exception("비동기 함수 실행 중 예상치 못한 오류 발생")

    logger.info("비동기 함수 호출 (실패 케이스)")
    try:
        await fetch_remote_config("https://error.example.com")
    except ConnectionError as e:
        logger.warning(f"비동기 함수에서 예상된 오류 처리 완료: {e}")

    logger.info("중첩된 비동기 함수 호출")
    nested_async_result = await nested_async_call(0)
    logger.info(f"중첩 비동기 호출 결과: {nested_async_result}")

    # --- 직접 로그 메시지 (Pydantic 객체/Dict 포함) ---
    logger.info("-" * 30, extra={"section": "direct_logging"})
    final_user_info = UserInfo(user_id=999, username="final_user", roles=["guest"])
    # Pydantic 모델을 extra에 직접 전달 (JsonFormatter가 처리)
    # RichHandler는 객체를 repr() 형태로 보여줄 수 있음
    logger.info(
        "작업 완료 로그 (Pydantic 객체 포함)", extra={"final_user": final_user_info}
    )

    # 일반 dict를 extra에 전달
    raw_debug_data = {
        "a": 1,
        "b": datetime.now(),
        "c": Path("/tmp/data"),
        "d": [1, 2, {3: 4}],
    }
    # JsonFormatter는 이를 details 필드 아래에 병합 (safe_serialize 사용)
    # RichHandler는 dict를 보기 좋게 표시 (pretty_repr)
    logger.debug(
        "디버그 정보 (일반 dict 포함)",
        extra=raw_debug_data,  # 키 이름을 LogContext 필드와 다르게 하면 충돌 방지
    )
    # LogContext 필드 이름과 같은 키를 사용하면 JSON 로그에서 덮어쓸 수 있음
    logger.warning(
        "주의: extra 키 이름 충돌 가능성", extra={"function_name": "manual_log"}
    )

    logger.info(
        "[bold magenta]로깅 시스템 데모 종료.[/]", extra={"system_event": "stop"}
    )


if __name__ == "__main__":
    # Python 3.7+ 에서는 asyncio.run 사용 가능
    try:
        asyncio.run(main())
    except Exception as e:
        # 최상위 레벨에서 예외 발생 시 로깅
        logger.critical(f"메인 실행 중 치명적 오류 발생: {e}", exc_info=True)
        sys.exit(1)  # 오류 종료 코드
