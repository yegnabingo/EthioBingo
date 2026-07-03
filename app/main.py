from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pick & Win V3",
    version="3.0.0"
)

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
