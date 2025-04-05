import asyncio
import contextvars
import functools
import inspect
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union, overload

# Pydantic import
from pydantic import BaseModel, Field, ValidationError, field_validator

# 내부 임포트
from .logging_config import DEFAULT_LOG_LEVEL
from .logging_setup import get_logger

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
        # Pydantic v1 호환성 (필요시 제거 또는 v2 방식으로 변경)
        # str_strip_whitespace = True
        # json_encoders = {
        #     datetime: lambda v: v.isoformat(),
        #     Path: lambda v: str(v),
        # }
        # Pydantic v2 설정
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: str,
        }

    @field_validator("execution_time_seconds", mode="before")
    @classmethod
    def round_execution_time(cls, v):
        """실행 시간을 소수점 4자리까지 반올림합니다."""
        if isinstance(v, (float, int)):
            return round(v, 4)
        return v


# --- 로깅 데코레이터 헬퍼 함수 ---
def _format_call_args(func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """함수 호출 인자를 repr 문자열 딕셔너리로 포맷합니다."""
    try:
        bound_args = inspect.signature(func).bind(*args, **kwargs)
        bound_args.apply_defaults()
        # 순환 참조나 너무 큰 객체로 인한 문제를 피하기 위해 repr 사용
        return {k: repr(v) for k, v in bound_args.arguments.items()}
    except Exception:
        # 시그니처 바인딩 실패 시 원시 인자 반환
        return {"args": repr(args), "kwargs": repr(kwargs)}


def _log_entry(
    logger: logging.Logger,
    level: int,
    func_name: str,
    module_name: str,
    class_name: Optional[str],
    is_async: bool,
    call_args: Dict[str, Any],
    location: str,  # Combined filename and line number
):
    """함수 진입 로그를 기록합니다."""
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
        # Filter out 'self' argument for logging if it exists
        logged_args = {k: v for k, v in call_args.items() if k != "self"}
        logger.log(
            level,
            f"❇️ Entering {sync_async} [bold {color}]{name}[/] in\n{location} with args: {logged_args}\n",
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
    location: str,  # Combined filename and line number
    result: Optional[Any] = None,  # 결과 로깅은 제외됨 (성능 및 보안)
):
    """함수 종료 로그를 기록합니다."""
    try:
        # 결과 미리보기는 민감 정보 노출 및 성능 저하 가능성으로 제거
        # details = {"result_preview": repr(result)[:200]} if result is not None else None
        context = LogContext(
            event_type="exit",
            function_name=func_name,
            module_name=module_name,
            class_name=class_name,
            is_async=is_async,
            execution_time_seconds=elapsed,
            # details=details, # 결과 미리보기 제거
        )
        sync_async, color = ("async", "cyan") if is_async else ("sync", "green")
        name = f"{class_name}.{func_name}" if class_name else func_name
        logger.log(
            level,  # Corrected: Removed duplicate level argument
            f"☑️ Exited {sync_async} [bold {color}]{name}[/] in {elapsed:.4f}",  # Use location
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
    """함수 실행 중 발생한 오류 로그를 기록합니다."""
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
            details={"call_args": call_args},  # 오류 발생 시 호출 인자 포함
        )
        sync_async = "async" if is_async else "sync"
        name = f"{class_name}.{func_name}" if class_name else func_name
        logger.error(
            f"❌ Error in {sync_async} [bold red]{name}[/] after {elapsed:.4f}s: [red]{type(exception).__name__}: {exception}[/]",
            exc_info=True,  # 트레이스백 포함
            extra={"log_context": context},
        )
    except ValidationError as ve:
        # LogContext 생성 실패 시에도 원본 오류 로깅 시도
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
        # 오류 로깅 자체에서 오류 발생 시
        logger.error(
            f"Critical error while logging error for {func_name}: {e}",
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

    Returns:
        데코레이터가 적용된 함수 또는 클래스.
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
                    # 호출 가능하고, private(_로 시작)이 아니며, 제외 목록에 없는 경우
                    if (
                        callable(method)
                        and not name.startswith(
                            "_"
                        )  # _로 시작하는 protected/private 메서드 제외
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
                                and "__init__"
                                not in current_exclude  # 명시적으로 제외되지 않았는지 확인
                            ):
                                methods_to_trace[name] = method
                            elif (
                                name != "__init__"
                            ):  # __init__이 아닌 다른 public 메서드
                                methods_to_trace[name] = method

            # 찾은 메서드에 데코레이터 적용 (하위 클래스 메서드가 우선 적용되도록)
            for name, method in methods_to_trace.items():
                try:
                    # 내부 함수 데코레이터 호출 (level 전달)
                    traced_method = _function_decorator(
                        method, level
                    )  # level 인자 전달
                    setattr(cls, name, traced_method)
                except Exception as e:
                    logger.warning(
                        f"Failed to apply trace decorator to {cls.__name__}.{name}: {e}"
                    )
            return cls

        elif callable(obj):
            # --- 함수 데코레이팅 로직 ---
            return _function_decorator(obj, level)  # level 인자 전달
        else:
            # 함수나 클래스가 아닌 경우 경고 로깅 후 그대로 반환
            logger.warning(
                f"Trace decorator applied to non-callable, non-class object: {type(obj)}"
            )
            return obj

    def _function_decorator(
        func: Callable, func_level: int
    ) -> Callable:  # level 인자 추가
        # --- 실제 함수를 감싸는 래퍼 ---
        func_name = func.__name__
        module_name = func.__module__
        is_async = inspect.iscoroutinefunction(func)
        logger = get_logger()
        original_filename = inspect.getfile(func)
        try:
            _, lineno = inspect.getsourcelines(func)
            location = f"{original_filename}:{lineno}"
        except (OSError, TypeError):  # Handle cases where source can't be found
            location = original_filename  # Fallback to just filename
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
                logger,
                func_level,
                func_name,
                module_name,
                class_name,
                True,
                call_args,
                location,  # Pass location (filename:lineno)
            )
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                _log_exit(
                    logger,
                    func_level,
                    func_name,
                    module_name,
                    class_name,
                    True,
                    elapsed,
                    location,  # Pass location (filename:lineno)
                )
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
                logger,
                func_level,
                func_name,
                module_name,
                class_name,
                False,
                call_args,
                location,  # Pass location (filename:lineno)
            )
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                _log_exit(
                    logger,
                    func_level,
                    func_name,
                    module_name,
                    class_name,
                    False,
                    elapsed,
                    location,  # Pass location (filename:lineno)
                )
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
