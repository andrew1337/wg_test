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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.manager = ConnectionManager(
        q=MatchmakingQueue(blacklist=UsersBlacklist()),
        room_capacity=ROOM_CAPACITY,
        scoreboard=UsersScoreboard(),
    )
    asyncio.create_task(app.manager.handle_matchmaking())
    asyncio.create_task(app.manager.keep_connections_active())
    asyncio.create_task(app.manager.update_user_score())
    yield


app = FastAPI(lifespan=lifespan)


@lru_cache
def get_index():
    with open("static/index.html", "r") as f:
        return f.read()


@app.get("/")
async def get():
    return HTMLResponse(get_index())


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
            is_about_blacklist = mgr.handle_blacklist(player_name, data)
            if is_about_blacklist:
                await websocket.send_json(
                    {
                        "blacklist": "done",
                        "players": list(mgr.q.blacklist.blacklist[player_name]),
                    }
                )
                continue
            current_room = mgr.get_room_or_none(player_name)
            if not current_room:
                continue
            await current_room.handle_connection(websocket, message=data)
    except WebSocketDisconnect:
        mgr.disconnect(player_name)
