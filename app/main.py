import os
import sys
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# የወላጅ ፎልደርን ወደ sys.path መጨመር (የ app. ፓኬጅ በትክክል እንዲሰራ)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

# 🔄 [ዋናው ማስተካከያ] ሁሉንም ከ 'app.' ቅድመ-ቅጥያ ጋር ወጥ በሆነ መልኩ መጥራት
from app.database import Base, engine as db_engine
from app.init_db import initialize_database
from app.websocket_manager import manager
from app.game_engine import engine as bingo_engine

# የዳታቤዝ ቴብሎችን መፍጠር
Base.metadata.create_all(bind=db_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 40)
    print(" 🎯 Pick & Win V3 Starting...")
    print("=" * 40)
    try:
        initialize_database()
        print("✅ Database Initialization Complete.")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")
        
    # የጌም ኢንጂኑን ማለቂያ የሌለውን ሉፕ በጀርባ (Background) በጋራ መስመር ማስጀመር
    game_loop_task = asyncio.create_task(bingo_engine.start_game())
    yield
    # ሰርቨሩ ሲጠፋ ሉፑን ማቆም
    bingo_engine.running = False
    game_loop_task.cancel()
    print("🛑 Server Stopped")


app = FastAPI(title="Pick & Win V3", version="3.0.0", lifespan=lifespan)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # የደንበኛውን ግንኙነት በህይወት ማቆያ (Keep Alive)
            await websocket.receive_text()
    except Exception as e:
        print(f"Websocket disconnected: {e}")
    finally:
        manager.disconnect(websocket)

# የራውተሮች ማገናኛ (ከ app. ፓኬጅ ጋር)
from app.routes.cards import router as cards_router
from app.routes.users import router as users_router
from app.routes.deposit import router as deposit_router
from app.routes.admin import router as admin_router
from app.routes.withdraw import router as withdraw_router
from app.routes.games import router as games_router

app.include_router(cards_router)
app.include_router(users_router)
app.include_router(deposit_router)
app.include_router(admin_router)
app.include_router(withdraw_router)
app.include_router(games_router)

# የስታቲክ ፋይሎች ማገናኛ
if os.path.exists(os.path.join(CURRENT_DIR, "../static")):
    app.mount("/static", StaticFiles(directory=os.path.join(CURRENT_DIR, "../static")), name="static")
elif os.path.exists(os.path.join(CURRENT_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(CURRENT_DIR, "static")), name="static")

@app.get("/")
async def root(): 
    static_html = os.path.join(CURRENT_DIR, "../static/index.html")
    if os.path.exists(static_html):
        return FileResponse(static_html)
    return FileResponse(os.path.join(CURRENT_DIR, "static/index.html"))

@app.get("/health")
async def health(): 
    return {"status": "OK", "game_engine_running": bingo_engine.running}
