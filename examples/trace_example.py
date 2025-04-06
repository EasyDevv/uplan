"""Example usage of the @trace decorator and class tracing from uplan.utils.logging.logging_trace."""

import asyncio
import time
import logging

from uplan.utils.logging.logging_trace import get_logger, trace

logger = get_logger()


@trace
def example_sync_function(a: int, b: int = 2) -> int:
    logger.info("Inside example_sync_function")
    time.sleep(0.1)
    if a > 5:
        inner_sync_function(a * 2)
    return a + b


@trace(level=logging.INFO)
def inner_sync_function(x: int) -> float:
    logger.info(f"Inside inner_sync_function with x={x}")
    time.sleep(0.05)
    if x > 15:
        raise ValueError("Value too large in inner function")
    return x / 2


@trace
async def example_async_function(name: str) -> str:
    logger.info(f"Inside example_async_function for {name}")
    await asyncio.sleep(0.1)
    result = await inner_async_function(len(name))
    return f"Result for {name}: {result}"


@trace
async def inner_async_function(length: int) -> int:
    logger.info(f"Inside inner_async_function with length={length}")
    await asyncio.sleep(0.05)
    if length < 3:
        await asyncio.sleep(0.02)
        # pass
    elif length == 3:
        raise TypeError("Length cannot be 3")
    return length * 10


@trace(include_init=True, exclude_methods=["private_method"])
class MyClass:
    def __init__(self, value: int) -> None:
        self.value = value
        logger.debug(f"MyClass instance created with value: {self.value}")
        time.sleep(0.02)

    def public_method(self, multiplier: int) -> int:
        logger.info("Executing public_method")
        time.sleep(0.05)
        result = self._helper_method(self.value * multiplier)
        return result

    def _helper_method(self, data: int) -> int:
        logger.debug(f"Executing _helper_method with data: {data}")
        time.sleep(0.03)
        return data + 1

    def private_method(self) -> str:
        # This method should NOT be traced
        logger.info("Executing private_method - SHOULD NOT BE TRACED")
        return "private"

    async def async_method(self, delay: float) -> str:
        logger.info(f"Executing async_method with delay: {delay}")
        await asyncio.sleep(delay)
        if delay > 0.1:
            raise asyncio.TimeoutError("Async delay too long")
        return f"Async completed after {delay}s"


async def main() -> None:
    logger.info("Starting sync examples...")
    example_sync_function(3)
    try:
        example_sync_function(7)
    except ValueError as e:
        logger.warning(f"Caught expected ValueError: {e}")

    logger.info("\nStarting async examples...")
    await example_async_function("Test")
    try:
        await example_async_function("Abc")
    except TypeError as e:
        logger.warning(f"Caught expected TypeError: {e}")

    logger.info("\nStarting class examples...")
    instance = MyClass(value=10)
    instance.public_method(multiplier=3)
    instance.private_method()
    await instance.async_method(0.05)
    try:
        await instance.async_method(0.15)
    except asyncio.TimeoutError as e:
        logger.warning(f"Caught expected TimeoutError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
