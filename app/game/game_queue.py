import asyncio
from random import randint

from .blacklist import UsersBlacklist


class MatchmakingQueue:
    def __init__(self, blacklist: UsersBlacklist):
        self.blacklist = blacklist
        self.queue = asyncio.Queue()

    async def add(self, player_name):
        await self.queue.put(player_name)

    async def remove(self, player_name):
        tmp_queue = asyncio.Queue()
        while not self.queue.empty():
            item = await self.queue.get()
            if item == player_name:
                break
            await tmp_queue.put(item)
        while not tmp_queue.empty():
            await self.queue.put(await tmp_queue.get())

    def _is_blacklisted_by_somebody(self, match, user) -> bool:
        for i in match:
            if self.blacklist.is_banned(i, user):
                return True
        return False

    async def get_match(self, n: int) -> list:
        match = []
        while len(match) < n:
            item = await self.queue.get()
            if randint(0, 2):
                await self.add(item)
                continue
            if len(match) == 0:
                match.append(item)
                continue
            if self._is_blacklisted_by_somebody(match, item):
                await self.add(item)
                continue
            match.append(item)
        assert len(match) == n
        return match
