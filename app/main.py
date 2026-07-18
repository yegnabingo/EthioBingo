import os
import sys
import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)

if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from app.database import Base, engine as db_engine
from app.init_db import initialize_database
from app.websocket_manager import manager
from app.game_engine import engine as bingo_engine
from app.telegram import bot


Base.metadata.create_all(bind=db_engine)


def start_bot():
    print("🤖 Telegram Bot Started")

    while True:
        try:
            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=30
            )
        except Exception as e:
            print(f"❌ Telegram Bot Error: {e}")
            import time
            time.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("🎯 Pick & Win V3 Startup")
    print("=" * 50)

    try:
        initialize_database()
        print("✅ Database Initialization Complete.")
    except Exception as e:
        print("Database Error:", e)

    game_task = asyncio.create_task(
        bingo_engine.start_game()
    )

    bot_thread = threading.Thread(
        target=start_bot,
        daemon=True
    )
    bot_thread.start()

    yield

    bingo_engine.running = False
    game_task.cancel()

    print("🛑 Server Stopped")


app = FastAPI(
    title="Pick & Win V3",
    version="3.0.0",
    lifespan=lifespan
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)


from app.routes.cards import router as cards_router
from app.routes.users import router as users_router
from app.routes.games import router as games_router

app.include_router(cards_router)
app.include_router(users_router)
app.include_router(games_router)


STATIC1 = os.path.join(CURRENT_DIR, "../static")
STATIC2 = os.path.join(CURRENT_DIR, "static")

if os.path.exists(STATIC1):
    app.mount("/static", StaticFiles(directory=STATIC1), name="static")
elif os.path.exists(STATIC2):
    app.mount("/static", StaticFiles(directory=STATIC2), name="static")


@app.get("/")
async def root():
    if os.path.exists(os.path.join(STATIC1, "index.html")):
        return FileResponse(os.path.join(STATIC1, "index.html"))

    return FileResponse(os.path.join(STATIC2, "index.html"))


@app.get("/health")
async def health():
    return {
        "status": "OK",
        "game_engine_running": bingo_engine.running
    }
