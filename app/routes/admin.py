from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests

from app.database import SessionLocal
from app.models import User, Deposit, Withdrawal  # 👈 በዳታቤዝህ መሠረት Withdrawal መባሉ ተጠብቋል

router = APIRouter(
    prefix="/api",
    tags=["Wallet & Admin Integrated System"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------------------------------
# ⚙️ የቴሌግራም ቦት ቅንብሮች (እባክህ የራስህን ትክክለኛ መረጃ እዚህ ተካ)
# --------------------------------------------------------------------------
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_CHAT_ID = "YOUR_PERSONAL_TELEGRAM_ID"

# --------------------------------------------------------------------------
# 📝 የፒዳንቲክ (Pydantic) የጥያቄ መቀበያ ሞዴሎች
# --------------------------------------------------------------------------
class MiniAppDepositRequest(BaseModel):
    telegram_id: str
    telegram_name: str
    sms_data: str

class MiniAppWithdrawRequest(BaseModel):
    telegram_id: str
    amount: float
    bank_name: str
    account_number: str

class AdminActionPayload(BaseModel):
    deposit_id: int = None
    withdraw_id: int = None
    action: str  # "APPROVE" ወይም "REJECT"
    admin_telegram_id: str

# --------------------------------------------------------------------------
# 📥 1. ከሚኒ አፕ የዲፖዚት (SMS) ጥያቄ መቀበያ (User Side)
# --------------------------------------------------------------------------
@router.post("/wallet/deposit")
def user_submit_deposit(payload: MiniAppDepositRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if not user:
        return {"success": False, "message": "ተጠቃሚው አልተገኘም!"}

    # በድሮው የዳታቤዝ አወቃቀርህ መሠረት Columns ሳይዛቡ መመዝገብ
    new_deposit = Deposit(
        user_id=user.id,
        amount=0.0,  # አድሚኑ SMS አይቶ በትክክለኛው መጠን ያጸድቀዋል
        method="Auto-Detect",
        phone_or_acc="Mini-App",
        sms_text=payload.sms_data, # የድሮው ኮለም ስም ተጠብቋል
        status="Pending"
    )
    db.add(new_deposit)
    db.commit()
    db.refresh(new_deposit)

    # 🔔 ለአድሚን በቴሌግራም የቁልፍ ማሳወቂያ መላክ
    try:
        inline_keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"app_dep_{new_deposit.id}"},
                {"text": "❌ Reject", "callback_data": f"rej_dep_{new_deposit.id}"}
            ]]
        }
        notification_text = (
            f"📥 <b>አዲስ የገንዘብ ማስገቢያ (Deposit) ጥያቄ!</b>\n\n"
            f"👤 <b>ተጫዋች፦</b> {payload.telegram_name} (<code>{payload.telegram_id}</code>)\n"
            f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_deposit.id}\n\n"
            f"📝 <b>የተላከው የባንክ SMS፦</b>\n<code>{payload.sms_data}</code>\n\n"
            f"⚠️ <i>እባክዎ መረጃውን በባንክዎ አይተው ካረጋገጡ በኋላ ይፍቀዱ!</i>"
        )
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": ADMIN_CHAT_ID, "text": notification_text, "parse_mode": "HTML", "reply_markup": inline_keyboard
        })
    except Exception as e:
        print(f"የቴሌግራም ማሳወቂያ ስህተት፦ {str(e)}")

    return {"success": True, "message": "የገንዘብ ማስገቢያ ጥያቄዎ ለአስተዳዳሪው ተልኳል!"}

# 📤 2. ከሚኒ አፕ የዊዝድሮው (ብር ማውጫ) ጥያቄ መቀበያ (User Side)
# --------------------------------------------------------------------------
@router.post("/wallet/withdraw")
def user_submit_withdraw(payload: MiniAppWithdrawRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if not user:
        return {"success": False, "message": "ተጠቃሚው አልተገኘም!"}

    if user.balance < payload.amount:
        return {"success": False, "message": "በቂ ቀሪ ሂሳብ (Balance) የለዎትም!"}

    # 🔒 የደህንነት ህግ፡ ብሩን ወዲያውኑ ሆልድ (Hold) ማድረግ
    user.balance -= payload.amount

    # በድሮው የዳታቤዝ አወቃቀርህ (Withdrawal) መሠረት መመዝገብ
    new_withdraw = Withdrawal(
        user_id=user.id,
        amount=payload.amount,
        method=payload.bank_name,
        wallet=payload.account_number, # የድሮው ኮለም ስም ተጠብቋል
        status="Pending"
    )
    db.add(new_withdraw)
    db.commit()
    db.refresh(new_withdraw)

    # 🔔 ለአድሚን በቴሌግራም የቁልፍ ማሳወቂያ መላክ
    try:
        inline_keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"app_wit_{new_withdraw.id}"},
                {"text": "❌ Reject", "callback_data": f"rej_wit_{new_withdraw.id}"}
            ]]
        }
        notification_text = (
            f"📤 <b>አዲስ የገንዘብ ማውጫ (Withdraw) ጥያቄ!</b>\n\n"
            f"👤 <b>ተጫዋች፦</b> {user.telegram_name or payload.telegram_id}\n"
            f"💰 <b>የገንዘብ መጠን፦</b> {payload.amount} ETB\n"
            f"🏦 <b>ባንክ፦</b> {payload.bank_name}\n"
            f"💳 <b>የባንክ አካውንት/ስልክ ቁጥር፦</b> <code>{payload.account_number}</code>\n\n"
            f"⚠️ <i>ማሳሰቢያ፦ መጀመሪያ ብሩን ለተጫዋቹ መላክዎን ያረጋግጡና ከዚያ 'Approve' ይበሉ!</i>"
        )
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": ADMIN_CHAT_ID, "text": notification_text, "parse_mode": "HTML", "reply_markup": inline_keyboard
        })
    except Exception as e:
        print(f"የቴሌግራም ማሳወቂያ ስህተት፦ {str(e)}")

    return {"success": True, "message": "የገንዘብ ማውጫ ጥያቄዎ ለአስተዳዳሪው ተልኳል!"}

# 👮‍♂️ 3. አድሚኑ ቦት ላይ APPROVE/REJECT ሲጫን (Admin Deposit Side)
# --------------------------------------------------------------------------
@router.post("/deposit/admin/approve")
def approve_deposit(payload: AdminActionPayload, db: Session = Depends(get_db)):
    deposit = db.query(Deposit).filter(Deposit.id == payload.deposit_id).first()
    if not deposit: return {"success": False, "message": "Deposit not found"}
    if deposit.status != "Pending": return {"success": False, "message": "Already processed"}

    user = db.query(User).filter(User.id == deposit.user_id).first()
    if not user: return {"success": False, "message": "User not found"}

    if payload.action == "APPROVE":
        deposit.status = "Approved"
        user.balance += deposit.amount
    else:
        deposit.status = "Rejected"
    
    db.commit()
    return {"success": True, "message": f"Deposit {payload.action} successfully"}

# 👮‍♂️ 4. አድሚኑ ቦት ላይ APPROVE/REJECT ሲጫን (Admin Withdraw Side)
# --------------------------------------------------------------------------
@router.post("/withdraw/admin/approve")
def approve_withdraw(payload: AdminActionPayload, db: Session = Depends(get_db)):
    withdraw = db.query(Withdrawal).filter(Withdrawal.id == payload.withdraw_id).first()
    if not withdraw: return {"success": False, "message": "Withdraw request not found"}
    if withdraw.status != "Pending": return {"success": False, "message": "Already processed"}

    user = db.query(User).filter(User.id == withdraw.user_id).first()

    if payload.action == "APPROVE":
        withdraw.status = "Approved"
    else:
        withdraw.status = "Rejected"
        if user: user.balance += withdraw.amount # ውድቅ ከተደረገ ብሩን መመለስ

    db.commit()
    return {"success": True, "message": f"Withdrawal {payload.action} successfully"}
