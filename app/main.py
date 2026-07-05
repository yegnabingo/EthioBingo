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
    ይህ ፈንክሽን በየ 30 ሰከንዱ አዲስ ዙር እየጀመረ፣ 
    ሰዓቱ ሲያልቅ ለሁሉም ተጫዋች በዌብሶኬት (manager) እጣዎችን የሚጥል ዋናው ሞተር ነው!
    """
    import random
    while True:
        # --- ሀ. PICK PHASE (30 ሰከንድ መቁጠሪያ) ---
        for seconds_left in range(30, -1, -1):
            await manager.broadcast({
                "type": "time_update",
                "time": seconds_left,
                "phase": "PICK"
            })
            await asyncio.sleep(1)
        
        # --- ለ. DRAW PHASE (30 ሰከንዱ ሲያልቅ በራሱ በቀጥታ) ---
        await manager.broadcast({
            "type": "phase_change",
            "phase": "DRAW"
        })
        
        # 1-75 ቁጥሮችን በዘፈቀደ ማደባለቅ
        bingo_balls = list(range(1, 76))
        random.shuffle(bingo_balls)
        
        call_count = 0
        for ball in bingo_balls:
            call_count += 1
            # ኳሱን ለሁሉም በዌብሶኬት በ2 ሰከንድ ልዩነት መላክ
            await manager.broadcast({
                "type": "ball",
                "number": ball,
                "call_count": call_count
            })
            
            # TODO: እዚህ ጋ `check_winner()` ፈንክሽን በመጨመር አሸናፊ ካለ ሉፑን ሰብሮ (break) መውጣት ይቻላል።
            
            await asyncio.sleep(2) # ⚡️ ልክ ባልከው ህግ መሰረት በ2 ሰከንድ ልዩነት ይጠራሉ
            
        # ዙሩ ሲያልቅ ለ5 ሰከንድ አርፎ እንደገና ወደ 30 ሰከንድ Pick Phase ይመለሳል
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
