import asyncio
from typing import AsyncIterator


class Timer:
    def __init__(self, seconds: int):
        self._seconds = seconds
        self._cancel_event = asyncio.Event()

    async def start(self) -> AsyncIterator[int]:
        for i in range(self._seconds, 0, -1):
            if self._cancel_event.is_set():
                break
            yield i
            await asyncio.sleep(1)

    def stop(self) -> None:
        self._cancel_event.set()
