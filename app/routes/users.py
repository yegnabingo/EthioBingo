import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.database import SessionLocal
from app.models import User, Game, Deposit, Withdrawal
from app.schemas import DepositCreate, WithdrawCreate 

router = APIRouter(
    prefix="/api",
    tags=["Users"]
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_CHAT_ID", "")).strip()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_admin_notification(text: str, reply_markup=None):
    """ወደ አድሚን ቴሌግራም መረጃ ይላክ"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_TELEGRAM_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(url, json=payload, timeout=10)
        print("✅ Notification Status:", response.status_code)
    except Exception as e:
        print(f"❌ Telegram admin notify error: {e}")

def _telegram_edit_message_sync(message_id: int, text: str):
    """የቴሌግራም መልዕክትን ከጀርባ የሚያስተካክል (Non-blocking)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": ADMIN_TELEGRAM_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"✅ Telegram Edit Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Telegram Edit Exception: {e}")

# 🛠️ የ Pydantic ሞዴል
class AdminAction(BaseModel):
    deposit_id: Optional[int] = None
    withdraw_id: Optional[int] = None
    action: str
    admin_telegram_id: str
    message_id: Optional[int] = None

# 📥 1. አዲስ ተጫዋች ሲመዘገብ
@router.post("/users/register")
def register_user(telegram_id: str, telegram_name: str = None, first_name: str = None, db: Session = Depends(get_db)):
    if not str(telegram_id).strip().isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    existing = db.query(User).filter(User.telegram_id == telegram_id).first()
    if existing:
        return {
            "success": True, "message": "ተጠቃሚው አስቀድሞ ተመዝግቧል",
            "user": {
                "telegram_id": existing.telegram_id, 
                "balance": existing.balance, 
                "wallet": existing.balance,
                "gift_coin": getattr(existing, "gift_coin", 0.0)
            }
        }
    new_user = User(
        telegram_id=telegram_id, 
        telegram_name=telegram_name, 
        first_name=first_name, 
        balance=0.0, 
        gift_coin=0.0, 
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "success": True, 
        "message": "ምዝገባው በተካሄደ ሁኔታ ተጠናቋል", 
        "user": {
            "telegram_id": new_user.telegram_id, 
            "balance": new_user.balance,
            "wallet": new_user.balance,
            "gift_coin": new_user.gift_coin
        }
    }

# 🔍 2. የተጫዋቹን የዋሌት መረጃ መፈተሻ API
@router.get("/users/{telegram_id}")
def get_user(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {
            "success": False, 
            "user": {"telegram_id": telegram_id, "balance": 0.0, "wallet": 0.0, "gift_coin": 0.0}
        }
    return {
        "success": True, 
        "user": {
            "telegram_id": user.telegram_id, 
            "balance": user.balance,
            "wallet": user.balance,
            "gift_coin": getattr(user, "gift_coin", 0.0)
        }
    }

# 💰 3. ተጫዋች ከሚኒ አፕ ላይ ዲፖዚት ሲያደርግ
@router.post("/users/deposit")
def user_deposit_request(req: DepositCreate, db: Session = Depends(get_db)):
    if not str(req.telegram_id).strip().isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        return {"success": False, "message": "User not found."}

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
        return {"success": False, "message": "Failed to record deposit request."}

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve (አጽдቅ)", "callback_data": f"app_dep_{new_deposit.id}"},
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

# 📤 4. ተጫዋች ከሚኒ አፕ ላይ ዊዝድሮው ሲያደርግ
@router.post("/users/withdraw")
def user_withdraw_request(req: WithdrawCreate, db: Session = Depends(get_db)):
    if not str(req.telegram_id).strip().isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    user = db.query(User).filter(User.telegram_id == req.telegram_id).first()
    if not user:
        return {"success": False, "message": "User not found."}

    if user.balance < req.amount:
        return {"success": False, "message": f"ይቅርታ偏 በቂ ባላንስ የሎትም! ያሎት ባላንስ {user.balance} ETB ነው።"}

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
        return {"success": False, "message": "Failed to record withdrawal request."}

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
        f"<i>ይህንን ብር በባንክ ልከው ሲያበቁ 'Paid' የሚለውን ይጫኑ。</i>"
    )

    send_admin_notification(msg_text, reply_markup=inline_keyboard)
    return {"success": True, "message": "የማውጫ ጥያቄዎ ተመዝግቧል!"}

# 👮‍♂️ 5. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ (Deposit)
@router.post("/deposit/admin/approve")
def admin_approve_deposit(payload: AdminAction, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not str(payload.admin_telegram_id).strip().isdigit():
        return {"success": False, "message": "Invalid admin ID."}
    
    deposit = db.query(Deposit).filter(Deposit.id == payload.deposit_id).first()
    if not deposit: 
        return {"success": False, "message": "የዲፖዚት ጥያቄው አልተገኘም"}
    if deposit.status != "Pending": 
        return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል"}

    user = db.query(User).filter(User.id == deposit.user_id).first()
    if not user: 
        return {"success": False, "message": "ተጫዋቹ አልተገኘም"}

    if payload.action == "APPROVE":
        user.balance += deposit.amount
        deposit.status = "Approved"
        deposit.approved_by = payload.admin_telegram_id
        db.commit()
        
        if payload.message_id:
            # 🛠️ ፊክስ፦ የቴሌግራም መልዕክት ማስተካከያውን ወደ Background Task በመቀየር ሰርቨሩ እንዳይቆለፍ ማድረግ
            text = f"🟢 <b>የዲፖዚት ጥያቄ #{deposit.id} ጸድቋል!</b>\n💰 የተጨመረው መጠን፦ {deposit.amount} ETB\n👤 User: {user.telegram_id}"
            background_tasks.add_task(_telegram_edit_message_sync, payload.message_id, text)
            
        return {"success": True, "message": "ዲፖዚቱ በተሳካ ሁኔታ ጸድቋል!"}
    
    else:
        deposit.status = "Rejected"
        deposit.approved_by = payload.admin_telegram_id
        db.commit()
        
        if payload.message_id:
            text = f"🔴 <b>የዲፖዚት ጥያቄ #{deposit.id} ውድቅ ተደርጓል!</b>"
            background_tasks.add_task(_telegram_edit_message_sync, payload.message_id, text)
            
        return {"success": True, "message": "ጥያቄው ውድቅ ተደርጓል!"}

# 👮‍♂️ 6. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ (Withdraw)
@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: AdminAction, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not str(payload.admin_telegram_id).strip().isdigit():
        return {"success": False, "message": "Invalid admin ID."}
    
    withdraw = db.query(Withdrawal).filter(Withdrawal.id == payload.withdraw_id).first()
    if not withdraw: 
        return {"success": False, "message": "የማውጫ ጥያቄው አልተገኘም"}
    if withdraw.status != "Pending": 
        return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል"}

    user = db.query(User).filter(User.id == withdraw.user_id).first()
    if not user: 
        return {"success": False, "message": "ተጫዋቹ አልተገኘም"}

    if payload.action == "REJECT":
        user.balance += withdraw.amount
        withdraw.status = "Rejected"
        withdraw.approved_by = payload.admin_telegram_id
        db.commit()
             
        if payload.message_id:
            text = f"🔴 <b>የማውጫ ጥያቄ #{withdraw.id} ተሰርዟል!</b>\n💰 {withdraw.amount} ETB ተመልሷል"
            background_tasks.add_task(_telegram_edit_message_sync, payload.message_id, text)
            
        return {"success": True, "message": "የማውጫ ጥያቄው ውድቅ ተደርጎ ብሩ ተመልሷል!"}
    
    else:
        withdraw.status = "Approved"
        withdraw.approved_by = payload.admin_telegram_id
        db.commit()
        
        if payload.message_id:
            text = f"🟢 <b>የማውጫ ክፍያ #{withdraw.id} መፈጸሙ ተረጋግጧል!</b>\n💰 መጠን፦ {withdraw.amount} ETB"
            background_tasks.add_task(_telegram_edit_message_sync, payload.message_id, text)
        
        return {"success": True, "message": "ክፍያው መፈጸሙ ተረጋግጧል!"}
