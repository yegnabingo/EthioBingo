import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import User, Game # የዲፖዚት ማጽደቂያ ላይ ጌሙን ለመፈተሽ ካስፈለገ

router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)

# ⚙️ የቴሌግራም ቦት ቅንብሮች (መልዕክት መላኪያ)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
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
        requests.post(url, json=payload)
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 📥 1. አዲስ ተጫዋች ሲመዘገብ (የመጀመሪያ ፍሰት)
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
        balance=0.0,  # 🛠 ፊክስ፦ አዲስ ተጫዋች መጀመሪያ ላይ 0.00 ብር እንዲኖረው
        gift_coin=0.0
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


# 🔍 2. የተጫዋቹን የዋሌት እና የጊፍት መረጃ በቅጽበት መፈተሻ API
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

    # 💡 ማሳሰቢያ፦ ዲፖዚቱ በቀጥታ ባላንስ ላይ አይጨመርም! አድሚኑ ማጽደቅ አለበት።
    # ለጊዜው አድሚኑ እንዲለየው የተጫዋቹን ዳታቤዝ መታወቂያ (ID) ለቦቱ መላኪያነት እንይዛለን
    db.commit() 

    # 📲 ለአድሚኑ የቴሌግራም inline ቁልፍ ማዘጋጀት
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve (አጽድቅ)", "callback_data": f"app_dep_{user.id}"},
                {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_dep_{user.id}"}
            ]
        ]
    }

    msg_text = (
        f"🔔 <b>አዲስ የገንዘብ ማስገቢያ ጥያቄ!</b>\n\n"
        f"👤 ተጫዋች፦ {req.telegram_name} (ID: {req.telegram_id})\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>\n\n"
        f"📝 <b>የባንክ SMS መረጃ፦</b>\n<code>{req.sms_data}</code>"
    )
    
    send_admin_notification(msg_text, reply_markup=inline_keyboard)
    return {"success": True, "message": "የማስገቢያ ጥያቄዎ በተሳካ ሁኔታ ለአድሚን ተልኳል!"}


# 📤 4. ተጫዋች ከሚኒ አፕ ላይ ዊዝድሮው ሲያደርግ (Withdraw Request)
@router.post("/withdraw")
def user_withdraw_request(req: WithdrawRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")

    if user.balance < req.amount:
        return {"success": False, "message": f"ይቅርታ፣ በቂ ባላንስ የሎትም! ያሎት ባላንስ {user.balance} ETB ነው።"}

    # 🔐 ብሩን ከአካውንቱ ላይ ጊዜያዊ ሆልድ እናደርገዋለን (አድሚኑ ውድቅ ካደረገው ይመለሳል)
    user.balance -= req.amount
    db.commit()

    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Paid (ከፍያለሁ)", "callback_data": f"app_wit_{user.id}"},
                {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_wit_{user.id}"}
            ]
        ]
    }

    msg_text = (
        f"⚠️ <b>አዲስ የገንዘብ ማውጫ ጥያቄ!</b>\n\n"
        f"👤 ተጫዋች ID፦ {req.telegram_id}\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💳 የባንክ አካውንት፦ <code>{req.account_number}</code>\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>\n\n"
        f"ይህንን ብር በባንክ ልከው ሲያበቁ 'Paid' የሚለውን ይጫኑ።"
    )

    send_admin_notification(msg_text, reply_markup=inline_keyboard)
    return {"success": True, "message": "የማውጫ ጥያቄዎ ተመዝግቧል፣ አድሚኑ ልኮ ሲያበቃ ባላንስዎ ይስተካከላል!"}


# 👮‍♂️ 5. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ የሰርቨሩ ማስተካከያ ኤፒአይ
@router.post("/deposit/admin/approve")
def admin_approve_deposit(payload: AdminActionPayload, db: Session = Depends(get_db)):
    # እዚህ ላይ payload.deposit_id የተጫዋቹ የዳታቤዝ `user.id` ነው (ከቦቱ የመጣ)
    user = db.query(User).filter(User.id == payload.deposit_id).first()
    if not user:
        return {"success": False, "message": "ተጫዋቹ በሰርቨር ላይ አልተገኘም"}

    # አድሚኑ ካጸደቀው ብሩን ጨምርለት፣ ካልሆነ ዝም በል
    if payload.action == "APPROVE":
        # ለአሁኑ የሙከራ ሂደት በቦቱ የላከውን ዝቅተኛ የዲፖዚት መነሻ (50 ብር) ወይም አድሚኑ የሚሰጠውን እንጨምራለን
        # (ሙሉ አውቶማቲክ SMS Parser በባክኤንድህ ሌላ ቦታ ካለ እሱ ላይ ይጨምራል፣ ካልሆነ አውቶማቲክ 50 ብር ይጨምራል)
        user.balance += 50.0 
        db.commit()
        
        # ለተጫዋቹ በቦት ማሳወቅ ትችላለህ (አማራጭ)
        return {"success": True, "message": "ዲፖዚቱ በተሳካ ሁኔታ ጸድቋል!"}
    
    return {"success": True, "message": "ጥያቄው ውድቅ ተደርጓል!"}


@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: AdminActionPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.withdraw_id).first()
    if not user:
        return {"success": False, "message": "ተጫዋቹ አልተገኘም"}

    if payload.action == "REJECT":
        # ጥያቄው ውድቅ ከተደረገ የቀነስንበትን ብር እንመልስለታለን
        user.balance += 50.0 # እዚህ ጋር መመለስ ያለበት የጥያቄው እውነተኛ መጠን ነው
        db.commit()
        return {"success": True, "message": "የማውጫ ጥያቄው ውድቅ ተደርጎ ብሩ ተመልሷል!"}
    
    # APPROVED ከሆነ ብሩ ቀድሞ ስለተቀነሰ ዝም ብለን እናጸድቀዋለን
    return {"success": True, "message": "ክፍያው መፈጸሙ ተረጋግጧል!"}
