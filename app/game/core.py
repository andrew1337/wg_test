from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Set


class Move(Enum):
    ROCK = "r"
    PAPER = "p"
    SCISSORS = "s"


class GameResult(Enum):
    WIN = auto()
    TIE = auto()


@dataclass
class ResultTable:
    winners: Set
    losers: Set


WIN_COMBINATIONS = {
    Move.ROCK: Move.SCISSORS,
    Move.PAPER: Move.ROCK,
    Move.SCISSORS: Move.PAPER,
}


class Game:
    def __init__(self, players: List[str]):
        if len(players) < 2:
            raise ValueError("Game needs at least 2 players")
        self.players = set(players)
        self.disconnected: Set[str] = set()
        self.choices: dict[str, Move] = {}
        self.result: ResultTable = ResultTable(winners=set(), losers=set())

    def is_all_connected_players_are_made_a_move(self) -> bool:
        return len(self.choices) == len(self.players) - len(self.disconnected)

    def do_move(self, player: str, choice: Move) -> Optional[Move]:
        if choice not in Move.__members__.values():
            raise ValueError("Invalid choice. Choose R, P, or S.")
        if player in self.choices:
            return None
        self.choices[player] = choice
        return choice

    def stop_game(self) -> GameResult:
        return self.determine_winners()

    def determine_winners(self) -> GameResult:
        lucky_move = self._calculate_lucky_move(list(self.choices.values()))
        if not lucky_move and len(self.choices) == len(self.players):
            return GameResult.TIE
        winners = [
            player
            for player, choice in self.choices.items()
            if choice == lucky_move and player not in self.disconnected
        ]
        self.result.winners.update(winners)
        self.result.losers.update(self.players - set(winners))
        return GameResult.WIN

    @staticmethod
    def _calculate_lucky_move(moves: List[Move]) -> Optional[Move]:
        if len(moves) == 1:
            return moves[0]
        unique_moves = set(moves)
        if len(unique_moves) == 2:
            first, second = unique_moves
            return first if WIN_COMBINATIONS[first] == second else second
        return None
