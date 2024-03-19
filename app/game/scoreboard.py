from dataclasses import dataclass
from typing import Optional


@dataclass
class UserScore:
    games_count: int = 0
    wins_count: int = 0


class UsersScoreboard:
    def __init__(self):
        self.scores: dict[str, UserScore] = {}

    def get_or_create(self, username: str) -> UserScore:
        if username not in self.scores:
            self.scores[username] = UserScore(games_count=0, wins_count=0)
        return self.scores[username]

    def increase_games_count(self, username: str) -> None:
        current_score = self.get_or_create(username)
        current_score.games_count += 1

    def increase_wins_count(self, username: str) -> None:
        current_score = self.get_or_create(username)
        current_score.wins_count += 1

    def get_or_none(self, username: str) -> Optional[UserScore]:
        if username in self.scores:
            return self.scores[username]
        return None
