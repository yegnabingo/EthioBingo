import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import User, Game, Deposit, Withdrawal
from app.schemas import DepositCreate, WithdrawCreate 

router = APIRouter(
    prefix="/api",
    tags=["Users"]
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# 🛠️ ማስተካከያ፦ ADMIN_CHAT_ID ን በትክክል አንብቦ ወደ ስትሪንግ ይቀይራል
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_CHAT_ID", "")).strip()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 🛠️ ማስተካከያ፦ Telegram Notification በ response መልክ ተይዞ ስታተሱ ፕሪንት ይደረጋል
def send_admin_notification(text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_TELEGRAM_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )
        print(response.status_code)
        print(response.text)
    except Exception as e:
        print(f"⚠️ Telegram admin notify error: {e}")

# 🛠️ ማስተካከያ፦ Telegram Edit Payload እና Response ህትመት በተጠየቀው መሠረት ተስተካክሏል
def update_telegram_message(message_id: int, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": ADMIN_TELEGRAM_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": []
        }
    }
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )
        print(response.status_code)
        print(response.text)
    except Exception as e:
        print("Telegram Edit Error:", e)

class AdminAction(BaseModel):
    deposit_id: int | None = None
    withdraw_id: int | None = None
    action: str
    admin_telegram_id: str
    message_id: int | None = None

# 📥 1. አዲስ ተጫዋች ሲመዘገብ
@router.post("/users/register")
def register_user(telegram_id: str, telegram_name: str = None, first_name: str = None, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.telegram_id == telegram_id).first()
    if existing:
        return {
            "success": True, "message": "ተጠቃሚው አስቀድሞ ተመዝግቧል",
            "user": {"telegram_id": existing.telegram_id, "balance": existing.balance, "wallet": existing.balance, "gift_coin": getattr(existing, "gift_coin", 0.0)}
        }
    new_user = User(telegram_id=telegram_id, telegram_name=telegram_name, first_name=first_name, balance=0.0, gift_coin=0.0, created_at=datetime.utcnow())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"success": True, "message": "ምዝገባው በተካሄደ ሁኔታ ተጠናቋል", "user": {"telegram_id": new_user.telegram_id, "balance": new_user.balance, "wallet": new_user.balance}}

# 🔍 2. የተጫዋቹን የዋሌት መረጃ መፈተሻ API (አንድ አይነት ወጥ ፎርማት እንዲኖረው ተደርጓል)
@router.get("/users/{telegram_id}")
def get_user(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"success": False, "message": "User not found", "user": {"telegram_id": telegram_id, "balance": 0.0, "wallet": 0.0}}
    return {
        "success": True, 
        "user": {
            "telegram_id": user.telegram_id, 
            "balance": user.balance, 
            "wallet": user.balance,
            "gift": getattr(user, "gift_coin", 0.0)
        }
    }

# 💰 3. ተጫዋች ከሚኒ አፕ ላይ ዲፖዚት ሲያደርግ (Deposit Request)
@router.post("/users/deposit")
def user_deposit_request(req: DepositCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው በዳታቤዝ ላይ አልተገኘም!")

    try:
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
        raise HTTPException(status_code=500, detail="ዲፖዚቱን በዳታቤዝ ላይ መመዝገብ አልተቻለም።")

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve (አጽድቅ)", "callback_data": f"app_dep_{new_deposit.id}"},
            {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_dep_{new_deposit.id}"}
        ]]
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
    return {"success": True, "message": "የማስገቢያ ጥያቄዎ በተሳካ ሁኔታ ለአድሚን ተልኳል!"}

# 📤 4. ተጫዋች ከሚኒ አፕ ላይ ዊዝድሮው ሲያደርግ (Withdraw Request)
@router.post("/users/withdraw")
def user_withdraw_request(req: WithdrawCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው በዳታቤዝ ላይ አልተገኘም!")

    if user.balance < req.amount:
        return {"success": False, "message": f"ይቅርታ፣ በቂ ባላንስ የሎትም! ያሎት ባላንስ {user.balance} ETB ነው።"}

    try:
        user.balance -= req.amount
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
        "inline_keyboard": [[
            {"text": "✅ Paid (ከፍያለሁ)", "callback_data": f"app_wit_{new_withdraw.id}"},
            {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_wit_{new_withdraw.id}"}
        ]]
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

# 👮‍♂️ 5. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ (Deposit)
@router.post("/deposit/admin/approve")
def admin_approve_deposit(payload: AdminAction, db: Session = Depends(get_db)):
    deposit = db.query(Deposit).filter(Deposit.id == payload.deposit_id).first()
    if not deposit: return {"success": False, "message": "የዲፖዚት ጥያቄው አልተገኘም"}
    if deposit.status != "Pending": return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል"}

    user = db.query(User).filter(User.id == deposit.user_id).first()
    if not user: return {"success": False, "message": "ተጫዋቹ አልተገኘም"}

    if payload.action == "APPROVE":
        user.balance += deposit.amount
        deposit.status = "Approved"
        deposit.approved_by = payload.admin_telegram_id
        db.commit()
        
        if payload.message_id:
            update_telegram_message(payload.message_id, f"🟢 <b>የዲፖዚት ጥያቄ #{deposit.id} ጸድቋል!</b>\n💰 የተጨመረው መጠን፦ {deposit.amount} ETB\n👤 የተጫዋች ID: {user.telegram_id}")
            
        return {"success": True, "message": "ዲፖዚቱ በተሳካ ሁኔታ ጸድቋል!"}
    
    else:
        deposit.status = "Rejected"
        deposit.approved_by = payload.admin_telegram_id
        db.commit()
        
        if payload.message_id:
            update_telegram_message(payload.message_id, f"🔴 <b>የዲፖዚት ጥያቄ #{deposit.id} በባለሙያው ውድቅ ተደርጓል!</b>")
            
        return {"success": True, "message": "ጥያቄው ውድቅ ተደርጓል!"}

# 👮‍♂️ 6. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ (Withdraw)
@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: AdminAction, db: Session = Depends(get_db)):
    withdraw = db.query(Withdrawal).filter(Withdrawal.id == payload.withdraw_id).first()
    if not withdraw: return {"success": False, "message": "የማውጫ ጥያቄው አልተገኘም"}
    if withdraw.status != "Pending": return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል"}

    user = db.query(User).filter(User.id == withdraw.user_id).first()
    if not user: return {"success": False, "message": "ተጫዋቹ አልተገኘም"}

    if payload.action == "REJECT":
        user.balance += withdraw.amount
        withdraw.status = "Rejected"
        withdraw.approved_by = payload.admin_telegram_id
        db.commit()
             
        if payload.message_id:
            update_telegram_message(payload.message_id, f"🔴 <b>የማውጫ ጥያቄ #{withdraw.id} ተሰርዟል!</b>\n💰 {withdraw.amount} ETB ወደ ተጫዋቹ ሂሳብ ተመልሷል።")
            
        return {"success": True, "message": "የማውጫ ጥያቄው ውድቅ ተደርጎ ብሩ ተመልሷል!"}
    
    else:
        withdraw.status = "Approved"
        withdraw.approved_by = payload.admin_telegram_id
        db.commit()
        
        if payload.message_id:
            update_telegram_message(payload.message_id, f"🟢 <b>የማውጫ ክፍያ #{withdraw.id} መፈጸሙ ተረጋግጧል!</b>\n💰 የተላከው መጠን፦ {withdraw.amount} ETB")
        
        return {"success": True, "message": "ክፍያው መፈጸሙ ተረጋግጧል!"}
