import asyncio
import contextvars
import functools
import inspect
import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, overload

from pydantic import BaseModel, Field, ValidationError, field_validator

# 가정: logging_config 및 logging_setup은 이미 정의되어 있음
# from .logging_config import DEFAULT_LOG_LEVEL
# from .logging_setup import get_logger
from uplan.utils.logging.logging_setup import get_logger

DEFAULT_LOG_LEVEL = logging.DEBUG  # fallback level if needed


# --- Context Variables ---
current_function_context = contextvars.ContextVar[Optional[str]](
    "current_function_context", default=None
)
call_depth = contextvars.ContextVar[int]("call_depth", default=0)


# --- Pydantic Model ---
class LogContext(BaseModel):
    """Structured context info for log events."""

    event_type: str = Field(...)
    function_name: Optional[str] = Field(None)
    class_name: Optional[str] = Field(None)
    module_name: Optional[str] = Field(None)
    is_async: Optional[bool] = Field(None)
    execution_time_seconds: Optional[float] = Field(None)
    error_type: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    details: Optional[Dict[str, Any]] = Field(default=None)
    depth: Optional[int] = Field(None)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: str,
        }

    @field_validator("execution_time_seconds", mode="before")
    @classmethod
    def round_execution_time(cls, v):
        if isinstance(v, (float, int)):
            return round(v, 4)
        return v


# --- Color Palette ---
DEPTH_COLORS: List[str] = [
    "#b9e97c",
    "#f0e6a8",
    "#fdbb6f",
    "#f58fa8",
    "#99d4f0",
    "#c1a6ff",
    "#f58f8f",
    "#f0e6a8",
    "#b9e97c",
    "#99d4f0",
]


# --- Helper Functions ---
def _format_call_args(func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    try:
        bound = inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
        # repr() 대신 간단한 문자열 변환 사용 시도 (필요에 따라 조정)
        return {
            k: str(v) if isinstance(v, Path) else repr(v)
            for k, v in bound.arguments.items()
        }
    except Exception:
        return {"args": repr(args), "kwargs": repr(kwargs)}


def _get_color(depth: int) -> str:
    # 0-based depth이지만 로그 출력은 1-based depth를 사용하므로 조정
    return DEPTH_COLORS[(depth - 1) % len(DEPTH_COLORS)]


def _build_indent(depth: int) -> str:
    # depth 0은 indent 없음, depth 1은 indent 없음, depth 2부터 이전 depth의 bar 추가
    if depth <= 1:
        return ""
    return "".join(f"[{_get_color(i)}]│   [/] " for i in range(1, depth))


def _pretty_json(data: dict, indent_prefix: str) -> str:
    """Indents each line of the JSON string with the provided prefix."""
    try:
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        return "\n".join(f"{indent_prefix}{line}" for line in pretty.splitlines())
    except TypeError as e:
        # Handle potential serialization errors gracefully
        return f"{indent_prefix}{{... serialization error: {e} ...}}"
    except Exception as e:
        return f"{indent_prefix}{{... unknown error during json dump: {e} ...}}"


# _log_with_context 제거


def _log_entry(
    logger: logging.Logger,
    level: int,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    call_args: Dict[str, Any],
    location: str,
    depth: int,  # 1-based depth
) -> None:
    context = LogContext(
        event_type="entry",
        function_name=func_name,
        module_name=module_name,
        class_name=class_name,
        is_async=is_async,
        details={"call_args": call_args},
        depth=depth,
    )
    color = _get_color(depth)
    # indent는 현재 depth *이전까지*의 bar들을 포함
    indent = _build_indent(depth)
    # 현재 depth의 로그 라인들에 사용할 접두사들
    entry_prefix = indent + f"[{color}]├──[/] "
    child_prefix = indent + f"[{color}]│   [/] "

    sync_async = "async" if is_async else "sync"
    name = f"{class_name}.{func_name}" if class_name else func_name
    depth_str = f"[[{color}]Depth:{depth}[/]]"
    colored_name = f"[bold {color}]{name}[/]"
    colored_location = f"[{color}]{location}[/]"

    args_to_format = {k: v for k, v in call_args.items() if k != "self"}
    # _pretty_json에 후속 라인용 접두사(child_prefix)를 전달하여 각 JSON 라인을 올바르게 들여쓰기
    args_json_str = _pretty_json(args_to_format, child_prefix)

    # 전체 메시지를 직접 구성
    message_parts = [
        f"{entry_prefix}{depth_str} 🟢 Entry {sync_async} {colored_name}",
        f"{child_prefix}Args:",
        args_json_str,  # 이미 올바르게 들여쓰기된 JSON 문자열
        f"{child_prefix}Location: {colored_location}",
    ]
    message = "\n".join(
        m for m in message_parts if m is not None and m.strip() != ""
    )  # 빈 줄 제거

    try:
        logger.log(level, message, extra={"log_context": context})
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error during logging for {name}: {e}",
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
    # location: str, # Exit 로그에는 Location 불필요할 수 있음
    depth: int,  # 1-based depth
) -> None:
    context = LogContext(
        event_type="exit",
        function_name=func_name,
        module_name=module_name,
        class_name=class_name,
        is_async=is_async,
        execution_time_seconds=elapsed,
        depth=depth,
    )
    color = _get_color(depth)
    indent = _build_indent(depth)
    # 종료 라인용 접두사
    exit_prefix = indent + f"[{color}]└──[/] "

    sync_async = "async" if is_async else "sync"
    name = f"{class_name}.{func_name}" if class_name else func_name
    depth_str = f"[[{color}]Depth:{depth}[/]]"
    colored_name = f"[bold {color}]{name}[/]"

    # 단일 라인 메시지 직접 구성
    message = f"{exit_prefix}{depth_str} 🏿 Exit {sync_async} {colored_name} in {elapsed:.4f}s"

    try:
        logger.log(level, message, extra={"log_context": context})
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error during logging for {name}: {e}",
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
    location: str,  # 에러 발생 위치 (기본)
    depth: int,  # 1-based depth
) -> None:
    import traceback

    tb = exception.__traceback__
    extracted_tb = traceback.extract_tb(tb)
    precise_location = location  # 기본값
    if extracted_tb:
        last_frame = extracted_tb[-1]
        # 경로를 조금 더 짧게 표시할 수 있음 (예: 프로젝트 루트 기준 상대 경로)
        try:
            precise_location = (
                f"{Path(last_frame.filename).name}:{last_frame.lineno}"  # 파일명만 표시
            )
        except Exception:
            precise_location = (
                f"{last_frame.filename}:{last_frame.lineno}"  # 실패 시 전체 경로
            )

    context = LogContext(
        event_type="error",
        function_name=func_name,
        module_name=module_name,
        class_name=class_name,
        is_async=is_async,
        execution_time_seconds=elapsed,
        error_type=type(exception).__name__,
        error_message=str(exception),
        details={"call_args": call_args, "location": precise_location},
        depth=depth,
    )
    color = _get_color(depth)
    indent = _build_indent(depth)
    # 에러 로그용 접두사 (exit과 동일하게 종료 표시)
    error_prefix = indent + f"[{color}]└──[/] "
    # 에러 로그의 후속 라인용 접두사 (가독성을 위해 약간 다르게 할 수도 있음, 여기선 동일하게)
    # child_prefix_error = indent + f"[{color}]   [/] " # 세로선 대신 공백 사용 옵션
    child_prefix_error = indent + f"[{color}]│   [/] "  # entry와 동일하게 유지

    sync_async = "async" if is_async else "sync"
    name = f"{class_name}.{func_name}" if class_name else func_name
    depth_str = f"[[{color}]Depth:{depth}[/]]"
    colored_name = f"[bold {color}]{name}[/]"
    colored_location = f"[{color}]{precise_location}[/]"

    args_to_format = {k: v for k, v in call_args.items() if k != "self"}
    args_json_str = _pretty_json(args_to_format, child_prefix_error)

    # 에러 메시지 직접 구성
    message_parts = [
        f"{error_prefix}{depth_str} 🟥 [bold red]Error[/] in {sync_async} {colored_name} after {elapsed:.4f}s",
        f"{child_prefix_error}Args:",
        f"[{color}]{args_json_str}[/]",  # Args JSON 부분에 색상 적용?
        # args_json_str, # 색상 없이
        f"{child_prefix_error}Location: {colored_location}",
        f"{child_prefix_error}[bold red]{type(exception).__name__}:[/] [red]{exception}[/]",
    ]
    message = "\n".join(m for m in message_parts if m is not None and m.strip() != "")

    try:
        logger.log(logging.ERROR, message, extra={"log_context": context})
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error during error logging for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )
    except Exception as e:
        logger.error(
            f"Error during error logging for {name}: {e}",
            extra={"function_name": func_name, "class_name": class_name},
        )


# --- Trace Decorator ---
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
    include_init: bool = False,  # 클래스 데코레이터에서만 의미 있음
    exclude_methods: Optional[List[str]] = None,  # 클래스 데코레이터에서만 의미 있음
) -> Callable: ...


def trace(
    _obj: Optional[Union[Callable, Type]] = None,
    *,
    level: int = DEFAULT_LOG_LEVEL,
    include_init: bool = False,
    exclude_methods: Optional[List[str]] = None,
) -> Union[Callable, Type]:
    """
    Decorator to trace function or class method calls.

    Args:
        _obj: Function or class to decorate.
        level: Log level for entry/exit logs.
        include_init: If True, trace __init__ method (class decorator only).
        exclude_methods: List of method names to exclude (class decorator only).

    Returns:
        Decorated function or class.
    """
    exclude = exclude_methods or []

    def decorator(obj: Union[Callable, Type]) -> Union[Callable, Type]:
        logger = get_logger()

        if isinstance(obj, type):
            # Class decorator logic
            cls = obj
            current_exclude = list(exclude)  # 복사해서 사용
            if not include_init:
                current_exclude.append("__init__")

            methods_to_trace = {}
            # MRO를 순회하며 메소드 찾기 (상속 고려)
            for base_cls in reversed(cls.__mro__):
                if base_cls is object:
                    continue
                for name, method in base_cls.__dict__.items():
                    # 이름 규칙 및 제외 목록 확인
                    if name in current_exclude:
                        continue
                    is_special = name.startswith("__") and name.endswith("__")
                    if is_special and name != "__init__":
                        continue  # init 외 스페셜 메소드 제외
                    if name.startswith("_") and not is_special:
                        continue  # private/protected 제외

                    # 호출 가능한 함수/메소드인지 확인
                    if callable(method):
                        # 이미 처리된 메소드는 건너뜀 (하위 클래스 우선)
                        if name in methods_to_trace:
                            continue

                        # 데코레이팅할 함수인지 최종 확인
                        # (staticmethod, classmethod 등도 고려될 수 있으나 여기선 단순 함수/코루틴만)
                        if inspect.isfunction(method) or inspect.iscoroutinefunction(
                            method
                        ):
                            # __init__ 처리
                            if name == "__init__" and include_init:
                                methods_to_trace[name] = method
                            elif name != "__init__":
                                methods_to_trace[name] = method

            # 선택된 메소드들에 데코레이터 적용
            for name, method in methods_to_trace.items():
                try:
                    # level 인자를 _wrap_function에 전달
                    traced_method = _wrap_function(method, level)
                    setattr(cls, name, traced_method)
                except Exception as e:
                    logger.warning(
                        f"Failed to apply trace to {cls.__name__}.{name}: {e}"
                    )
            return cls

        elif callable(obj):
            # Function decorator logic
            return _wrap_function(obj, level)  # level 인자 전달

        else:
            # 데코레이터를 잘못된 타입에 적용한 경우
            logger.warning(
                f"Trace decorator applied to non-callable, non-class object: {type(obj)}"
            )
            return obj  # 원본 객체 반환

    # 내부 함수: 실제 함수 래핑 로직
    def _wrap_function(func: Callable, func_level: int) -> Callable:
        func_name = func.__name__
        module_name = func.__module__
        is_async = inspect.iscoroutinefunction(func)
        logger = get_logger()

        try:
            # 소스 위치 가져오기 (실패 가능성 있음)
            filename = inspect.getfile(func)
            lines, lineno = inspect.getsourcelines(func)
            # 경로 단축 (예: 프로젝트 루트 기준) - 필요시 구현
            location = f"{Path(filename).name}:{lineno}"  # 파일명만 사용
        except (OSError, TypeError, IOError):
            location = module_name  # 실패 시 모듈 이름 사용

        class_name: Optional[str] = None
        try:
            # 클래스명 추출 시도
            qualname_parts = func.__qualname__.split(".")
            if len(qualname_parts) > 1:
                class_name = qualname_parts[-2]
        except AttributeError:
            pass  # 클래스 외부 함수

        # Async 함수 래퍼
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            parent_ctx = current_function_context.get()
            current_ctx_name = f"{class_name}.{func_name}" if class_name else func_name
            full_ctx = (
                f"{parent_ctx} -> {current_ctx_name}"
                if parent_ctx
                else current_ctx_name
            )
            token_ctx = current_function_context.set(full_ctx)

            parent_depth = call_depth.get()
            current_depth = parent_depth + 1  # Depth는 1부터 시작
            token_depth = call_depth.set(current_depth)

            start = time.perf_counter()
            call_args = {}  # 먼저 초기화
            try:
                call_args = _format_call_args(func, args, kwargs)
                _log_entry(
                    logger,
                    func_level,
                    func_name,
                    module_name,
                    class_name,
                    True,
                    call_args,
                    location,
                    current_depth,
                )
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                _log_exit(
                    logger,
                    func_level,
                    func_name,
                    module_name,
                    class_name,
                    True,
                    elapsed,
                    current_depth,
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                # call_args가 Exception 발생 전에 설정되었는지 확인
                if not call_args:
                    try:
                        call_args = _format_call_args(func, args, kwargs)
                    except Exception:  # 인자 포맷팅 실패 시
                        call_args = {
                            "args": repr(args),
                            "kwargs": repr(kwargs),
                            "error": "Failed to format arguments",
                        }
                _log_error(
                    logger,
                    func_name,
                    module_name,
                    class_name,
                    True,
                    elapsed,
                    e,
                    call_args,
                    location,
                    current_depth,
                )
                raise  # 원래 예외 다시 발생
            finally:
                call_depth.reset(token_depth)
                current_function_context.reset(token_ctx)

        # Sync 함수 래퍼
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            parent_ctx = current_function_context.get()
            current_ctx_name = f"{class_name}.{func_name}" if class_name else func_name
            full_ctx = (
                f"{parent_ctx} -> {current_ctx_name}"
                if parent_ctx
                else current_ctx_name
            )
            token_ctx = current_function_context.set(full_ctx)

            parent_depth = call_depth.get()
            current_depth = parent_depth + 1  # Depth는 1부터 시작
            token_depth = call_depth.set(current_depth)

            start = time.perf_counter()
            call_args = {}
            try:
                call_args = _format_call_args(func, args, kwargs)
                _log_entry(
                    logger,
                    func_level,
                    func_name,
                    module_name,
                    class_name,
                    False,
                    call_args,
                    location,
                    current_depth,
                )
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                _log_exit(
                    logger,
                    func_level,
                    func_name,
                    module_name,
                    class_name,
                    False,
                    elapsed,
                    current_depth,
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                if not call_args:
                    try:
                        call_args = _format_call_args(func, args, kwargs)
                    except Exception:
                        call_args = {
                            "args": repr(args),
                            "kwargs": repr(kwargs),
                            "error": "Failed to format arguments",
                        }
                _log_error(
                    logger,
                    func_name,
                    module_name,
                    class_name,
                    False,
                    elapsed,
                    e,
                    call_args,
                    location,
                    current_depth,
                )
                raise
            finally:
                call_depth.reset(token_depth)
                current_function_context.reset(token_ctx)

        return async_wrapper if is_async else sync_wrapper

    # 데코레이터 적용 (@trace 또는 @trace(...) 호출 처리)
    if _obj is None:
        # @trace(...) 형태로 호출됨, decorator 함수 반환
        return decorator
    else:
        # @trace 형태로 호출됨, 바로 객체에 decorator 적용
        return decorator(_obj)
