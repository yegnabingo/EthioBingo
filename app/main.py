import asyncio
import random
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

# የድሮዎቹ አስመጪዎች (Imports)
from app.websocket_manager import manager
from app.database import Base, engine as db_engine, SessionLocal
from app.init_db import initialize_database
from app.models import Game  # የጨዋታ ሞዴል

# የራውተሮች አስመጪዎች
from app.routes.cards import router as cards_router
from app.routes.users import router as users_router
from app.routes.deposit import router as deposit_router
from app.routes.admin import router as admin_router
from app.routes.withdraw import router as withdraw_router
from app.routes.games import router as games_router

# 1. የዳታቤዝ ቴብሎችን መፍጠር
Base.metadata.create_all(bind=db_engine)


# 2. የ Lifespan መቆጣጠሪያ (አፑ ሲጀምር ሁሉንም ነገር በአንድ ላይ ያስነሳል)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 40)
    print(" 🎯 Pick & Win V3 Starting...")
    print("=" * 40)
    
    # ሀ. የዳታቤዝ መረጃዎችን መነሻ ማድረግ (Initialize)
    try:
        initialize_database()
        print("✅ Database Initialization Complete.")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")
        
    # ለ. የጨዋታውን አውቶማቲክ ሉፕ (Background Task) እዚሁ ውስጥ ማስነሳት
    game_loop_task = asyncio.create_task(run_automated_game_loop())
    
    yield
    
    # አፑ ሲጠፋ የጀርባ ስራውን ማቆም
    game_loop_task.cancel()
    print("🛑 Server Stopped")


app = FastAPI(
    title="Pick & Win V3",
    version="3.0.0",
    lifespan=lifespan
)


# 3. 📡 ዌብሶኬት ማገናኛ
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f"Websocket disconnected: {e}")
    finally:
        manager.disconnect(websocket)


# 4. 🔄 የተስተካከለው የጨዋታ ሉፕ ሞተር (Game Loop Motor)
async def run_automated_game_loop():
    """
    በየ 30 ሰከንዱ ዙር እየቀያየረ የዳታቤዙን ሁኔታ 'running' የሚያደርግ 
    እና እጣዎችን የሚጥለው ዋናው ሞተር (ከዳታቤዝ ሞዴል ጋር የተስማማ)
    """
    print("🎯 የቢንጎ ሰዓት መቁጠሪያ ሞተር በጀርባ ስራ ጀምሯል...")
    
    while True:
        db = SessionLocal()
        current_game_id = None
        
        try:
            # 1. በዳታቤዝ ውስጥ አዲስ የነቃ ጨዋታ መፍጠር ወይም ያለውን 'running' ማድረግ
            active_game = db.query(Game).filter(Game.status == "running").first()
            if not active_game:
                # 💡 [ማስተካከያ] በሞዴልህ ላይ የሌሉትን fields አስወግደን በህጉ መሰረት ብቻ መፍጠር
                active_game = Game(
                    status="running",
                    started_at=datetime.utcnow()
                )
                db.add(active_game)
                db.commit()
                db.refresh(active_game)
            
            current_game_id = active_game.id
        except Exception as e:
            print(f"❌ Database game session error: {e}")
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
        
        # 1-75 ኳሶችን በዘፈቀደ ማዘጋጀት
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
            
            # ጨዋታው በጣም እንዳይረዝም በ35ኛው ኳስ ላይ እንዲያበቃ ማድረግ 
            if call_count >= 35:
                break
                
            await asyncio.sleep(2)  # በ2 ሰከንድ ልዩነት ቀጣይ ኳስ መጣል
            
        # ዙሩ ሲያልቅ ጨዋታውን በዳታቤዝ 'finished' ማድረግ
        if current_game_id:
            db = SessionLocal()
            try:
                game_to_close = db.query(Game).filter(Game.id == current_game_id).first()
                if game_to_close:
                    game_to_close.status = "finished"
                    game_to_close.finished_at = datetime.utcnow()
                    db.commit()
                    print(f"🏁 Game ID {current_game_id} ተጠናቆ በዳታቤዝ ተዘግቷል።")
            except Exception as e:
                print(f"❌ Error closing game: {e}")
            finally:
                db.close()

        # ለቀጣዩ ዙር ተጫዋቾች እንዲዘጋጁ 5 ሰከንድ እረፍት መስጠት
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
