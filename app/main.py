from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
from app.database import Base, engine
from app.init_db import initialize_database

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

initialize_database()

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
