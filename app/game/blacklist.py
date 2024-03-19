from collections import defaultdict


class UsersBlacklist:
    def __init__(self):
        self.blacklist: dict[str, set] = defaultdict(set)

    def ban(self, username: str, banned_username: str):
        self.blacklist[username].add(banned_username)
        self.blacklist[banned_username].add(username)

    def is_banned(self, who, whom) -> bool:
        return whom in self.blacklist[who]
