from sqlalchemy.orm import Session
from app import models

# ==========================
# USERS
# ==========================

def get_user_by_telegram_id(db: Session, telegram_id: str):
    return (
        db.query(models.User)
        .filter(models.User.telegram_id == telegram_id)
        .first()
    )


def create_user(
    db: Session,
    telegram_id: str,
    telegram_name: str,
    first_name: str
):
    # 🎯 ፊክስ፦ አዲስ ሰው ሲመዘገብ balance እና wallet ሁለቱም 0 መሆናቸውን እዚህ ላይ እናረጋግጣለን
    user = models.User(
        telegram_id=telegram_id,
        telegram_name=telegram_name,
        first_name=first_name,
        balance=0.0,
        wallet=0.0,
        gift_coin=0.0
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ==========================
# GAMES
# ==========================

def create_game(db: Session, game_no: int, ticket_price: float):
    game = models.Game(
        game_no=game_no,
        ticket_price=ticket_price,
        status="WAITING"
    )

    db.add(game)
    db.commit()
    db.refresh(game)

    return game


def get_current_game(db: Session):
    return (
        db.query(models.Game)
        .order_by(models.Game.id.desc())
        .first()
    )


def update_game_status(db: Session, game, status: str):
    game.status = status

    db.commit()

    db.refresh(game)

    return game
