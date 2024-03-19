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

class GameState(Enum): # todo: move staet here adn to refacror
    timer: Optional[Timer]
    is_ended: asyncio.Event
    result: Optional[GameResult]

class GameRoom:
    def __init__(self, capacity: int, scoreboard: UsersScoreboard):
        self.players: Dict[str, WebSocketServerProtocol] = {}
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
        self.game_result: Optional[GameResult] = None
        self.scoreboard: UsersScoreboard = scoreboard

    def _get_player_by_ws(self, ws: WebSocketServerProtocol) -> Optional[str]:
        for player, w in self.players.items():
            if w == ws:
                return player
        return None

    async def add_player(self, player_name: str, ws: WebSocketServerProtocol):
        self.players[player_name] = ws
        await self.notify_all({"ping": f"Player {player_name} joined the game."})
        if len(self.players) == self.capacity:
            await self.start_game()

    async def start_game(self):
        if len(self.players) != self.capacity:
            print("Problem with start_game()")
        self.game_is_ended.clear()
        self.game_result = None
        players_names = list(self.players.keys())
        self.game = self.game_class(players_names)

        await self.notify_all({"game_state": "start", "players": players_names})
        await self.start_timer()
        await asyncio.sleep(0.5)

    async def _last_tick(self):
        await asyncio.sleep(1)
        self.game_is_ended.set()
        self.timer.stop()
        self.game_result = self.game.stop_game()
        await self.notify_all({"game_state": "countdown", "countdown": 0})
        await self.notify_all({"game_state": "stop", "stop": "countdown"})
        await self.notify_results()

    async def start_timer(self):
        self.timer = self.timer_class(self.timer_inintial_seconds)
        async for remaining_time in self.timer.start():
            if self.game.is_all_players_made_a_move() or self.game_is_ended.is_set():
                self.game_is_ended.set()
                self.timer.stop()
                break
            await self.notify_all(
                {"game_state": "countdown", "countdown": remaining_time, "players": list(self.players.keys())}
            )
            if remaining_time == 1:
                await self._last_tick()

    async def handle_connection(self, ws: WebSocketServerProtocol, message: str):
        try:
            await self.handle_message(ws, message)
        except ConnectionClosed:
            self.handle_disconnection(ws)
            raise

    async def do_restart(self):
        draw_timer = self.timer_class(3)
        async for i in draw_timer.start():
            await self.notify_all(
                {
                    "game_state": "result",
                    "result": PlayerResult.DRAW.name,
                    "restart_seconds_remaining": i,
                }
            )
        await self.start_game()

    async def handle_message(self, ws: WebSocketServerProtocol, message: dict):
        choice_str = message.get("choice", None)
        if choice_str:
            await self.handle_choice(ws, choice_str)
        if self.game.is_all_players_made_a_move():
            self.game_is_ended.set()
            self.timer.stop()
            self.game_result = self.game.stop_game()
            await self.notify_all(
                {"game_state": "stop", "stop": "all_players_made_a_move"}
            )
            await self.notify_results()

    async def handle_choice(self, ws: WebSocketServerProtocol, msg: str):
        try:
            move = Move(msg.strip().lower())
            is_accepted = self.game.handle_choice(
                player=self._get_player_by_ws(ws), choice=move
            )
            await ws.send_json({"ping": f"Choice made: {is_accepted}"})
        except ValueError:
            await ws.send_json({"ping": f"Invalid choice {msg=}"})

    def handle_disconnection(self, ws: WebSocketServerProtocol):
        player = self._get_player_by_ws(ws)
        print(f"disconnected: {player=}")
        self.game.disconnected.add(player)

    async def notify_results(self):
        if self.game_result == GameResult.TIE:
            await self.notify_all(
                {"game_state": "result", "result": PlayerResult.DRAW.name}
            )
            # await self.do_restart()
            return
        for player, ws in self.players.items():
            await ws.send_json(
                {
                    "game_state": "result",
                    "result": (
                        PlayerResult.WIN.name
                        if player in self.game.result.winners
                        else PlayerResult.LOSE.name
                    ),
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
                print(f"Skip sending message to removed {ws=}")
