from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=UserResponse)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    existing = db.query(User).filter(
        User.telegram_id == user.telegram_id
    ).first()

    if existing:
        return existing

    new_user = User(
        telegram_id=user.telegram_id,
        telegram_name=user.telegram_name,
        first_name=user.first_name,
        balance=0
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get("/{telegram_id}", response_model=UserResponse)
def get_user(
    telegram_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.telegram_id == telegram_id
    ).first()

    if not user:
        return {
            "telegram_id": telegram_id,
            "telegram_name": "",
            "first_name": "Guest",
            "balance": 0
        }

    return user
