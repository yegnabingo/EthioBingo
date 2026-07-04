from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Game

router = APIRouter(
    prefix="/api/games",
    tags=["Games"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/current")
def current_game(db: Session = Depends(get_db)):

    game = (
        db.query(Game)
        .order_by(Game.id.desc())
        .first()
    )

    if not game:
        return {
            "success": False,
            "message": "No active game"
        }

    return {
        "success": True,
        "game_id": game.id,
        "game_no": game.game_no,
        "status": game.status,
        "ticket_price": game.ticket_price,
        "total_players": game.total_players,
        "total_pool": game.total_pool
    }
