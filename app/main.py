import os
import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from telebot import types

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)

if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

import app.models as models
from app.database import engine as db_engine, Base
from app.websocket_manager import manager
from app.game_engine import engine as bingo_engine
from app.telegram import bot
from app.init_db import initialize_database

# 🟢 Synchronous የዳታቤዝ Migration እና Table ፍጠራን በበስተጀርባ የሚያከናውን Function
def setup_database_sync():
    try:
        # Tables መፍጠር
        Base.metadata.create_all(bind=db_engine)
        
        # Initial data ማስገባት
        initialize_database()

        # Columns Auto-migration
        with db_engine.connect() as conn:
            conn.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS winners_info TEXT DEFAULT '[]';"))
            conn.execute(text("ALTER TABLE player_cards ADD COLUMN IF NOT EXISTS card_data TEXT;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS gift_coin FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_games_played INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_deposit_amount FLOAT DEFAULT 0.0;"))
            conn.commit()
            
        print("✅ Database Initialization & Migration Complete.")
    except Exception as e:
        print("❌ Database Error:", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("🎯 Pick & Win V3 Startup (Webhook Mode)")
    print("=" * 50)
    
    # 1. የዳታቤዝ ስራዎችን በ Thread execution (to_thread) በማስኬድ Event Loop እንዳይዘጋ ማድረግ
    await asyncio.to_thread(setup_database_sync)

    # 2. የ game_engine ን በ Background Task ማስጀመር
    game_task = asyncio.create_task(bingo_engine.start_game())

    # 3. FastAPI ፖርቱን ከፍቶ ዝግጁ እንዲሆን Yield ማድረግ
    yield

    bingo_engine.running = False
    game_task.cancel()
    print("🛑 Server Stopped")

app = FastAPI(title="Pick & Win V3", version="3.0.0", lifespan=lifespan)

# 🌐 CORS Middleware መጨመር (Port Scanning እንዳይታገድ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔗 Telegram Webhook Endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        json_str = await request.body()
        update = types.Update.de_json(json_str.decode("utf-8"))
        bot.process_new_updates([update])
        return Response(status_code=200)
    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        return Response(status_code=500)

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

# 🔗 ALL ROUTERS (Sports Betting Router ጨምሮ)
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
    if os.path.exists(os.path.join(STATIC2, "index.html")):
        return FileResponse(os.path.join(STATIC2, "index.html"))
    return {"status": "ok", "message": "Pick & Win V3 API is live"}

@app.get("/health")
async def health():
    return {"status": "OK", "game_engine_running": bingo_engine.running}

# 🚀 Render Deployment Port Fix
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
