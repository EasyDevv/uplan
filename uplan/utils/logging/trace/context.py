import contextvars
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


current_function_context: contextvars.ContextVar[Optional[str]] = (
    contextvars.ContextVar("current_function_context", default=None)
)
call_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "call_depth", default=0
)


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
