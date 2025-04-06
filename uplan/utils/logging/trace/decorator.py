import functools
import inspect
import time
from pathlib import Path
from typing import Any, Callable, List, Optional, Type, Union, overload

from uplan.utils.logging.logging_setup import get_logger
from uplan.utils.logging.trace.context import current_function_context, call_depth
from uplan.utils.logging.trace.helpers import format_call_args
from uplan.utils.logging.trace.loggers import log_entry, log_exit, log_error

import logging

DEFAULT_LOG_LEVEL = logging.DEBUG


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
    include_init: bool = False,
    exclude_methods: Optional[List[str]] = None,
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
            cls = obj
            current_exclude = list(exclude)
            if not include_init:
                current_exclude.append("__init__")

            methods_to_trace = {}
            for base_cls in reversed(cls.__mro__):
                if base_cls is object:
                    continue
                for name, method in base_cls.__dict__.items():
                    if name in current_exclude:
                        continue
                    is_special = name.startswith("__") and name.endswith("__")
                    if is_special and name != "__init__":
                        continue
                    if name.startswith("_") and not is_special:
                        continue
                    if callable(method):
                        if name in methods_to_trace:
                            continue
                        if inspect.isfunction(method) or inspect.iscoroutinefunction(
                            method
                        ):
                            if name == "__init__" and include_init:
                                methods_to_trace[name] = method
                            elif name != "__init__":
                                methods_to_trace[name] = method

            for name, method in methods_to_trace.items():
                try:
                    traced_method = _wrap_function(method, level)
                    setattr(cls, name, traced_method)
                except Exception as e:
                    logger.warning(
                        f"Failed to apply trace to {cls.__name__}.{name}: {e}"
                    )
            return cls

        elif callable(obj):
            return _wrap_function(obj, level)

        else:
            logger.warning(
                f"Trace decorator applied to non-callable, non-class object: {type(obj)}"
            )
            return obj

    def _wrap_function(func: Callable, func_level: int) -> Callable:
        func_name = func.__name__
        module_name = func.__module__
        is_async = inspect.iscoroutinefunction(func)
        logger = get_logger()

        try:
            filename = inspect.getfile(func)
            lines, lineno = inspect.getsourcelines(func)
            p = Path(filename)
            location = f"{p.parent.name}/{p.name}:{lineno}"
        except (OSError, TypeError, IOError):
            location = module_name

        class_name: Optional[str] = None
        try:
            qualname_parts = func.__qualname__.split(".")
            if len(qualname_parts) > 1:
                class_name = qualname_parts[-2]
        except AttributeError:
            pass

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
            current_depth = parent_depth + 1
            token_depth = call_depth.set(current_depth)

            start = time.perf_counter()
            call_args = {}
            try:
                call_args = format_call_args(func, args, kwargs)
                log_entry(
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
                log_exit(
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
                if not call_args:
                    try:
                        call_args = format_call_args(func, args, kwargs)
                    except Exception:
                        call_args = {
                            "args": repr(args),
                            "kwargs": repr(kwargs),
                            "error": "Failed to format arguments",
                        }
                log_error(
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
                raise
            finally:
                call_depth.reset(token_depth)
                current_function_context.reset(token_ctx)

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
            current_depth = parent_depth + 1
            token_depth = call_depth.set(current_depth)

            start = time.perf_counter()
            call_args = {}
            try:
                call_args = format_call_args(func, args, kwargs)
                log_entry(
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
                log_exit(
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
                        call_args = format_call_args(func, args, kwargs)
                    except Exception:
                        call_args = {
                            "args": repr(args),
                            "kwargs": repr(kwargs),
                            "error": "Failed to format arguments",
                        }
                log_error(
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

    if _obj is None:
        return decorator
    else:
        return decorator(_obj)
