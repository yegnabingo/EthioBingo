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

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_TELEGRAM_ID", "")).strip()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_admin_notification(text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_TELEGRAM_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(url, json=payload, timeout=10)
        print("✅ Notification Status:", response.status_code)
    except Exception as e:
        print(f"❌ Telegram admin notify error: {e}")

def _telegram_edit_message_sync(chat_id: str, message_id: int, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"✅ Telegram Edit Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Telegram Edit Exception: {e}")

class AdminAction(BaseModel):
    deposit_id: Optional[int] = None
    withdraw_id: Optional[int] = None
    action: str
    admin_telegram_id: str
    message_id: Optional[int] = None
    admin_password: Optional[str] = None

# 📥 1. አዲስ ተጫዋች ሲመዘገብ
@router.post("/users/register")
def register_user(telegram_id: str, telegram_name: str = None, first_name: str = None, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    if not tg_id_str.isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    existing = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if existing:
        user_wallet = getattr(existing, "wallet", 0.0) or 0.0
        return {
            "success": True, "message": "ተጠቃሚው አስቀድሞ ተመዝግቧል",
            "user": {
                "telegram_id": existing.telegram_id, 
                "balance": user_wallet, 
                "wallet": user_wallet,
                "gift_coin": getattr(existing, "gift_coin", 0.0) or 0.0
            }
        }
    
    new_user = User(
        telegram_id=tg_id_str, 
        telegram_name=telegram_name, 
        first_name=first_name, 
        wallet=0.0, 
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
            "balance": new_user.wallet,
            "wallet": new_user.wallet,
            "gift_coin": new_user.gift_coin
        }
    }

# 🔍 2. የተጫዋቹን የዋሌት መረጃ መፈተሻ API
@router.get("/users/{telegram_id}")
def get_user(telegram_id: str, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {
            "success": False, 
            "user": {"telegram_id": tg_id_str, "balance": 0.0, "wallet": 0.0, "gift_coin": 0.0}
        }
        
    user_wallet = getattr(user, "wallet", 0.0) or 0.0
    return {
        "success": True, 
        "user": {
            "telegram_id": user.telegram_id, 
            "balance": user_wallet, 
            "wallet": user_wallet,
            "gift_coin": getattr(user, "gift_coin", 0.0) or 0.0
        }
    }

# 💰 3. ተጫዋች ከሚኒ አፕ ላይ ዲፖዚት ሲያደርግ
@router.post("/users/deposit")
def user_deposit_request(req: DepositCreate, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    if not tg_id_str.isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    
    if not user:
        try:
            user = User(
                telegram_id=tg_id_str,
                telegram_name=req.telegram_name if req.telegram_name else "ተጫዋች",
                wallet=0.0,
                balance=0.0,
                gift_coin=0.0,
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"የተጠቃሚ ምዝገባ ስህተት፦ {str(e)}"}

    try:
        new_deposit = Deposit(
            user_id=user.id,
            amount=req.amount,
            method=req.bank_name,     
            sms_text=req.sms_data,    
            tx_hash=f"ባንክ፦ {req.bank_name} | SMS፦ {req.sms_data}", 
            status="Pending",
            created_at=datetime.utcnow(),
            telegram_id=tg_id_str,
            telegram_name=req.telegram_name if req.telegram_name else "ተጫዋች",
            wallet=str(user.wallet)
        )
        db.add(new_deposit)
        db.commit()
        db.refresh(new_deposit)
    except Exception as e:
        db.rollback()
        print(f"❌ Database Deposit Error: {e}") 
        return {"success": False, "message": f"Failed to record deposit request: {str(e)}"}

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve (አጽድቅ)", "callback_data": f"app_dep_{new_deposit.id}"},
            {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_dep_{new_deposit.id}"}
        ]]
    }

    msg_text = (
        f"🔔 <b>አዲስ የገንዘብ ማስገቢያ ጥያቄ!</b>\n\n"
        f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_deposit.id}\n"
        f"👤 ተጫዋች፦ {new_deposit.telegram_name} (ID: {new_deposit.telegram_id})\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>\n\n"
        f"📝 <b>የባንክ SMS መረጃ፦</b>\n<code>{req.sms_data}</code>"
    )
    
    send_admin_notification(msg_text, reply_markup=inline_keyboard)
    return {"success": True, "message": "የማስገቢያ ጥያቄዎ በተሳካ ሁኔታ ለአድሚን ተልኳል!"}


# 📤 4. ተጫዋች ከሚኒ አፕ ላይ ዊዝድሮው ሲያደርግ
@router.post("/users/withdraw")
def user_withdraw_request(req: WithdrawCreate, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    if not tg_id_str.isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {"success": False, "message": "User not found. Please register first."}

    user_wallet = getattr(user, "wallet", 0.0) or 0.0
    if user_wallet < req.amount:
        return {"success": False, "message": f"ይቅርታ፣ በቂ ባላንስ የሎትም! ያሎት ባላንስ {user_wallet} ETB ነው።"}

    try:
        user.wallet = user_wallet - req.amount
        user.balance = user.wallet
        
        new_withdraw = Withdrawal(
            user_id=user.id,
            amount=req.amount,
            method=req.bank_name,     
            wallet=str(req.account_number), 
            status="Pending",
            created_at=datetime.utcnow()
        )
        db.add(new_withdraw)
        db.commit()
        db.refresh(new_withdraw)
    except Exception as e:
        db.rollback()
        print(f"❌ Database Withdraw Error: {e}") 
        return {"success": False, "message": f"Failed to record withdrawal request: {str(e)}"}

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Paid (ከፍያለሁ)", "callback_data": f"app_wit_{new_withdraw.id}"},
            {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_wit_{new_withdraw.id}"}
        ]]
    }

    msg_text = (
        f"⚠️ <b>አዲስ የገንዘብ ማውጫ ጥያቄ!</b>\n\n"
        f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_withdraw.id}\n"
        f"👤 ተጫዋች ID፦ {tg_id_str}\n"
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
    try:
        deposit = db.query(Deposit).filter(Deposit.id == payload.deposit_id).first()
        if not deposit: 
            return {"success": False, "message": "የዲፖዚት ጥያቄው በዳታቤዝ ውስጥ አልተገኘም!"}
        
        if deposit.status != "pending": 
            return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል (Pending አይደለም)!"}

        user = db.query(User).filter(User.id == deposit.user_id).first()
        if not user: 
            return {"success": False, "message": "ይህንን ጥያቄ የላከው ተጫዋች አልተገኘም!"}

        if payload.action == "APPROVE":
            current_wallet = getattr(user, "wallet", 0.0) or 0.0
            user.wallet = current_wallet + deposit.amount
            user.balance = user.wallet
            
            deposit.status = "approved"
            deposit.approved_by = str(payload.admin_telegram_id)
            db.commit()
            
            if payload.message_id:
                text = (
                    f"🟢 <b>የዲፖዚት ጥያቄ #{deposit.id} ጸድቋል!</b>\n\n"
                    f"💰 <b>የተጨመረው መጠን፦</b> {deposit.amount} ETB\n"
                    f"👤 <b>ተጫዋች ID፦</b> <code>{user.telegram_id}</code>\n"
                    f"🏦 <b>ባንክ፦</b> {deposit.method}\n"
                    f"👮‍♂️ <b>ያጸደቀው አድሚን፦</b> {payload.admin_telegram_id}"
                )
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
                
            return {"success": True, "message": "ዲፖዚቱ በተሳካ ሁኔታ ጸድቋል!"}
        
        else:
            deposit.status = "rejected"
            deposit.approved_by = str(payload.admin_telegram_id)
            db.commit()
            
            if payload.message_id:
                text = f"🔴 <b>የዲፖዚት ጥያቄ #{deposit.id} ውድቅ ተደርጓል!</b>\n👮‍♂️ <b>የሰረዘው አድሚን፦</b> {payload.admin_telegram_id}"
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
                
            return {"success": True, "message": "ጥያቄው ውድቅ ተደርጓል!"}

    except Exception as e:
        db.rollback()
        error_msg = f"❌ <b>ባክኤንድ ስህተት (Deposit Approve)፦</b>\n<code>{str(e)}</code>"
        send_admin_notification(error_msg)
        return {"success": False, "message": f"Internal Server Error: {str(e)}"}


# 👮‍♂️ 6. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ (Withdraw)
@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: AdminAction, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        withdraw = db.query(Withdrawal).filter(Withdrawal.id == payload.withdraw_id).first()
        if not withdraw: 
            return {"success": False, "message": "የማውጫ ጥያቄው በዳታቤዝ ውስጥ አልተገኘም!"}
        
        if withdraw.status != "pending": 
            return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል!"}

        user = db.query(User).filter(User.id == withdraw.user_id).first()
        if not user: 
            return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

        if payload.action == "REJECT":
            current_wallet = getattr(user, "wallet", 0.0) or 0.0
            user.wallet = current_wallet + withdraw.amount
            user.balance = user.wallet
            
            withdraw.status = "rejected"
            withdraw.approved_by = str(payload.admin_telegram_id)
            db.commit()
                 
            if payload.message_id:
                text = (
                    f"🔴 <b>የማውጫ ጥያቄ #{withdraw.id} ተሰርዟል!</b>\n\n"
                    f"💰 <b>የተመለሰው መጠን፦</b> {withdraw.amount} ETB\n"
                    f"👤 <b>ተጫዋች ID፦</b> <code>{user.telegram_id}</code>\n"
                    f"👮‍♂️ <b>የሰረዘው አድሚን፦</b> {payload.admin_telegram_id}"
                )
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
                
            return {"success": True, "message": "የማውጫ ጥያቄው ውድቅ ተደርጎ ብሩ ተመልሷል!"}
        
        else:
            withdraw.status = "approved"
            withdraw.approved_by = str(payload.admin_telegram_id)
            db.commit()
            
            if payload.message_id:
                text = (
                    f"🟢 <b>የማውጫ ክፍያ #{withdraw.id} መፈጸሙ ተረጋግጧል!</b>\n\n"
                    f"💰 <b>የወጣው መጠን፦</b> {withdraw.amount} ETB\n"
                    f"🏦 <b>ባንክ፦</b> {withdraw.method}\n"
                    f"💳 <b>አካውንት፦</b> <code>{withdraw.wallet}</code>\n"
                    f"👮‍♂️ <b>ያጸደቀው አድሚን፦</b> {payload.admin_telegram_id}"
                )
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
            
            return {"success": True, "message": "ክፍያው መፈጸሙ ተረጋግጧል!"}

    except Exception as e:
        db.rollback()
        error_msg = f"❌ <b>ባክኤንድ ስህተት (Withdraw Approve)፦</b>\n<code>{str(e)}</code>"
        send_admin_notification(error_msg)
        return {"success": False, "message": f"Internal Server Error: {str(e)}"}
