import asyncio
from fastapi import WebSocket
from app.websocket_manager import manager
from app.database import Base, engine as db_engine
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.database import Base, engine
from app.init_db import initialize_database
from app.schemas import PickCardRequest, PickCardResponse
from app.card_service import reserve_card
from app.database import SessionLocal
from app.models import User, Game
from fastapi import FastAPI
from app.routes.cards import router as cards_router
from app.routes.users import router as users_router
from app.routes.deposit import router as deposit_router
from app.routes.admin import router as admin_router
from app.routes.withdraw import router as withdraw_router
from app.routes.games import router as games_router
from fastapi.responses import FileResponse

# Create database tables
Base.metadata.create_all(bind=db_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("=" * 40)
    print(" Pick & Win V3 Starting...")
    print("=" * 40)

    yield

    print("Server Stopped")

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

    except:

        manager.disconnect(websocket)

        
initialize_database()
@app.on_event("startup")
async def startup_event():

    asyncio.create_task(engine.start_game())

app.include_router(cards_router)
app.include_router(users_router)
app.include_router(deposit_router)
app.include_router(admin_router)
app.include_router(withdraw_router)
app.include_router(games_router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {
        "status": "OK"
    }
