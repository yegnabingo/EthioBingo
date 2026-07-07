from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Deposit

router = APIRouter(
    prefix="/api/deposit/admin",  # ከቦቱ ሊንክ ጋር እንዲጣጣም የተደረገ
    tags=["Admin Deposit"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ቦቱ የሚልከውን የJSON ፎርማት ለመቀበል የሚረዳ የPydantic ሞዴል
class AdminDepositAction(BaseModel):
    deposit_id: int
    action: str  # "APPROVE" ወይም "REJECT"
    admin_telegram_id: str

@router.post("/approve")
def approve_deposit(
    payload: AdminDepositAction,
    db: Session = Depends(get_db)
):
    # ከቦቱ የመጣውን deposit_id መፈለግ
    deposit = db.query(Deposit).filter(Deposit.id == payload.deposit_id).first()

    if not deposit:
        return {
            "success": False,
            "message": "Deposit not found"
        }

    # አድሚኑ Reject ካደረገው
    if payload.action == "REJECT":
        if deposit.status == "Rejected":
            return {"success": False, "message": "Already rejected"}
        deposit.status = "Rejected"
        db.commit()
        return {"success": True, "message": "Deposit rejected successfully"}

    # አድሚኑ Approve ካደረገው
    if deposit.status == "Approved":
        return {
            "success": False,
            "message": "Already approved"
        }

    user = db.query(User).filter(User.id == deposit.user_id).first()
    if not user:
        return {"success": False, "message": "User not found"}

    # ሂሳብ ማደስ እና ሁኔታውን መለወጥ
    user.balance += deposit.amount
    deposit.status = "Approved"

    db.commit()

    return {
        "success": True,
        "message": "Deposit approved successfully"
    }
