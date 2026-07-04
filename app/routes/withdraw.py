from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Withdrawal
from app.schemas import WithdrawlCreate

router = APIRouter(
    prefix="/api/withdraw",
    tags=["Withdraw"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/request")
def create_withdrawl(
    telegram_id: str,
    withdraw: WithdrawlCreate,
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

    if user.balance < withdraw.amount:
        return {
            "success": False,
            "message": "Insufficient balance"
        }

    new_withdraw = Withdrawl(
        user_id=user.id,
        amount=withdraw.amount,
        wallet=withdraw.wallet,
        status="pending"
    )

    db.add(new_withdraw)
    db.commit()

    return {
        "success": True,
        "message": "Withdrawl request sent to admin"
    }
