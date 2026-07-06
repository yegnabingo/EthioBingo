from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Deposit

router = APIRouter(
    prefix="/api/deposit",
    tags=["Deposit"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 📥 1. ተጫዋቾች የገንዘብ ማስገቢያ ጥያቄ የሚልኩበት API
@router.post("/request")
def create_deposit(
    telegram_id: str,
    amount: float = Body(...),
    method: str = Body(...),         # Telebirr, CBE, ወዘተ
    phone_or_acc: str = Body(...),   # የላከበት ስልክ ቁጥር
    sms_text: str = Body(None),      # ኮፒ አድርጎ የለጠፈው የባንክ SMS
    db: Session = Depends(get_db)
):
    # ተጠቃሚውን መፈለግ
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"success": False, "message": "ተጠቃሚው አልተገኘም!"}

    # አዲሱን የዲፖዚት ጥያቄ በዳታቤዝ መመዝገብ
    new_deposit = Deposit(
        user_id=user.id,
        amount=amount,
        method=method,
        phone_or_acc=phone_or_acc,
        sms_text=sms_text,
        status="Pending"
    )

    db.add(new_deposit)
    db.commit()

    # 💡 ከዚህ በታች ያለው ኮድ በዳታቤዝ db.commit() ከተደረገ በኋላ እና ከ return በፊት ይገባል፡-
    
    # 🔔 ለአድሚን በቴሌግራም ማሳወቂያ መላክ
    try:
        BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
        ADMIN_CHAT_ID = "YOUR_PERSONAL_TELEGRAM_ID"  #
        
        # የ Approve እና Reject inline ቁልፎችን ማዘጋጀት
        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"app_wit_{new_withdraw.id}"},
                    {"text": "❌ Reject", "callback_data": f"rej_wit_{new_withdraw.id}"}
                ]
            ]
        }
        
        # ለአድሚኑ የሚላከው ዝርዝር መረጃ
        notification_text = (
            f"📤 <b>አዲስ የገንዘብ ማውጫ (Withdraw) ጥያቄ!</b>\n\n"
            f"👤 <b>ተጫዋች፦</b> {user.telegram_name or telegram_id}\n"
            f"💰 <b>የገንዘብ መጠን፦</b> {amount} ETB\n"
            f"🏦 <b>እንዲገባበት የፈለገው ባንክ፦</b> {method}\n"
            f"💳 <b>የባንክ አካውንት/ስልክ ቁጥር፦</b> <code>{wallet}</code>\n\n"
            f"⚠️ <i>ማሳሰቢያ፦ እባክዎ መጀመሪያ ወደ ተጫዋቹ አካውንት ብሩን መላክዎን ያረጋግጡና ከዚያ 'Approve' የሚለውን ይጫኑ!</i>"
        )
        
        import requests
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(telegram_url, json={
            "chat_id": ADMIN_CHAT_ID,
            "text": notification_text,
            "parse_mode": "HTML",
            "reply_markup": inline_keyboard
        })
    except Exception as e:
        print(f"ለአድሚን የቴሌግራም መልዕክት መላክ አልተቻለም፦ {str(e)}")

    return {
        "success": True,
        "message": "የገንዘብ ማስገቢያ ጥያቄዎ ለአስተዳዳሪው ተልኳል፣ በትዕግስት ይጠብቁ!"
    }


# 🛠️ 2. አድሚኑ ጥያቄውን አይቶ Approve ወይም Reject የሚያደርግበት API
@router.post("/admin/approve")
def admin_approve_deposit(
    deposit_id: int = Body(...),
    action: str = Body(...),         # 'APPROVE' ወይም 'REJECT'
    admin_telegram_id: str = Body(...),
    db: Session = Depends(get_db)
):
    # መጀመሪያ አድሚኑ እውነተኛ አድሚን መሆኑን ማረጋገጥ
    admin_user = db.query(User).filter(User.telegram_id == admin_telegram_id).first()
    if not admin_user or not admin_user.is_admin:
        return {"success": False, "message": "ይህንን ለማድረግ ፈቃድ የለዎትም!"}

    # የዲፖዚት ጥያቄውን መፈለግ
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id).first()
    if not deposit:
        return {"success": False, "message": "የዲፖዚት ጥያቄው አልተገኘም!"}

    if deposit.status != "Pending":
        return {"success": False, "message": f"ይህ ጥያቄ አስቀድሞ {deposit.status} ሆኗል!"}

    # ጥያቄውን የላከውን ተጫዋች መፈለግ
    player = db.query(User).filter(User.id == deposit.user_id).first()
    if not player:
        return {"success": False, "message": "ጥያቄውን የላከው ተጫዋች አልተገኘም!"}

    if action == "APPROVE":
        deposit.status = "Approved"
        deposit.approved_by = admin_user.telegram_name or admin_telegram_id
        
        # 🪙 [ዋናው ህግ] የተጫዋቹን የገንዘብ መጠን (Balance) መጨመር
        player.balance += deposit.amount
        db.commit()
        
        # 💡 [ማስታወሻ] እዚህ ጋር ለተጫዋቹ በቴሌግራም ቦት "ብርዎ ገብቷል" የሚል መልዕክት መላክ ይቻላል።
        return {"success": True, "message": f"የ {deposit.amount} ብር ማስገቢያ ጥያቄ በተሳካ ሁኔታ ጸድቋል!"}

    elif action == "REJECT":
        deposit.status = "Rejected"
        deposit.approved_by = admin_user.telegram_name or admin_telegram_id
        db.commit()
        return {"success": True, "message": "የገንዘብ ማስገቢያ ጥያቄው ውድቅ ተደርጓል!"}

    return {"success": False, "message": "የማይታወቅ ትዕዛዝ!"}
