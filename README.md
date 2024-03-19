# Rock Paper Scissors

## Usage
```bash
cd app
```

Run
```bash
uvicorn main:app --reload --host 0.0.0.0
```

Test
```bash
python -m unittest discover
```

Start using docker
```bash
docker-compose up
```


## User Story

✅ The player opens the page and confirms his readiness to participate in the game round (one open tab - one player);

✅ An opponent is randomly selected from the queue of players for the current one;

✅ After selecting an opponent, the playing field opens, which contains:

	✅ Countdown timer for turn;
	
	✅ Personal account score counter with information about wins and total number of games played;
	
	✅ Action selection button (rock, scissors or paper).

✅ Players must make their choice before the timer runs out;

❔ After players make their choice, the round is announced: 

	❌ In case of a draw, the round is played again;
	
	✅ If one of the players did not make a choice within the allotted time, he is considered a loser;
	
	❔ If both players do not have time to make a choice, their gaming sessions end (they start the game again);
	
	✅ If one player wins, the player counters are updated.

✅ Players would see final screen with win/lose title.

## User Stories Advanced Level

❔ Players are given the opportunity to start the game again after round finish;

✅ The player's personal account should be available after reloading the page;

❔ The ability to end the session early and exit the game before it ends (with auto-loss);

✅ Before starting the session, the player can enter his nickname;

❌ After summing up the round, players are given the opportunity to play a new round with the same opponent;

✅ More than two players can participate in one round (set through the application configuration);

❌ You can view the round history;

✅ Blacklist feature:

	✅ Players can add their opponents to a blacklist while playing;
	
	✅ If a player is on another player's blacklist, they will never be matched together.