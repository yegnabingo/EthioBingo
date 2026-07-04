from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Deposit

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/approve-deposit/{deposit_id}")
def approve_deposit(
    deposit_id: int,
    db: Session = Depends(get_db)
):

    deposit = db.query(Deposit).filter(
        Deposit.id == deposit_id
    ).first()

    if not deposit:
        return {
            "success": False,
            "message": "Deposit not found"
        }

    if deposit.status == "approved":
        return {
            "success": False,
            "message": "Already approved"
        }

    user = db.query(User).filter(
        User.id == deposit.user_id
    ).first()

    user.balance += deposit.amount

    deposit.status = "approved"

    db.commit()

    return {
        "success": True,
        "message": "Deposit approved successfully"
    }
