import asyncio
from fastapi import WebSocket
from app.websocket_manager import manager
from app.game_engine import engine
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.database import Base, engine
from app.init_db import initialize_database
from app.schemas import PickCardRequest, PickCardResponse
from app.card_service import reserve_card
from app.database import SessionLocal
from app.models import User, Game

# Create database tables
Base.metadata.create_all(bind=engine)

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

@app.post("/api/pick", response_model=PickCardResponse)
def pick_card(request: PickCardRequest):

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.telegram_id == request.telegram_id
        ).first()

        if not user:
            return PickCardResponse(
                success=False,
                message="User not found"
            )

        game = db.query(Game).filter(
            Game.status == "running"
        ).first()

        if not game:
            return PickCardResponse(
                success=False,
                message="No active game"
            )

        success, result = reserve_card(
            db=db,
            card_number=request.card_number,
            user_id=user.id,
            game_id=game.id
        )

        if not success:
            return PickCardResponse(
                success=False,
                message=result
            )

        return PickCardResponse(
            success=True,
            message="Card reserved successfully"
        )

    finally:
        db.close()
        
initialize_database()
@app.on_event("startup")
async def startup_event():

    asyncio.create_task(engine.start_game())


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
