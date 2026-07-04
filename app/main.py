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

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {
        "app": "Pick & Win V3",
        "status": "Running"
    }


@app.get("/health")
async def health():
    return {
        "status": "OK"
    }
