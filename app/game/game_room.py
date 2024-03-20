import asyncio
from enum import Enum, auto
from typing import Dict, Optional

from websockets import ConnectionClosed, WebSocketServerProtocol

from .core import Game, GameResult, Move
from .my_timer import Timer
from .scoreboard import UsersScoreboard


class PlayerResult(Enum):
    WIN = auto()
    LOSE = auto()
    DRAW = auto()


class UserInteractions:
    def __init__(self, game_room: "GameRoom"):
        self.game_room = game_room

    async def handle_connection(self, ws: WebSocketServerProtocol, message: str):
        try:
            await self.handle_message(ws, message)
        except ConnectionClosed:
            self.handle_disconnection(ws)
            raise

    async def handle_message(self, ws: WebSocketServerProtocol, message: dict):
        choice_str = message.get("choice", None)
        player = self.game_room.ws_player_mapping.get(ws, None)
        if choice_str and player:
            self.game_room.handle_choice(player, choice_str)

    def handle_disconnection(self, ws: WebSocketServerProtocol):
        player = self.game_room.ws_player_mapping[ws]
        self.game_room.game.disconnected.add(player)


class GameRoom:
    def __init__(self, capacity: int, scoreboard: UsersScoreboard):
        self.players: Dict[str, WebSocketServerProtocol] = {}
        self.ws_player_mapping: Dict[WebSocketServerProtocol, str] = {}
        if capacity < 2:
            raise ValueError(f"Room capacity should be >= 2, got: {capacity}")
        self.capacity = capacity
        self.players_ready_to_restart = set()
        self.timer_class = Timer
        self.timer_inintial_seconds = 10
        self.timer: Optional[Timer] = None
        self.game_class = Game
        self.game: Optional[Game] = None
        self.game_is_ended = asyncio.Event()
        self.scoreboard: UsersScoreboard = scoreboard
        self.user_interactions = UserInteractions(self)

    def handle_choice(self, player: str, msg: str):
        try:
            move = Move(msg.strip().lower())
        except ValueError:
            return
        is_accepted = self.game.do_move(player=player, choice=move)
        if not is_accepted:
            return
        if self.game.is_all_connected_players_are_made_a_move():
            self.game_is_ended.set()

    async def add_player(self, player_name: str, ws: WebSocketServerProtocol):
        self.players[player_name] = ws
        self.ws_player_mapping[ws] = player_name
        await self.notify_all({"ping": f"Player {player_name} joined the game."})
        if len(self.players) == self.capacity:
            await self.start_game()

    async def start_game(self):
        if len(self.players) < 2:
            raise RuntimeError("Not enough players")
        self.game_is_ended.clear()
        players_names = list(self.players.keys())
        self.game = self.game_class(players_names)
        await self.notify_all({"game_state": "start", "players": players_names})
        await self.start_timer()
        await self.game_is_ended.wait()
        self.timer.stop()
        game_result = self.game.stop_game()
        await self.manage_results(game_result)
        if game_result == GameResult.TIE:
            await self.do_restart()

    async def start_timer(self):
        self.timer = self.timer_class(self.timer_inintial_seconds)
        async for remaining_time in self.timer.start():
            if self.game_is_ended.is_set():
                break
            message = {
                "game_state": "countdown",
                "countdown": remaining_time,
                "players": list(self.players.keys()),
            }
            await self.notify_all(message)
            if remaining_time == 1:
                await self._last_tick()

    async def _last_tick(self):
        await asyncio.sleep(1)
        await self.notify_all({"game_state": "countdown", "countdown": 0})
        self.game_is_ended.set()

    async def do_restart(self):
        restart_timer = self.timer_class(3)
        async for i in restart_timer.start():
            await self.notify_all(
                {
                    "game_state": "result",
                    "result": PlayerResult.DRAW.name,
                    "restart_seconds_remaining": i,
                }
            )
        await self.start_game()

    async def manage_results(self, result: GameResult):
        if result == GameResult.TIE:
            await self.notify_all(
                {"game_state": "result", "result": PlayerResult.DRAW.name}
            )
            return
        for player, ws in self.players.items():
            result = (
                PlayerResult.WIN.name
                if player in self.game.result.winners
                else PlayerResult.LOSE.name
            )
            await ws.send_json(
                {
                    "game_state": "result",
                    "result": result,
                }
            )
        self.write_down_results()

    def write_down_results(self):
        for player in self.game.players:
            self.scoreboard.increase_games_count(player)
            if player in self.game.result.winners:
                self.scoreboard.increase_wins_count(player)

    async def notify_all(self, message):
        for ws in self.players.values():
            try:
                await ws.send_json(message)
            except RuntimeError:
                pass
