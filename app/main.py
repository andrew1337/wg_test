import asyncio
import os
from contextlib import asynccontextmanager
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from game.blacklist import UsersBlacklist
from game.game_queue import MatchmakingQueue
from game.matchmaking import ConnectionManager
from game.scoreboard import UsersScoreboard

load_dotenv()

ROOM_CAPACITY = int(os.getenv("ROOM_CAPACITY", 2))


@lru_cache
def read_file(f):
    with open(f, "r") as file:
        return file.read()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.manager = ConnectionManager(
        q=MatchmakingQueue(blacklist=UsersBlacklist()),
        room_capacity=ROOM_CAPACITY,
        scoreboard=UsersScoreboard(),
    )
    asyncio.create_task(app.manager.handle_matchmaking())
    asyncio.create_task(
        app.manager.keep_connections_active(
            read_file("static/still_alive.txt").split("\n")
        )
    )
    asyncio.create_task(app.manager.update_user_score())
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def get():
    return HTMLResponse(read_file("static/index.html"))


@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str):
    mgr: ConnectionManager = app.manager
    await mgr.connect(websocket, player_name)
    try:
        while True:
            data = await websocket.receive_json()
            print(f"handle_websocket {data=}", player_name, data)
            if data is None:
                continue
            if mgr.handle_blacklist(player_name, data):
                continue
            current_room = mgr.get_room_or_none(player_name)
            if not current_room:
                continue
            await current_room.user_interactions.handle_connection(
                websocket, message=data
            )
    except WebSocketDisconnect:
        mgr.disconnect(player_name)
