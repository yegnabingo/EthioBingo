from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User

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


# 📥 1. አዲስ ተጫዋች ሲመዘገብ (ወይም ሚኒ አፑን መጀመሪያ ሲከፍት)
@router.post("/register")
def register_user(
    telegram_id: str,
    telegram_name: str = None,
    first_name: str = None,
    db: Session = Depends(get_db)
):
    # ተጠቃሚው አስቀድሞ መኖሩን ማረጋገጥ
    existing = db.query(User).filter(User.telegram_id == telegram_id).first()
    if existing:
        return {
            "success": True,
            "message": "ተጠቃሚው አስቀድሞ ተመዝግቧል",
            "user": {
                "telegram_id": existing.telegram_id,
                "telegram_name": existing.telegram_name,
                "first_name": existing.first_name,
                "balance": existing.balance,
                "gift_coins": getattr(existing, "gift_coins", 0.0) #
            }
        }

    # አዲስ ተጫዋች መፍጠር
    new_user = User(
        telegram_id=telegram_id,
        telegram_name=telegram_name,
        first_name=first_name,
        balance=0.0,
        gift_coins=0.0  # መጀመሪያ ሲመዘገብ 0.00 ሳንቲም ይሰጠዋል
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "success": True,
        "message": "ምዝገባው በተሳካ ሁኔታ ተጠናቋል",
        "user": {
            "telegram_id": new_user.telegram_id,
            "telegram_name": new_user.telegram_name,
            "first_name": new_user.first_name,
            "balance": new_user.balance,
            "gift_coins": new_user.gift_coins
        }
    }


# 🔍 2. የተጫዋቹን የዋሌት እና የጊፍት መረጃ በቅጽበት መፈተሻ API
@router.get("/{telegram_id}")
def get_user(
    telegram_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    # 💡 ተጫዋቹ በዳታቤዝ ከሌለ ሚኒ አፑ እንዳይበላሽ ጊስት አካውንት በደህንነት መመለስ
    if not user:
        return {
            "success": False,
            "message": "User not found",
            "user": {
                "telegram_id": telegram_id,
                "telegram_name": "",
                "first_name": "Guest",
                "balance": 0.0,        # Wallet: - ETB
                "gift_coins": 0.0       # Gift: 0.00 Coin
            }
        }

    # 🎯 መረጃውን ልክ በስክሪኑ ላይ ባለው ፎርማት መሰረት መመለስ
    return {
        "success": True,
        "user": {
            "telegram_id": user.telegram_id,
            "telegram_name": user.telegram_name,
            "first_name": user.first_name,
            "wallet": user.balance,         # እውነተኛ ቀሪ ሂሳብ
            "gift": getattr(user, "gift_coins", 0.0) # የአድሚን ነፃ ሳንቲም
        }
    }
