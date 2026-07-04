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
    user = models.User(
        telegram_id=telegram_id,
        telegram_name=telegram_name,
        first_name=first_name,
        balance=0
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
