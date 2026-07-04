from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Deposit
from app.schemas import DepositCreate

router = APIRouter(
    prefix="/api/deposit",
    tags=["Deposit"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/request")
def create_deposit(
    telegram_id: str,
    deposit: DepositCreate,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.telegram_id == telegram_id
    ).first()

    if not user:
        return {
            "success": False,
            "message": "User not found"
        }

    new_deposit = Deposit(
        user_id=user.id,
        amount=deposit.amount,
        tx_hash=deposit.tx_hash,
        status="Pending"
    )

    db.add(new_deposit)
    db.commit()

    return {
        "success": True,
        "message": "Deposit request sent to admin"
    }
