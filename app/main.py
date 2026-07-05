import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

# የድሮዎቹ አስመጪዎች (Imports) እንዳሉ ቀጥለዋል
from app.websocket_manager import manager
from app.database import Base, engine as db_engine
from app.init_db import initialize_database

# የራውተሮች አስመጪዎች
from app.routes.cards import router as cards_router
from app.routes.users import router as users_router
from app.routes.deposit import router as deposit_router
from app.routes.admin import router as admin_router
from app.routes.withdraw import router as withdraw_router
from app.routes.games import router as games_router

# 1. የዳታቤዝ ቴብሎችን መፍጠር
Base.metadata.create_all(bind=db_engine)

# 2. የ Lifespan መቆጣጠሪያ (አፑ ሲጀምር ዳታቤዝ እንዲያዘጋጅ)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 40)
    print(" 🎯 Pick & Win V3 Starting...")
    print("=" * 40)
    
    # የዳታቤዝ መረጃዎችን መነሻ ማድረግ (Initialize)
    try:
        initialize_database()
        print("✅ Database Initialization Complete.")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")
        
    yield
    print("🛑 Server Stopped")

app = FastAPI(
    title="Pick & Win V3",
    version="3.0.0",
    lifespan=lifespan
)

# 3. 📡 ዌብሶኬት ማገናኛ (የቀድሞውን manager ይጠቀማል)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # ከፊት ገጽ (Frontend) የሚመጣ መልዕክት ካለ ለመቀበል
            await websocket.receive_text()
    except Exception as e:
        print(f"Websocket disconnected: {e}")
    finally:
        manager.disconnect(websocket)

# 4. 🔄 የጨዋታውን ሉፕ (Game Loop) በጀርባ ማስጀመር
@app.on_event("startup")
async def startup_event():
    # ማሳሰቢያ፡ እዚህ ላይ የድሮው ኮድ `engine.start_game()` ይል ነበር። 
    # ነገር ግን `engine` የ SQLAlchemy Database Engine ስለሆነ የጨዋታ ሉፕ መያዝ አይችልም።
    # የጨዋታውን አውቶማቲክ ሉፕ (30s -> Draw) በጀርባ እንዲያሽከረክር Background Task እንሰጠዋለን።
    asyncio.create_task(run_automated_game_loop())

async def run_automated_game_loop():
    """
    በየ 30 ሰከንዱ ዙር እየቀያየረ የዳታቤዙን ሁኔታ 'running' የሚያደርግ 
    እና እጣዎችን የሚጥለው ዋናው ሞተር
    """
    import random
    from app.database import SessionLocal
    from app.models import Game # የጨዋታ ሞዴልህን ያመጣል

    while True:
        db = SessionLocal()
        try:
            # 1. በዳታቤዝ ውስጥ አዲስ የነቃ ጨዋታ መፍጠር ወይም ያለውን 'running' ማድረግ
            active_game = db.query(Game).filter(Game.status == "running").first()
            if not active_game:
                active_game = Game(status="running")
                db.add(active_game)
                db.commit()
                db.refresh(active_game)
        except Exception as e:
            print(f"Database game session error: {e}")
        finally:
            db.close()

        # --- ሀ. PICK PHASE (30 ሰከንድ መቁጠሪያ) ---
        for seconds_left in range(30, -1, -1):
            await manager.broadcast({
                "type": "time_update",
                "time": seconds_left,
                "phase": "PICK"
            })
            await asyncio.sleep(1)
        
        # --- ለ. DRAW PHASE (በቀጥታ ይጀምራል) ---
        await manager.broadcast({
            "type": "phase_change",
            "phase": "DRAW"
        })
        
        bingo_balls = list(range(1, 76))
        random.shuffle(bingo_balls)
        
        call_count = 0
        for ball in bingo_balls:
            call_count += 1
            await manager.broadcast({
                "type": "ball",
                "number": ball,
                "call_count": call_count
            })
            
            # TODO: እዚህ ጋ የዊነር ቼክ መጨመር ይቻላል
            await asyncio.sleep(2) # በ2 ሰከንድ ልዩነት ጥሪ
            
        # ዙሩ ሲያልቅ ጨዋታውን በዳታቤዝ አጠናቅቆ ለቀጣዩ ማዘጋጀት
        db = SessionLocal()
        try:
            active_game = db.query(Game).filter(Game.status == "running").first()
            if active_game:
                active_game.status = "finished"
                db.commit()
        finally:
            db.close()

        await asyncio.sleep(5)


# 5. ሁሉንም የኤፒአይ መንገዶች (Routers) ማገናኘት
app.include_router(cards_router)
app.include_router(users_router)
app.include_router(deposit_router)
app.include_router(admin_router)
app.include_router(withdraw_router)
app.include_router(games_router)

# 6. Static ፋይሎች (HTML, CSS, JS) ማሳያ
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"status": "OK"}
