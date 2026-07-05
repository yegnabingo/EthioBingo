import random
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
    # 1. የመጨረሻውን ጨዋታ መፈለግ
    game = db.query(Game).order_by(Game.id.desc()).first()

    # 💡 [ዋናው ማስተካከያ] ጨዋታ በዳታቤዝ ውስጥ ጨርሶ ከሌለ ወዲያውኑ አዲስ መፍጠር
    if not game:
        game = Game(
            game_no=str(random.randint(500000, 699999)), # ልክ በፎቶው ላይ እንዳየኸው ዓይነት ቁጥር
            status="running",
            ticket_price=10.0,
            total_players=0,
            total_pool=0.0
        )
        db.add(game)
        db.commit()
        db.refresh(game)

    # 2. ጨዋታው ካለቀ አዲስ የነቃ ጨዋታ ማዘጋጀት (Auto-Loop ለሚቀጥለው ዙር)
    elif game.status == "finished":
        game = Game(
            game_no=str(int(game.game_no) + 1), # የጨዋታውን ቁጥር በ1 መጨመር
            status="running",
            ticket_price=10.0,
            total_players=0,
            total_pool=0.0
        )
        db.add(game)
        db.commit()
        db.refresh(game)

    return {
        "success": True,
        "game_id": game.id,
        "game_no": game.game_no,
        "status": game.status,
        "ticket_price": game.ticket_price,
        "total_players": game.total_players,
        "total_pool": game.total_pool
    }
