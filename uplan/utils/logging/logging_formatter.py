import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

# 상대 경로 임포트 (순환 참조 방지를 위해 try-except 사용 또는 나중에 수정)
# LogContext는 logging_trace 모듈로 이동될 예정입니다.
# 현재 단계에서는 임시로 정의하거나, 나중에 임포트 구문을 수정해야 할 수 있습니다.
# 우선 임포트를 시도하고, 안되면 임시 정의를 사용합니다.
try:
    from .logging_trace import LogContext
except ImportError:
    # 임시 LogContext 정의 (실제 정의는 logging_trace.py에 있음)
    class LogContext(BaseModel):
        pass


# --- JSON 직렬화 헬퍼 ---
def safe_serialize(obj: Any) -> Any:
    """객체를 JSON 직렬화 가능한 형태로 안전하게 변환합니다."""
    if isinstance(obj, BaseModel):
        try:
            # Pydantic v2 호환
            return obj.model_dump(mode="json", exclude_none=True)
        except Exception:
            return repr(obj)
    if isinstance(obj, (datetime, Path)):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
    try:
        # 간단한 타입은 직접 직렬화 시도
        json.dumps(obj)
        return obj
    except (TypeError, OverflowError):
        # 직렬화 불가능한 경우 repr 사용
        try:
            return repr(obj)
        except Exception:
            # repr 조차 실패하는 극단적인 경우
            return f"<unserializable type: {type(obj).__name__}>"


# --- JSON 포맷터 ---
class JsonFormatter(logging.Formatter):
    """로그 레코드를 JSON 형식으로 포맷합니다."""

    def __init__(self, fmt_keys: Optional[Dict[str, str]] = None):
        """
        JsonFormatter를 초기화합니다.

        Args:
            fmt_keys: 로그 레코드 속성을 JSON 키에 매핑하는 딕셔너리.
                      None이면 기본 매핑을 사용합니다.
        """
        super().__init__()
        self.fmt_keys = fmt_keys or {
            "level": "levelname",
            "logger": "name",
            "module": "module",
            "function": "funcName",
            "line": "lineno",
            "thread_name": "threadName",
        }
        # ISO 8601 유사 형식 (UTC 기준)
        self.default_time_format = "%Y-%m-%dT%H:%M:%S"
        self.default_msec_format = "%s.%03dZ"

    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        """
        로그 레코드의 생성 시간을 UTC 기준 ISO 8601 형식 문자열로 변환합니다.

        Args:
            record: 포맷할 로그 레코드.
            datefmt: 사용할 날짜 형식 (무시됨, 항상 UTC ISO 형식 사용).

        Returns:
            포맷된 시간 문자열.
        """
        utc_ct = datetime.fromtimestamp(record.created, tz=timezone.utc)
        t = utc_ct.strftime(self.default_time_format)
        return self.default_msec_format % (t, record.msecs)

    def format(self, record: logging.LogRecord) -> str:
        """
        주어진 로그 레코드를 JSON 문자열로 포맷합니다.

        Args:
            record: 포맷할 로그 레코드.

        Returns:
            JSON 형식의 로그 문자열.
        """
        log_entry: Dict[str, Any] = {"timestamp": self.formatTime(record)}

        # Always include source location info
        log_entry["location"] = f"{record.pathname}:{record.lineno}"

        # fmt_keys에 따라 기본 로그 속성 추가
        for key, val_key in self.fmt_keys.items():
            val = getattr(record, val_key, None)
            if val is not None:
                log_entry[key] = val

        # 메시지 처리 (dict/list인 경우 그대로 사용, 아니면 getMessage() 호출)
        log_entry["message"] = (
            record.getMessage()
            if not isinstance(record.msg, (dict, list))
            else record.msg
        )

        # LogContext 처리
        log_context_data = None
        if hasattr(record, "log_context") and isinstance(
            record.log_context, LogContext
        ):
            try:
                # Pydantic v2 호환
                log_context_data = record.log_context.model_dump(
                    mode="json", exclude_none=True
                )
                log_entry.update(log_context_data)
            except Exception as e:
                log_entry["log_context_serialization_error"] = repr(e)

        # 추가 데이터 (extra) 처리
        standard_attrs = list(logging.LogRecord.__dict__.keys()) + [
            "message",
            "asctime",
            "relativeCreated",
            "log_context",
            "args",  # args는 getMessage()에서 사용되므로 제외
        ]
        extra_data = {}
        for k, v in record.__dict__.items():
            is_standard = k in standard_attrs
            is_internal = k.startswith("_")
            is_from_log_context = log_context_data and k in log_context_data
            # 표준 속성, 내부 속성, LogContext에서 이미 처리된 속성이 아니면 extra로 간주
            if not is_standard and not is_internal and not is_from_log_context:
                extra_data[k] = v
        if extra_data:
            # extra 데이터는 안전하게 직렬화
            log_entry["extra_data"] = {
                k: safe_serialize(v) for k, v in extra_data.items()
            }

        # 예외 정보 처리
        if record.exc_info:
            # formatException은 None이 아닌 exc_info 튜플을 기대합니다.
            traceback_str = self.formatException(record.exc_info)
            exc_type, exc_value, _ = (
                record.exc_info
            )  # Keep original extraction for type/message
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                "traceback": traceback_str,  # 항상 트레이스백 추가
            }
        elif record.exc_text:  # exc_info가 없을 때 exc_text 사용
            log_entry["exception_text"] = record.exc_text
        if record.stack_info:  # 스택 정보가 있으면 추가
            log_entry["stack_info"] = record.stack_info

        # 최종 JSON 직렬화
        try:
            return json.dumps(log_entry, default=safe_serialize, ensure_ascii=False)
        except Exception as e:
            # 직렬화 실패 시 오류 정보 포함하여 다시 시도 (repr 사용)
            log_entry["json_serialization_error"] = repr(e)
            # repr을 기본값으로 사용하여 최대한 로그 남기기
            return json.dumps(log_entry, default=repr, ensure_ascii=False)
