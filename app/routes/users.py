import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime  # 👈 ለጊዜ ማስተካከያ ተጨምሯል

from app.database import SessionLocal
from app.models import User, Game, Deposit, Withdrawal

router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)

# ⚙️ የቴሌግራም ቦት ቅንብሮች (ከ Railway Env በአንድ አይነት ስም ያነባሉ)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_CHAT_ID", "YOUR_TELEGRAM_ID_HERE")

def send_admin_notification(text: str, reply_markup=None):
    """ለአድሚኑ በቴሌግራም ቦት በኩል የውሳኔ ቁልፍ ያለው መልዕክት መላኪያ"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_TELEGRAM_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        res = requests.post(url, json=payload, timeout=10) # Timeout ተጨምሯል እንዳይዝረከረክ
        print(f"📡 Telegram Router Notify Log: {res.text}")
    except Exception as e:
        print(f"⚠️ Telegram admin notify error: {e}")

# 📝 የፒዳንቲክ ሞዴሎች (Schemas)
class DepositRequest(BaseModel):
    telegram_id: str
    telegram_name: str
    amount: float
    bank_name: str
    sms_data: str

class WithdrawRequest(BaseModel):
    telegram_id: str
    amount: float
    bank_name: str
    account_number: str

class AdminActionPayload(BaseModel):
    deposit_id: int = None
    withdraw_id: int = None
    action: str  # "APPROVE" ወይም "REJECT"
    admin_telegram_id: str = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 📥 1. አዲስ ተጫዋች ሲመዘገብ
@router.post("/register")
def register_user(
    telegram_id: str,
    telegram_name: str = None,
    first_name: str = None,
    db: Session = Depends(get_db)
):
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
                "gift_coin": getattr(existing, "gift_coin", 0.0)
            }
        }

    new_user = User(
        telegram_id=telegram_id,
        telegram_name=telegram_name,
        first_name=first_name,
        balance=0.0,
        gift_coin=0.0,
        created_at=datetime.utcnow()  # 👈 በእጅ ትክክለኛውን ሰዓት መስጠት (ፊክስ)
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
            "gift_coin": new_user.gift_coin
        }
    }


# 🔍 2. የተጫዋቹን የዋሌት መረጃ መፈተሻ API
@router.get("/{telegram_id}")
def get_user(
    telegram_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        return {
            "success": False,
            "message": "User not found",
            "user": {
                "telegram_id": telegram_id,
                "telegram_name": "",
                "first_name": "Guest",
                "balance": 0.0,
                "gift_coin": 0.0
            }
        }

    return {
        "success": True,
        "user": {
            "telegram_id": user.telegram_id,
            "telegram_name": user.telegram_name,
            "first_name": user.first_name,
            "wallet": user.balance,
            "gift": getattr(user, "gift_coin", 0.0)
        }
    }


# 💰 3. ተጫዋች ከሚኒ አፕ ላይ ዲፖዚት ሲያደርግ (Deposit Request)
@router.post("/deposit")
def user_deposit_request(req: DepositRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")

    try:
        # 🛠 ፊክስ፦ የሌሉትን ኮለሞች ትተን በነባሩ 'tx_hash' ላይ መረጃውን አቀናጅተን መያዝ
        new_deposit = Deposit(
            user_id=user.id,
            amount=req.amount,
            tx_hash=f"ባንክ፦ {req.bank_name} | SMS፦ {req.sms_data}", 
            status="Pending",
            created_at=datetime.utcnow()
        )
        db.add(new_deposit)
        db.commit()
        db.refresh(new_deposit)
    except Exception as e:
        db.rollback()
        print(f"❌ Database Deposit Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ዲፖዚቱን ዳታቤዝ ላይ መመዝገብ አልተቻለም፦ {str(e)}")

    # 📲 ለአድሚኑ የቴሌግራም inline ቁልፍ ማዘጋጀት
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve (አጽድቅ)", "callback_data": f"app_dep_{new_deposit.id}"},
                {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_dep_{new_deposit.id}"}
            ]
        ]
    }

    msg_text = (
        f"🔔 <b>አዲስ የገንዘብ ማስገቢያ ጥያቄ!</b>\n\n"
        f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_deposit.id}\n"
        f"👤 ተጫዋች፦ {req.telegram_name} (ID: {req.telegram_id})\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>\n\n"
        f"📝 <b>የባንክ SMS መረጃ፦</b>\n<code>{req.sms_data}</code>"
    )
    
    send_admin_notification(msg_text, reply_markup=inline_keyboard)
    return {"success": True, "message": "የማስገቢያ ጥያቄዎ በተካካ ሁኔታ ለአድሚን ተልኳል!"}


# 📤 4. ተጫዋች ከሚኒ አፕ ላይ ዊዝድሮው ሲያደርግ (Withdraw Request)
@router.post("/withdraw")
def user_withdraw_request(req: WithdrawRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")

    if user.balance < req.amount:
        return {"success": False, "message": f"ይቅርታ፣ በቂ ባላንስ የሎትም! ያሎት ባላንስ {user.balance} ETB ነው።"}

    try:
        # 🔐 ብሩን ከአካውንቱ ላይ ጊዜያዊ ሆልድ ማድረግ
        user.balance -= req.amount
        
        # 🛠 ፊክስ፦ የሌለውን 'method' ኮለም ትተን፣ ባንኩን እና አካውንቱን አንድ ላይ አቀናጅተን 'wallet' ውስጥ መያዝ
        new_withdraw = Withdrawal(
            user_id=user.id,
            amount=req.amount,
            wallet=f"ባንክ፦ {req.bank_name} | አካውንት፦ {req.account_number}",
            status="Pending",
            created_at=datetime.utcnow()
        )
        db.add(new_withdraw)
        db.commit()
        db.refresh(new_withdraw)
    except Exception as e:
        db.rollback()
        print(f"❌ Database Withdraw Error: {str(e)}")
        raise HTTPException(status_code=500, detail="የማውጫ ጥያቄውን መመዝገብ አልተቻለም።")

    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Paid (ከፍያለሁ)", "callback_data": f"app_wit_{new_withdraw.id}"},
                {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_wit_{new_withdraw.id}"}
            ]
        ]
    }

    msg_text = (
        f"⚠️ <b>አዲስ የገንዘብ ማውጫ ጥያቄ!</b>\n\n"
        f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_withdraw.id}\n"
        f"👤 ተጫዋች ID፦ {req.telegram_id}\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💳 የባንክ አካውንት፦ <code>{req.account_number}</code>\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>\n\n"
        f"<i>ይህንን ብር በባንክ ልከው ሲያበቁ 'Paid' የሚለውን ይጫኑ።</i>"
    )

    send_admin_notification(msg_text, reply_markup=inline_keyboard)
    return {"success": True, "message": "የማውጫ ጥያቄዎ ተመዝግቧል፣ አድሚኑ ልኮ ሲያበቃ ባላንስዎ ይስተካከላል!"}


# 👮‍♂️ 5. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ የሰርቨሩ ማስተካከያ ኤፒአይ
@router.post("/deposit/admin/approve")
def admin_approve_deposit(payload: AdminActionPayload, db: Session = Depends(get_db)):
    deposit = db.query(Deposit).filter(Deposit.id == payload.deposit_id).first()
    if not deposit:
        return {"success": False, "message": "የዲፖዚት ጥያቄው በሰርቨር ላይ አልተገኘም"}
        
    if deposit.status != "Pending":
        return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል"}

    user = db.query(User).filter(User.id == deposit.user_id).first()
    if not user:
        return {"success": False, "message": "ተጫዋቹ በሰርቨር ላይ አልተገኘም"}

    if payload.action == "APPROVE":
        deposit.status = "Approved"
        deposit.approved_by = payload.admin_telegram_id
        user.balance += deposit.amount  # 🛠 ፊክስ፦ የተላከውን እውነተኛ የብር መጠን ይጨምራል
        db.commit()
        return {"success": True, "message": "ዲፖዚቱ በተሳካ ሁኔታ ጸድቋል!"}
    
    deposit.status = "Rejected"
    deposit.approved_by = payload.admin_telegram_id
    db.commit()
    return {"success": True, "message": "ጥያቄው ውድቅ ተደርጓል!"}


@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: AdminActionPayload, db: Session = Depends(get_db)):
    withdraw = db.query(Withdrawal).filter(Withdrawal.id == payload.withdraw_id).first()
    if not withdraw:
        return {"success": False, "message": "የማውጫ ጥያቄው አልተገኘም"}
        
    if withdraw.status != "Pending":
        return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል"}

    user = db.query(User).filter(User.id == withdraw.user_id).first()
    if not user:
        return {"success": False, "message": "ተጫዋቹ አልተገኘም"}

    if payload.action == "REJECT":
        withdraw.status = "Rejected"
        withdraw.approved_by = payload.admin_telegram_id
        user.balance += withdraw.amount # 🛠 ፊክስ፦ ጥያቄው ውድቅ ከተደረገ እውነተኛውን መጠን ይመልሳል
        db.commit()
        return {"success": True, "message": "የማውጫ ጥያቄው ውድቅ ተደርጎ ብሩ ተመልሷል!"}
    
    withdraw.status = "Approved"
    withdraw.approved_by = payload.admin_telegram_id
    db.commit()
    return {"success": True, "message": "ክፍያው መፈጸሙ ተረጋግጧል!"}
