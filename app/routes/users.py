import os
import requests
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional

from app.database import SessionLocal
from app.models import User, Deposit, Withdrawal, Game, DailyCheckIn, PlayerCard
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
    id: Optional[int] = None
    deposit_id: Optional[int] = None
    withdraw_id: Optional[int] = None
    action: str
    admin_telegram_id: Optional[str] = None  
    admin_id: Optional[str] = None           
    message_id: Optional[int] = None
    admin_password: Optional[str] = None


# 👤 1. የተጫዋች ፕሮፋይል መረጃ ማሳያ API (Profile Modal)
@router.get("/users/profile/{telegram_id}")
def get_user_profile(telegram_id: str, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")
    
    return {
        "success": True,
        "profile": {
            "telegram_id": user.telegram_id,
            "telegram_name": user.telegram_name or user.first_name or f"User_{user.id}",
            "balance": getattr(user, "balance", 0.0) or 0.0,
            "gift_coin": getattr(user, "gift_coin", 0.0) or 0.0,
            "total_games_played": getattr(user, "total_games_played", 0) or 0,
            "total_games_won": getattr(user, "total_games_won", 0) or 0,
            "total_winnings": getattr(user, "total_winnings", 0.0) or 0.0,
            "weekly_games_played": getattr(user, "weekly_games_played", 0) or 0,
            "weekly_deposit_amount": getattr(user, "weekly_deposit_amount", 0.0) or 0.0
        }
    }


# 🏆 2. የሳምንቱ ምርጥ ተጫዋቾች የደረጃ ሰንጠረዥ (Leaderboard API)
@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    # በሳምንቱ ብዙ ካርድ የተጫወቱትን በቅደም ተከተል ያወጣል
    top_players = db.query(User).order_by(
        User.weekly_games_played.desc(),
        User.weekly_deposit_amount.desc()
    ).limit(10).all()

    leaderboard_data = []
    for rank, player in enumerate(top_players, 1):
        leaderboard_data.append({
            "rank": rank,
            "telegram_name": player.telegram_name or player.first_name or f"User_{player.id}",
            "weekly_games": getattr(player, "weekly_games_played", 0) or 0,
            "weekly_deposits": getattr(player, "weekly_deposit_amount", 0.0) or 0.0
        })

    return {"success": True, "leaderboard": leaderboard_data}


# 🎁 3. የሳምንታዊ ልዩ ሽልማት መረጃ (Bonus Info API)
@router.get("/bonus/info/{telegram_id}")
def get_bonus_info(telegram_id: str, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    
    user_rank = "አልተመደቡም"
    user_weekly_games = 0
    
    if user:
        user_weekly_games = getattr(user, "weekly_games_played", 0) or 0
        # የተጫዋቹን የራሱን ሳምንታዊ ደረጃ ማስላት
        higher_players = db.query(User).filter(
            User.weekly_games_played > user_weekly_games
        ).count()
        user_rank = f"{higher_players + 1}ኛ"

    return {
        "success": True,
        "bonus_info": {
            "title": "🎁 ሳምንታዊ የልዩ ሽልማት ውድድር",
            "description": "በየሳምንቱ ብዙ ካርዶችን በመግዛት ከ 1 እስከ 3 ለወጡ ተጫዋቾች የሚሰጥ ልዩ የገንዘብ ሽልማት!",
            "prizes": [
                {"rank": "1ኛ የወጣ", "reward": "500 ETB"},
                {"rank": "2ኛ የወጣ", "reward": "300 ETB"},
                {"rank": "3ኛ የወጣ", "reward": "150 ETB"}
            ],
            "user_current_rank": user_rank,
            "user_weekly_games": user_weekly_games
        }
    }


# 📥 4. አዲስ ተጫዋች ሲመዘገብ
@router.post("/users/register")
def register_user(telegram_id: str, telegram_name: str = None, first_name: str = None, referred_by: str = None, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    if not tg_id_str.isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    existing = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if existing:
        user_balance = getattr(existing, "balance", 0.0) or 0.0
        return {
            "success": True, "message": "ተጠቃሚው አስቀድሞ ተመዝግቧል",
            "user": {
                "telegram_id": existing.telegram_id, 
                "balance": user_balance, 
                "wallet": user_balance,
                "gift_coin": getattr(existing, "gift_coin", 0.0) or 0.0
            }
        }
    
    ref_id_str = None
    if referred_by and str(referred_by).strip().isdigit():
        ref_id_str = str(referred_by).strip()
        if ref_id_str == tg_id_str:
            ref_id_str = None

    new_user = User(
        telegram_id=tg_id_str, 
        telegram_name=telegram_name, 
        first_name=first_name, 
        wallet=0.0, 
        balance=0.0,   
        gift_coin=0.0, 
        referred_by=ref_id_str,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    if ref_id_str:
        referrer = db.query(User).filter(User.telegram_id == ref_id_str).first()
        if referrer:
            referrer.gift_coin = (referrer.gift_coin or 0.0) + 2.0
            db.commit()
            print(f"🎉 Referral Bonus! User {ref_id_str} received 2.0 ETB bonus for inviting {tg_id_str}")
    
    return {
        "success": True, 
        "message": "ምዝገባው በተሳካ ሁኔታ ተጠናቋል", 
        "user": {
            "telegram_id": new_user.telegram_id, 
            "balance": 0.0,
            "wallet": 0.0,
            "gift_coin": new_user.gift_coin
        }
    }


# 🎁 5. የዕለታዊ ስጦታ መውሰጃ API (Daily Check-in)
@router.post("/users/daily-checkin")
def user_daily_checkin(telegram_id: str, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")
        
    today_date = date.today()
    
    already_checked = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user.id, 
        DailyCheckIn.checked_date == today_date
    ).first()
    
    if already_checked:
        return {
            "success": False, 
            "message": "⚠️ የዛሬውን የስጦታ መጫወቻዎን ቀድመው ወስደዋል! እባክዎ ነገ በድጋሚ ይመለሱ።",
            "gift_coin": user.gift_coin
        }
        
    user.gift_coin = (user.gift_coin or 0.0) + 10.0
    new_checkin = DailyCheckIn(user_id=user.id, checked_date=today_date)
    db.add(new_checkin)
    db.commit()
    
    return {
        "success": True, 
        "message": "🎉 የ 10 ETB እለታዊ ነፃ መጫወቻ ስጦታዎን በተሳካ ሁኔታ ወስደዋል!", 
        "gift_coin": user.gift_coin
    }


# 🔍 6. የተጫዋቹን የዋሌት መረጃ መፈተሻ API
@router.get("/users/{telegram_id}")
def get_user(telegram_id: str, db: Session = Depends(get_db)):
    tg_id_str = str(telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {
            "success": False, 
            "user": {"telegram_id": tg_id_str, "balance": 0.0, "wallet": 0.0, "gift_coin": 0.0}
        }
        
    user_balance = getattr(user, "balance", 0.0) or 0.0
    return {
        "success": True, 
        "user": {
            "telegram_id": user.telegram_id, 
            "balance": user_balance, 
            "wallet": user_balance,
            "gift_coin": getattr(user, "gift_coin", 0.0) or 0.0
        }
    }


# 💰 7. ተጫዋች ከሚኒ አፕ ላይ ዲፖዚት ሲያደርግ
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
            status="pending",
            created_at=datetime.utcnow(),
            telegram_id=tg_id_str,
            telegram_name=req.telegram_name if req.telegram_name else "ተጫዋች",
            wallet=str(user.balance)  
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
            {"text": "✅ APPROVED (አጽድቅ)", "callback_data": f"approve_dep_{new_deposit.id}"},
            {"text": "❌ REJECTED (ሰርዝ)", "callback_data": f"reject_dep_{new_deposit.id}"}
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


# 📤 8. ተጫዋች ከሚኒ አፕ ላይ ዊዝድሮው ሲያደርግ
@router.post("/users/withdraw")
def user_withdraw_request(req: WithdrawCreate, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    if not tg_id_str.isdigit():
        return {"success": False, "message": "Invalid Telegram ID."}
    
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {"success": False, "message": "User not found. Please register first."}

    has_approved_deposit = db.query(Deposit).filter(
        Deposit.user_id == user.id,
        Deposit.status == "approved"
    ).first()

    if not has_approved_deposit:
        return {
            "success": False, 
            "message": "⚠️ ያሸነፉትን ብር ለማውጣት (Withdraw) ለማድረግ፡ መጀመሪያ ቢያንስ 1 ጊዜ Deposit ማድረግ አለብዎት!"
        }

    user_balance = getattr(user, "balance", 0.0) or 0.0
    if user_balance < req.amount:
        return {"success": False, "message": f"ይቅርታ፣ በቂ ባላንስ የሎትም! ያሎት ባላንስ {user_balance} ETB ነው።"}

    try:
        user.balance = user_balance - req.amount
        user.wallet = user.balance
        
        new_withdraw = Withdrawal(
            user_id=user.id,
            amount=req.amount,
            method=req.bank_name,     
            wallet=str(req.account_number), 
            status="pending",
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
            {"text": "✅ APPROVED (ከፍያለሁ)", "callback_data": f"approve_with_{new_withdraw.id}"},
            {"text": "❌ REJECTED (ሰርዝ)", "callback_data": f"reject_with_{new_withdraw.id}"}
        ]]
    }

    msg_text = (
        f"⚠️ <b>አዲስ የገንዘብ ማውጫ ጥያቄ!</b>\n\n"
        f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_withdraw.id}\n"
        f"👤 ተጫዋች ID፦ {tg_id_str}\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💳 የባንክ አካውንት፦ <code>{req.account_number}</code>\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>\n\n"
        f"<i>ይህንን ብር በባንክ ልከው ሲያበቁ 'Paid' የሚለውን ይጫኑ።</i>"
    )

    send_admin_notification(msg_text, reply_markup=inline_keyboard)
    return {"success": True, "message": "የማውጫ ጥያቄዎ ተመዝግቧል!"}


# 👮‍♂️ 9. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ (Deposit - ዲፖዚት ሲጸድቅ ቆጣሪዎችን ይጨምራል)
@router.post("/deposit/admin/approve")
def admin_approve_deposit(payload: AdminAction, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        active_admin_id = payload.admin_telegram_id or payload.admin_id or "Admin"
        
        target_id = payload.id or payload.deposit_id
        if not target_id:
            return {"success": False, "message": "የዲፖዚት ID አልተላከም!"}

        deposit = db.query(Deposit).filter(Deposit.id == target_id).first()
        if not deposit: 
            return {"success": False, "message": f"የዲፖዚት ጥያቄ #{target_id} በዳታቤዝ ውስጥ አልተገኘም!"}
        
        if deposit.status.lower() != "pending": 
            return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል (Pending አይደለም)!"}

        user = None
        if deposit.user_id:
            user = db.query(User).filter(User.id == deposit.user_id).first()
        elif deposit.telegram_id:
            user = db.query(User).filter(User.telegram_id == str(deposit.telegram_id)).first()

        if not user: 
            return {"success": False, "message": "ይህንን ጥያቄ የላከው ተጫዋች አልተገኘም!"}

        action_upper = payload.action.upper()
        if action_upper in ["APPROVE", "APPROVED"]:
            current_balance = getattr(user, "balance", 0.0) or 0.0
            user.balance = current_balance + deposit.amount
            user.wallet = user.balance
            
            # 🎯 🔴 አዲስ የተጨመረ፦ የሳምንቱን ዲፖዚት መጠን መቁጠሪያ
            user.weekly_deposit_amount = (getattr(user, "weekly_deposit_amount", 0.0) or 0.0) + deposit.amount
            
            deposit.status = "approved"
            deposit.approved_by = str(active_admin_id)
            db.commit()
            
            if payload.message_id:
                text = (
                    f"🟢 <b>የዲፖዚት ጥያቄ #{deposit.id} ጸድቋል!</b>\n\n"
                    f"💰 <b>የተጨመረው መጠን፦</b> {deposit.amount} ETB\n"
                    f"👤 <b>ተጫዋች ID፦</b> <code>{user.telegram_id}</code>\n"
                    f"🏦 <b>ባንክ፦</b> {deposit.method}\n"
                    f"👮‍♂️ <b>ያጸደቀው አድሚን፦</b> {active_admin_id}"
                )
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
                
            return {"success": True, "message": "ዲፖዚቱ በተሳካ ሁኔታ ጸድቋል!"}
        
        else:
            deposit.status = "rejected"
            deposit.approved_by = str(active_admin_id)
            db.commit()
            
            if payload.message_id:
                text = f"🔴 <b>የዲፖዚት ጥያቄ #{deposit.id} ውድቅ ተደርጓል!</b>\n👮‍♂️ <b>የሰረዘው አድሚን፦</b> {active_admin_id}"
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
                
            return {"success": True, "message": "ጥያቄው ውድቅ ተደርጓል!"}

    except Exception as e:
        db.rollback()
        error_msg = f"❌ <b>ባክኤንድ ስህተት (Deposit Approved)፦</b>\n<code>{str(e)}</code>"
        send_admin_notification(error_msg)
        return {"success": False, "message": f"Internal Server Error: {str(e)}"}


# 👮‍♂️ 10. አድሚኑ ከቴሌግራም ላይ APPROVE/REJECT ሲያደርግ (Withdraw)
@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: AdminAction, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        active_admin_id = payload.admin_telegram_id or payload.admin_id or "Admin"

        target_id = payload.id or payload.withdraw_id
        if not target_id:
            return {"success": False, "message": "የዊዝድሮው ID አልተላከም!"}

        withdraw = db.query(Withdrawal).filter(Withdrawal.id == target_id).first()
        if not withdraw: 
            return {"success": False, "message": f"የማውጫ ጥያቄ #{target_id} በዳታቤዝ ውስጥ አልተገኘም!"}
        
        if withdraw.status.lower() != "pending": 
            return {"success": False, "message": "ይህ ጥያቄ ቀድሞ ውሳኔ አግኝቷል!"}

        user = db.query(User).filter(User.id == withdraw.user_id).first()
        if not user: 
            return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

        action_upper = payload.action.upper()
        if action_upper in ["REJECT", "REJECTED"]:
            current_balance = getattr(user, "balance", 0.0) or 0.0
            user.balance = current_balance + withdraw.amount
            user.wallet = user.balance
            
            withdraw.status = "rejected"
            withdraw.approved_by = str(active_admin_id)
            db.commit()
                 
            if payload.message_id:
                text = (
                    f"🔴 <b>የማውጫ ጥያቄ #{withdraw.id} ተሰርዟል!</b>\n\n"
                    f"💰 <b>የተመለሰው መጠን፦</b> {withdraw.amount} ETB\n"
                    f"👤 <b>ተጫዋች ID፦</b> <code>{user.telegram_id}</code>\n"
                    f"👮‍♂️ <b>የሰረዘው አድሚን፦</b> {active_admin_id}"
                )
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
                
            return {"success": True, "message": "የማውጫ ጥያቄው ውድቅ ተደርጎ ብሩ ተመልሷል!"}
        
        else:
            withdraw.status = "approved"
            withdraw.approved_by = str(active_admin_id)
            db.commit()
            
            if payload.message_id:
                text = (
                    f"🟢 <b>የማውጫ ክፍያ #{withdraw.id} መፈጸሙ ተረጋግጧል!</b>\n\n"
                    f"💰 <b>የወጣው መጠን፦</b> {withdraw.amount} ETB\n"
                    f"🏦 <b>ባንክ፦</b> {withdraw.method}\n"
                    f"💳 <b>አካውንት፦</b> <code>{withdraw.wallet}</code>\n"
                    f"👮‍♂️ <b>ያጸደቀው አድሚን፦</b> {active_admin_id}"
                )
                background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, payload.message_id, text)
            
            return {"success": True, "message": "ክፍያው መፈጸሙ ተረጋግጧል!"}

    except Exception as e:
        db.rollback()
        error_msg = f"❌ <b>ባክኤንድ ስህተት (Withdraw Approved)፦</b>\n<code>{str(e)}</code>"
        send_admin_notification(error_msg)
        return {"success": False, "message": f"Internal Server Error: {str(e)}"}
