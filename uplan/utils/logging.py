import asyncio
import contextvars
import functools
import inspect
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union, overload

# Pydantic import
from pydantic import BaseModel, Field, ValidationError, field_validator

# Rich imports
from rich.json import JSON
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

# Rich 콘솔 및 트레이스백 핸들러 초기화
install_rich_traceback(show_locals=False)

# --- 설정 ---
DEFAULT_LOG_LEVEL = logging.DEBUG  # 기본 트레이스 레벨을 DEBUG로 변경
FILE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_DIR = Path("logs")
LOG_FILENAME_FORMAT = "app_{timestamp}.log"
JSON_LOG_FILENAME_FORMAT = "app_structured_{timestamp}.log"
CONSOLE_LOG_LEVEL = logging.DEBUG
JSON_LOG_LEVEL = logging.DEBUG
LOGGER_NAME = "tracer"

LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- 컨텍스트 변수 ---
current_function_context = contextvars.ContextVar[Optional[str]](
    "current_function_context", default=None
)


# --- Pydantic 모델 ---
class LogContext(BaseModel):
    """로그 이벤트에 대한 구조화된 컨텍스트 정보."""

    event_type: str = Field(...)
    function_name: Optional[str] = Field(None)
    class_name: Optional[str] = Field(None)
    module_name: Optional[str] = Field(None)
    is_async: Optional[bool] = Field(None)
    execution_time_seconds: Optional[float] = Field(None)
    error_type: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    details: Optional[Dict[str, Any]] = Field(None)

    class Config:
        str_strip_whitespace = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v),
        }

    @field_validator("execution_time_seconds", mode="before")
    @classmethod
    def round_execution_time(cls, v):
        if isinstance(v, (float, int)):
            return round(v, 4)
        return v


# --- JSON 직렬화 헬퍼 ---
def safe_serialize(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        try:
            return obj.model_dump(mode="json", exclude_none=True)
        except Exception:
            return repr(obj)
    if isinstance(obj, (datetime, Path)):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
    try:
        json.dumps(obj)
        return obj
    except (TypeError, OverflowError):
        try:
            return repr(obj)
        except Exception:
            return f"<unserializable type: {type(obj).__name__}>"


# --- JSON 포맷터 ---
class JsonFormatter(logging.Formatter):
    def __init__(self, fmt_keys: Optional[Dict[str, str]] = None):
        super().__init__()
        self.fmt_keys = fmt_keys or {
            "level": "levelname",
            "logger": "name",
            "module": "module",
            "function": "funcName",
            "line": "lineno",
            "thread_name": "threadName",
        }
        self.default_time_format = "%Y-%m-%dT%H:%M:%S"
        self.default_msec_format = "%s.%03dZ"

    def formatTime(self, record, datefmt=None):
        utc_ct = datetime.fromtimestamp(record.created, tz=timezone.utc)
        t = utc_ct.strftime(self.default_time_format)
        return self.default_msec_format % (t, record.msecs)

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {"timestamp": self.formatTime(record)}
        for key, val_key in self.fmt_keys.items():
            val = getattr(record, val_key, None)
            if val is not None:
                log_entry[key] = val

        log_entry["message"] = (
            record.getMessage()
            if not isinstance(record.msg, (dict, list))
            else record.msg
        )

        log_context_data = None
        if hasattr(record, "log_context") and isinstance(
            record.log_context, LogContext
        ):
            try:
                log_context_data = record.log_context.model_dump(
                    mode="json", exclude_none=True
                )
                log_entry.update(log_context_data)
            except Exception as e:
                log_entry["log_context_serialization_error"] = repr(e)

        standard_attrs = list(logging.LogRecord.__dict__.keys()) + [
            "message",
            "asctime",
            "relativeCreated",
            "log_context",
            "args",
        ]
        extra_data = {}
        for k, v in record.__dict__.items():
            is_standard = k in standard_attrs
            is_internal = k.startswith("_")
            is_from_log_context = log_context_data and k in log_context_data
            if not is_standard and not is_internal and not is_from_log_context:
                extra_data[k] = v
        if extra_data:
            log_entry["extra_data"] = {
                k: safe_serialize(v) for k, v in extra_data.items()
            }

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
            }
        elif record.exc_text:
            log_entry["exception_text"] = record.exc_text
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info

        try:
            return json.dumps(log_entry, default=safe_serialize, ensure_ascii=False)
        except Exception as e:
            log_entry["json_serialization_error"] = repr(e)
            return json.dumps(log_entry, default=repr, ensure_ascii=False)


# --- 로깅 설정 ---
def setup_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.hasHandlers():
        return logger
    effective_level = min(CONSOLE_LOG_LEVEL, JSON_LOG_LEVEL)
    logger.setLevel(effective_level)

    console_handler = RichHandler(
        level=CONSOLE_LOG_LEVEL,
        rich_tracebacks=True,
        markup=True,
        show_path=True,
        show_level=True,
        show_time=True,
        log_time_format="[%Y-%m-%d %H:%M:%S.%f]",
        tracebacks_show_locals=False,
    )
    logger.addHandler(console_handler)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_log_filename = LOG_DIR / JSON_LOG_FILENAME_FORMAT.format(timestamp=timestamp)
    json_file_handler = logging.FileHandler(json_log_filename, encoding="utf-8")
    json_file_handler.setLevel(JSON_LOG_LEVEL)
    json_formatter = JsonFormatter()
    json_file_handler.setFormatter(json_formatter)
    logger.addHandler(json_file_handler)

    logger.propagate = False
    return logger


# --- 로거 인스턴스 ---
_logger = setup_logging()


def get_logger() -> logging.Logger:
    return _logger


# --- 로깅 데코레이터 헬퍼 함수 ---
def _format_call_args(func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    try:
        bound_args = inspect.signature(func).bind(*args, **kwargs)
        bound_args.apply_defaults()
        return {k: repr(v) for k, v in bound_args.arguments.items()}
    except Exception:
        return {"args": repr(args), "kwargs": repr(kwargs)}


def _log_entry(
    logger: logging.Logger,
    level: int,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    call_args: Dict[str, Any],
):
    try:
        context = LogContext(
            event_type="entry",
            function_name=func_name,
            module_name=module_name,
            class_name=class_name,
            is_async=is_async,
            details={"call_args": call_args},
        )
        sync_async, color = ("async", "cyan") if is_async else ("sync", "green")
        name = f"{class_name}.{func_name}" if class_name else func_name
        logger.log(
            level,
            f"▶️ Entering {sync_async} [bold {color}]{name}[/]",
            extra={"log_context": context},
        )
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error on entry context for {func_name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error logging entry for {func_name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )


def _log_exit(
    logger: logging.Logger,
    level: int,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    elapsed: float,
    result: Optional[Any] = None,
):
    try:
        details = {"result_preview": repr(result)[:200]} if result is not None else None
        context = LogContext(
            event_type="exit",
            function_name=func_name,
            module_name=module_name,
            class_name=class_name,
            is_async=is_async,
            execution_time_seconds=elapsed,
            details=details,
        )
        sync_async, color = ("async", "cyan") if is_async else ("sync", "green")
        name = f"{class_name}.{func_name}" if class_name else func_name
        logger.log(
            level,
            f"✅ Exited {sync_async} [bold {color}]{name}[/] in {elapsed:.4f}s",
            extra={"log_context": context},
        )
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error on exit context for {func_name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error logging exit for {func_name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )


def _log_error(
    logger: logging.Logger,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    elapsed: float,
    exception: Exception,
    call_args: Dict[str, Any],
):
    try:
        context = LogContext(
            event_type="error",
            function_name=func_name,
            module_name=module_name,
            class_name=class_name,
            is_async=is_async,
            execution_time_seconds=elapsed,
            error_type=type(exception).__name__,
            error_message=str(exception),
            details={"call_args": call_args},
        )
        sync_async = "async" if is_async else "sync"
        name = f"{class_name}.{func_name}" if class_name else func_name
        logger.error(
            f"❌ Error in {sync_async} [bold red]{name}[/] after {elapsed:.4f}s: [red]{type(exception).__name__}: {exception}[/]",
            exc_info=True,
            extra={"log_context": context},
        )
    except ValidationError as ve:
        logger.error(
            f"Pydantic validation error on error context for {func_name}: {ve}",
            extra={"function_name": func_name, "class_name": class_name},
        )
        logger.error(
            f"❌ Error in {sync_async} [bold red]{name}[/] after {elapsed:.4f}s: [red]{type(exception).__name__}: {exception}[/] (Context validation failed)",
            exc_info=True,
            extra={
                "original_error": repr(exception),
                "function_name": func_name,
                "class_name": class_name,
            },
        )
    except Exception as e:
        logger.error(
            f"Error logging error for {func_name}: {e}",
            exc_info=True,
            extra={
                "function_name": func_name,
                "class_name": class_name,
                "original_error": repr(exception),
            },
        )


# --- 통합 트레이싱 데코레이터 ---


# Overloads for type hinting
@overload
def trace(
    _obj: Type,
    *,
    level: int = DEFAULT_LOG_LEVEL,
    include_init: bool = False,
    exclude_methods: Optional[List[str]] = None,
) -> Type: ...


@overload
def trace(
    _obj: Optional[Callable] = None,
    *,
    level: int = DEFAULT_LOG_LEVEL,
    include_init: bool = False,  # Ignored for functions
    exclude_methods: Optional[List[str]] = None,  # Ignored for functions
) -> Callable: ...


def trace(
    _obj: Optional[Union[Callable, Type]] = None,
    *,
    level: int = DEFAULT_LOG_LEVEL,
    include_init: bool = False,
    exclude_methods: Optional[List[str]] = None,
) -> Union[Callable, Type]:
    """
    함수 또는 클래스의 메서드 호출을 로깅하는 통합 데코레이터.

    클래스에 적용 시: 지정된 public 메서드에 트레이싱을 적용합니다.
    함수에 적용 시: 해당 함수의 시작, 종료, 예외를 로깅합니다.

    Args:
        _obj: 데코레이터가 적용될 함수 또는 클래스.
        level: 진입/종료 로그 레벨 (기본값: logging.DEBUG). 오류는 항상 ERROR 레벨.
        include_init (클래스 전용): True이면 __init__ 메서드도 트레이싱 (기본값: False).
        exclude_methods (클래스 전용): 트레이싱에서 제외할 메서드 이름 목록.
    """
    exclude = exclude_methods or []

    def decorator(obj: Union[Callable, Type]) -> Union[Callable, Type]:
        logger = get_logger()

        if isinstance(obj, type):
            # --- 클래스 데코레이팅 로직 ---
            cls = obj
            current_exclude = list(exclude)  # 원본 리스트 변경 방지
            if not include_init:
                current_exclude.append("__init__")

            methods_to_trace = {}
            # 클래스 계층 구조를 순회하며 메서드 찾기 (MRO 사용)
            for base_cls in reversed(cls.__mro__):
                if base_cls is object:
                    continue  # object 클래스는 건너뜀
                for name, method in base_cls.__dict__.items():
                    if (
                        callable(method)
                        and not name.startswith("_")
                        and name not in current_exclude
                    ):
                        # 함수 또는 코루틴 함수인지 확인
                        if inspect.isfunction(method) or inspect.iscoroutinefunction(
                            method
                        ):
                            # __init__ 특별 처리
                            if (
                                name == "__init__"
                                and include_init
                                and "__init__" not in current_exclude
                            ):
                                methods_to_trace[name] = method
                            elif name != "__init__":
                                methods_to_trace[name] = method

            # 찾은 메서드에 데코레이터 적용 (하위 클래스 메서드가 우선 적용되도록)
            for name, method in methods_to_trace.items():
                try:
                    # 내부 함수 데코레이터 호출 (level 전달)
                    traced_method = _function_decorator(method)
                    setattr(cls, name, traced_method)
                except Exception as e:
                    logger.warning(
                        f"Failed to apply trace decorator to {cls.__name__}.{name}: {e}"
                    )
            return cls

        elif callable(obj):
            # --- 함수 데코레이팅 로직 ---
            return _function_decorator(obj)
        else:
            # 함수나 클래스가 아닌 경우 그대로 반환 (또는 오류 발생)
            logger.warning(
                f"Trace decorator applied to non-callable, non-class object: {type(obj)}"
            )
            return obj

    def _function_decorator(func: Callable) -> Callable:
        # --- 실제 함수를 감싸는 래퍼 ---
        func_name = func.__name__
        module_name = func.__module__
        is_async = inspect.iscoroutinefunction(func)
        logger = get_logger()
        class_name: Optional[str] = None
        try:
            # func.__qualname__ 접근 시 AttributeError 발생 가능성 처리 (e.g., 일부 내장 함수)
            if "." in func.__qualname__:
                class_name = func.__qualname__.rsplit(".", 1)[0]
        except AttributeError:
            pass  # class_name은 None으로 유지

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            parent_context = current_function_context.get()
            current_ctx_name = f"{class_name}.{func_name}" if class_name else func_name
            full_context = (
                f"{parent_context} -> {current_ctx_name}"
                if parent_context
                else current_ctx_name
            )
            token = current_function_context.set(full_context)
            start_time = time.perf_counter()
            call_args = _format_call_args(func, args, kwargs)
            _log_entry(
                logger, level, func_name, module_name, class_name, True, call_args
            )
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                _log_exit(
                    logger, level, func_name, module_name, class_name, True, elapsed
                )  # result 로깅 제외
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                _log_error(
                    logger,
                    func_name,
                    module_name,
                    class_name,
                    True,
                    elapsed,
                    e,
                    call_args,
                )
                raise
            finally:
                current_function_context.reset(token)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            parent_context = current_function_context.get()
            current_ctx_name = f"{class_name}.{func_name}" if class_name else func_name
            full_context = (
                f"{parent_context} -> {current_ctx_name}"
                if parent_context
                else current_ctx_name
            )
            token = current_function_context.set(full_context)
            start_time = time.perf_counter()
            call_args = _format_call_args(func, args, kwargs)
            _log_entry(
                logger, level, func_name, module_name, class_name, False, call_args
            )
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                _log_exit(
                    logger, level, func_name, module_name, class_name, False, elapsed
                )  # result 로깅 제외
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                _log_error(
                    logger,
                    func_name,
                    module_name,
                    class_name,
                    False,
                    elapsed,
                    e,
                    call_args,
                )
                raise
            finally:
                current_function_context.reset(token)

        return async_wrapper if is_async else sync_wrapper

    # 데코레이터 사용 방식 처리 (@trace 또는 @trace(...))
    if _obj is None:
        # @trace(...) 형태로 호출됨 -> decorator 반환
        return decorator
    else:
        # @trace 형태로 호출됨 -> decorator(_obj) 즉시 실행
        return decorator(_obj)


# --- 예제 사용 ---
class UserInfo(BaseModel):
    user_id: int
    username: str
    signup_ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    roles: list[str] = []


logger = get_logger()


@trace(level=logging.INFO)
def process_data(data: dict, user: UserInfo, *, dry_run: bool = False):
    logger.info(
        f"데이터 처리 중: data_id={data.get('id')}, user={user.username}",
        extra={"user_details": user, "process_mode": "dry" if dry_run else "live"},
    )
    time.sleep(0.1)
    if not data.get("valid"):
        raise ValueError(f"유효하지 않은 데이터 발견: id={data.get('id')}")
    processed_result = {
        "status": "processed",
        "original_id": data.get("id"),
        "processed_at": datetime.now(timezone.utc),
    }
    logger.debug("세부 처리 완료", extra={"intermediate_result": processed_result})
    return processed_result


@trace
async def fetch_remote_config(url: str, timeout: int = 5):
    logger.info(f"설정 가져오는 중: {url} (timeout: {timeout}s)")
    await asyncio.sleep(0.2)
    if "error" in url:
        raise ConnectionError(f"원격 서버 연결 실패: {url}")
    config_data = {
        "config_version": "1.2.3",
        "url": url,
        "fetched_at": datetime.now(timezone.utc),
    }
    logger.debug(
        f"설정 데이터 수신 완료 from {url}", extra={"received_config": config_data}
    )
    return config_data


@trace
def nested_sync_call(level: int):
    logger.info(f"Nested sync call level {level}")
    if level < 2:
        nested_sync_call(level + 1)
    time.sleep(0.05)
    return f"Completed level {level}"


@trace
async def nested_async_call(level: int):
    logger.info(f"Nested async call level {level}")
    if level < 2:
        await nested_async_call(level + 1)
    await asyncio.sleep(0.05)
    return f"Completed async level {level}"


# 클래스 데코레이터 적용 예제 (통합된 trace 사용)
@trace(level=logging.INFO, include_init=True, exclude_methods=["_internal_helper"])
class DataProcessor:
    def __init__(self, name: str):
        self.name = name
        logger.info(f"DataProcessor '{self.name}' initialized.")
        self._internal_state = "ready"

    def process_item(self, item_id: int) -> str:
        logger.info(f"Processing item {item_id} with {self.name}")
        time.sleep(0.08)
        if item_id % 3 == 0:
            raise RuntimeError(f"Processing failed for item {item_id}")
        return f"Item {item_id} processed by {self.name}"

    async def process_item_async(self, item_id: int) -> str:
        logger.info(f"Async processing item {item_id} with {self.name}")
        await asyncio.sleep(0.12)
        if item_id % 4 == 0:
            raise asyncio.TimeoutError(f"Async processing timed out for item {item_id}")
        return f"Item {item_id} processed async by {self.name}"

    def _internal_helper(self):
        logger.debug("Internal helper called.")


# --- 메인 실행 로직 ---
async def main():
    logger.info(
        "[bold magenta]로깅 시스템 시작됨 (Rich Console & JSON File)[/]",
        extra={"system_event": "start", "log_dir": str(LOG_DIR)},
    )

    # --- 동기 함수 테스트 ---
    logger.info("-" * 30, extra={"section": "sync_tests"})
    current_user = UserInfo(user_id=101, username="alice", roles=["admin", "dev"])
    valid_data = {"id": "xyz789", "value": 100, "valid": True}
    invalid_data = {"id": "abc123", "value": 50, "valid": False}
    try:
        result_sync = process_data(valid_data, user=current_user)
        logger.info("동기 함수 성공 결과:", extra={"result": result_sync})
    except Exception:
        logger.exception("동기 함수 실행 중 예상치 못한 오류 발생")
    try:
        process_data(invalid_data, user=current_user)
    except ValueError as e:
        logger.warning(f"동기 함수에서 예상된 오류 처리 완료: {e}")
    nested_sync_result = nested_sync_call(0)
    logger.info(f"중첩 동기 호출 결과: {nested_sync_result}")

    # --- 비동기 함수 테스트 ---
    logger.info("-" * 30, extra={"section": "async_tests"})
    try:
        config = await fetch_remote_config("https://config.example.com")
        logger.info("비동기 함수 성공 결과:", extra={"config_data": config})
    except Exception:
        logger.exception("비동기 함수 실행 중 예상치 못한 오류 발생")
    try:
        await fetch_remote_config("https://error.example.com")
    except ConnectionError as e:
        logger.warning(f"비동기 함수에서 예상된 오류 처리 완료: {e}")
    nested_async_result = await nested_async_call(0)
    logger.info(f"중첩 비동기 호출 결과: {nested_async_result}")

    # --- 클래스 데코레이터 테스트 ---
    logger.info("-" * 30, extra={"section": "class_decorator_tests"})
    processor = DataProcessor("ProcessorAlpha")
    try:
        class_sync_result = processor.process_item(1)
        logger.info(f"클래스 동기 메서드 결과: {class_sync_result}")
    except Exception:
        logger.exception("클래스 동기 메서드 오류 발생")
    try:
        processor.process_item(3)
    except RuntimeError as e:
        logger.warning(f"클래스 동기 메서드 예상된 오류 처리: {e}")
    try:
        class_async_result = await processor.process_item_async(5)
        logger.info(f"클래스 비동기 메서드 결과: {class_async_result}")
    except Exception:
        logger.exception("클래스 비동기 메서드 오류 발생")
    try:
        await processor.process_item_async(8)
    except asyncio.TimeoutError as e:
        logger.warning(f"클래스 비동기 메서드 예상된 오류 처리: {e}")
    processor._internal_helper()

    # --- 직접 로그 메시지 ---
    logger.info("-" * 30, extra={"section": "direct_logging"})
    final_user_info = UserInfo(user_id=999, username="final_user", roles=["guest"])
    logger.info(
        "작업 완료 로그 (Pydantic 객체 포함)", extra={"final_user": final_user_info}
    )
    raw_debug_data = {
        "a": 1,
        "b": datetime.now(timezone.utc),
        "c": Path("/tmp/data"),
        "d": [1, 2, {3: 4}],
        "nested": {"e": True},
    }
    logger.debug("디버그 정보 (일반 dict 포함)", extra=raw_debug_data)
    logger.warning(
        "주의: extra 키 이름 충돌 가능성", extra={"function_name": "manual_log"}
    )

    logger.info(
        "[bold magenta]로깅 시스템 데모 종료.[/]", extra={"system_event": "stop"}
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"메인 실행 중 치명적 오류 발생: {e}", exc_info=True)
        sys.exit(1)
