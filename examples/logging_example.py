import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Pydantic import
from pydantic import BaseModel, Field

# Refactored logging imports
from uplan.utils.logging import get_logger, trace
from uplan.utils.logging import LOG_DIR


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
        # LOG_DIR은 config에서 가져옵니다.
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
        logger.warning(f"동기 함수에서 예상된 오류 ({type(e).__name__}) 처리 완료.")
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
        logger.warning(f"비동기 함수에서 예상된 오류 ({type(e).__name__}) 처리 완료.")
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
        logger.warning(
            f"클래스 동기 메서드에서 예상된 오류 ({type(e).__name__}) 처리 완료."
        )
    try:
        class_async_result = await processor.process_item_async(5)
        logger.info(f"클래스 비동기 메서드 결과: {class_async_result}")
    except Exception:
        logger.exception("클래스 비동기 메서드 오류 발생")
    try:
        await processor.process_item_async(8)
    except asyncio.TimeoutError as e:
        logger.warning(
            f"클래스 비동기 메서드에서 예상된 오류 ({type(e).__name__}) 처리 완료."
        )
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
        "c": Path("/tmp/data"),  # pathlib.Path 사용
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
        # get_logger()를 사용하여 설정된 로거로 critical 오류 로깅
        logger.critical(f"메인 실행 중 치명적 오류 발생: {e}", exc_info=True)
        sys.exit(1)
