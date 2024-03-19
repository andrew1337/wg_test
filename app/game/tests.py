import unittest
from unittest.mock import AsyncMock, MagicMock

from websockets import WebSocketServerProtocol

from game.blacklist import UsersBlacklist
from game.core import Game, GameResult, Move
from game.game_room import GameRoom
from game.matchmaking import MatchmakingQueue
from game.my_timer import Timer
from game.scoreboard import UsersScoreboard


class TestGame(unittest.TestCase):
    def setUp(self):
        self.game = Game(["Player1", "Player2"])

    def test_init(self):
        self.assertEqual(len(self.game.players), 2)

    def test_handle_choice(self):
        self.assertEqual(Move.ROCK, self.game.handle_choice("Player1", Move.ROCK))
        self.assertEqual(len(self.game.choices), 1)
        self.assertEqual(Move.PAPER, self.game.handle_choice("Player2", Move.PAPER))
        self.assertEqual(len(self.game.choices), 2)

    def test_is_all_players_made_a_move(self):
        self.assertFalse(self.game.is_all_players_made_a_move())
        self.game.handle_choice("Player1", Move.ROCK)
        self.assertFalse(self.game.is_all_players_made_a_move())
        self.game.handle_choice("Player2", Move.PAPER)
        self.assertTrue(self.game.is_all_players_made_a_move())

    def test_determine_winners(self):
        self.game.handle_choice("Player1", Move.ROCK)
        self.game.handle_choice("Player2", Move.SCISSORS)
        self.assertEqual(self.game.determine_winners(), GameResult.WIN)

    def test_determine_winners_tie(self):
        self.game.handle_choice("Player1", Move.ROCK)
        self.game.handle_choice("Player2", Move.ROCK)
        self.assertEqual(self.game.determine_winners(), GameResult.TIE)

    def test_determine_winners_disconnected_player(self):
        self.game.handle_choice("Player1", Move.ROCK)
        self.game.disconnected.add("Player2")
        self.assertEqual(self.game.determine_winners(), GameResult.WIN)

    def test_calculate_lucky_move(self):
        moves = [Move.ROCK, Move.PAPER, Move.SCISSORS]
        self.assertIsNone(Game._calculate_lucky_move(moves))

        moves = [Move.ROCK, Move.SCISSORS]
        self.assertEqual(Game._calculate_lucky_move(moves), Move.ROCK)

        moves = [Move.PAPER, Move.SCISSORS]
        self.assertEqual(Game._calculate_lucky_move(moves), Move.SCISSORS)

        moves = [Move.PAPER, Move.PAPER]
        self.assertIsNone(Game._calculate_lucky_move(moves))

        moves = [Move.ROCK, Move.ROCK, Move.SCISSORS, Move.SCISSORS]
        self.assertEqual(Game._calculate_lucky_move(moves), Move.ROCK)


class TestGameRoom(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.room = GameRoom(capacity=2, scoreboard=UsersScoreboard())
        print(f"asdfasdfa {self.room=}")
        self.ws1 = MagicMock(spec=WebSocketServerProtocol)
        self.ws1.send_json = AsyncMock()
        self.ws2 = MagicMock(spec=WebSocketServerProtocol)
        self.ws2.send_json = AsyncMock()

    # async def test_add_player(self):
    #     await self.room.add_player("Player1", self.ws1)
    #     self.assertEqual(len(self.room.players), 1)
    #     self.assertIn(self.ws1, self.room.players.values())
    #     self.assertIn("Player1", self.room.players.keys())

    #     await self.room.add_player("Player2", self.ws2)
    #     self.assertEqual(len(self.room.players), 2)
    #     self.assertIn(self.ws2, self.room.players.values())
    #     self.assertIn("Player2", self.room.players.keys())

    #     self.assertIsNotNone(self.room.game)
    #     self.assertIsNotNone(self.room.timer)

    async def test_handle_choice(self):
        await self.room.add_player("Player1", self.ws1)
        self.room.game.handle_choice = MagicMock(return_value=True)
        await self.room.handle_message(self.ws1, {"choice": Move.ROCK.value})
        self.room.game.handle_choice.assert_called_once_with(
            player="Player1", choice=Move.ROCK
        )

#     async def test_handle_disconnection(self):
#         await self.room.add_player("Player1", self.ws1)
#         await self.room.add_player("Player2", self.ws2)
#         # await self.room.start_game()
#         # Disconnecting a player
#         await self.room.handle_disconnection(self.ws1)
#         # Asserting that the disconnected player is added to the game's disconnected set
#         self.assertIn("Player1", self.room.game.disconnected)


class TestMatchmakingQueue(unittest.IsolatedAsyncioTestCase):
    async def test_add_remove(self):
        matchmaking_queue = MatchmakingQueue(blacklist=UsersBlacklist())
        await matchmaking_queue.add(1)
        await matchmaking_queue.add(2)
        await matchmaking_queue.add(3)
        await matchmaking_queue.remove(2)
        match = await matchmaking_queue.get_match(2)
        self.assertEqual(sorted(match), [1, 3])

    async def test_get_match(self):
        matchmaking_queue = MatchmakingQueue(blacklist=UsersBlacklist())
        await matchmaking_queue.add(1)
        await matchmaking_queue.add(2)
        match = await matchmaking_queue.get_match(2)
        self.assertEqual(match, [1, 2])


class TestTimer(unittest.IsolatedAsyncioTestCase):
    async def test_run(self):
        """
        Test that Timer.start() correctly generates a sequence of numbers.
        """
        timer = Timer(5)
        task = timer.start()
        results = []
        async for i in task:
            results.append(i)
        self.assertEqual(list(range(5, 0, -1)), list(results))

    async def test_run_with_stop(self):
        timer = Timer(5)
        task = timer.start()

        results = []
        async for i in task:
            results.append(i)
            if i == 3:
                timer.stop()  # Stop early for testing

        self.assertEqual(results, [5, 4, 3])


if __name__ == "__main__":
    unittest.main()
