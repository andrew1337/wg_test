import asyncio
from dataclasses import dataclass
from json import loads
from typing import Dict, Optional

from fastapi import WebSocket

from .game_queue import MatchmakingQueue
from .game_room import GameRoom
from .scoreboard import UserScore, UsersScoreboard


class UserAreadyInRoom(Exception):
    pass


@dataclass
class UserInfo:
    ws: WebSocket
    room: GameRoom


class ConnectionManager:
    def __init__(
        self, q: MatchmakingQueue, room_capacity: int, scoreboard: UsersScoreboard
    ):
        self.users: Dict[str, UserInfo] = {}
        self.q = q
        self.room_capacity = room_capacity
        self.users_scoreboard = scoreboard

    async def connect(self, websocket: WebSocket, player_name: str):
        self.users[player_name] = UserInfo(ws=websocket, room=None)
        await websocket.accept()
        await self.q.add(player_name)

    def disconnect(self, player_name: str):
        self.users.pop(player_name, None)

    def get_room_or_none(self, player_name) -> Optional[GameRoom]:
        info = self.users.get(player_name, None)
        if not info:
            return None
        return info.room

    async def _add_user_to_room(self, player_name, room: GameRoom):
        current_user = self.users[player_name]
        if current_user.room:
            raise UserAreadyInRoom(f"{player_name=} is already in game")
        current_user.room = room
        await room.add_player(player_name, current_user.ws)

    async def handle_matchmaking(self):
        while True:
            print("handle_matchmaking")
            match = await self.q.get_match(self.room_capacity)
            if not match:
                print("no match found")
                await asyncio.sleep(1)
                continue
            game_room = GameRoom(self.room_capacity, scoreboard=self.users_scoreboard)
            await asyncio.gather(
                *(
                    self._add_user_to_room(player_name, game_room)
                    for player_name in match
                )
            )

    async def keep_connections_active(self):
        while True:
            await asyncio.sleep(5)
            for uinfo in self.users.values():
                try:
                    await uinfo.ws.send_json({"hey, dear client": "please keep alive"})
                except RuntimeError:
                    print("Skip sending message to removed user")

    async def update_user_score(self):
        while True:
            await asyncio.sleep(1)
            for name, info in self.users.items():
                user_score: UserScore = self.users_scoreboard.get_or_none(name)
                if not user_score:
                    continue
                await info.ws.send_json(
                    {
                        "game_state": "score",
                        "score": {
                            "wins": user_score.wins_count,
                            "games": user_score.games_count,
                        },
                    }
                )

    def handle_blacklist(self, user: str, message: dict) -> bool:
        will_ban_him = message.get("block", None)
        if not will_ban_him:
            return False
        self.q.blacklist.ban(username=user, banned_username=will_ban_him)
        return True
