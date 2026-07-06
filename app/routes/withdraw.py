from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Withdrawal

router = APIRouter(
    prefix="/api/withdraw",
    tags=["Withdraw"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 📤 1. ተጫዋቾች የገንዘብ ማውጫ ጥያቄ የሚልኩበት API
@router.post("/request")
def create_withdraw(
    telegram_id: str,
    amount: float = Body(...),
    method: str = Body(...),   # Telebirr, CBE, Commercial Bank, ወዘተ
    wallet: str = Body(...),   # ብሩ የሚገባበት የአካውንት ወይም የስልክ ቁጥር
    db: Session = Depends(get_db)
):
    # ተጠቃሚውን መፈለግ
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"success": False, "message": "ተጠቃሚው አልተገኘም!"}

    # የገንዘብ መጠን ማረጋገጥ
    if user.balance < amount:
        return {"success": False, "message": "በቂ ቀሪ ሂሳብ (Balance) የለዎትም!"}

    # 🔒 የደህንነት ህግ፡ ተጫዋቹ ጥያቄ ሲልክ ማውጣት የፈለገውን ብር ከዋሌቱ ላይ ወዲያውኑ እንቀንሳለን
    # ይህ የሚደረገው ጥያቄው Pending እያለ ያንን ብር ደግሞ ሌላ ጨዋታ ላይ እንዳይጫወትበት ለመከላከል ነው
    user.balance -= amount

    # አዲሱን የዊዝድሮው ጥያቄ መመዝገብ
    new_withdraw = Withdrawal(
        user_id=user.id,
        amount=amount,
        method=method,
        wallet=wallet,
        status="Pending"
    )

    db.add(new_withdraw)
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
        "message": "የገንዘብ ማውጫ ጥያቄዎ ለአስተዳዳሪው ተልኳል፣ በአጭር ጊዜ ውስጥ ይስተናገዳል!"
    }


# 🛠️ 2. አድሚኑ የዊዝድሮው ጥያቄውን አይቶ Approve ወይም Reject የሚያደርግበት API
@router.post("/admin/approve")
def admin_approve_withdrawal(
    withdraw_id: int = Body(...),
    action: str = Body(...),         # 'APPROVE' ወይም 'REJECT'
    admin_telegram_id: str = Body(...),
    db: Session = Depends(get_db)
):
    # አድሚኑን ማረጋገጥ
    admin_user = db.query(User).filter(User.telegram_id == admin_telegram_id).first()
    if not admin_user or not admin_user.is_admin:
        return {"success": False, "message": "ይህንን ለማድረግ ፈቃድ የለዎትም!"}

    # የዊዝድሮው ጥያቄውን መፈለግ
    withdraw = db.query(Withdrawal).filter(Withdrawal.id == withdraw_id).first()
    if not withdraw:
        return {"success": False, "message": "የዊዝድሮው ጥያቄው አልተገኘም!"}

    if withdraw.status != "Pending":
        return {"success": False, "message": f"ይህ ጥያቄ አስቀድሞ {withdraw.status} ሆኗል!"}

    # ተጫዋቹን መፈለግ
    player = db.query(User).filter(User.id == withdraw.user_id).first()
    if not player:
        return {"success": False, "message": "ጥያቄውን የላከው ተጫዋች አልተገኘም!"}

    if action == "APPROVE":
        # አድሚኑ በባንክ ብሩን መላኩን አረጋግጦ ሲያጸድቀው ስታተሱን እናድሳለን
        withdraw.status = "Approved"
        withdraw.approved_by = admin_user.telegram_name or admin_telegram_id
        db.commit()
        
        # 💡 [ማስታወሻ] ለተጫዋቹ በቦት "የማውጫ ጥያቄዎ ጸድቋል፣ ባንክዎን ያረጋግጡ" ማለት ይቻላል።
        return {"success": True, "message": "የገንዘብ ማውጫ ጥያቄው በተሳካ ሁኔታ ጸድቋል!"}

    elif action == "REJECT":
        withdraw.status = "Rejected"
        withdraw.approved_by = admin_user.telegram_name or admin_telegram_id
        
        # 🪙 [ዋናው የደህንነት ህግ] ጥያቄው ውድቅ ከተደረገ፣ ተቀንሶ የነበረውን ብር መልሰን ለተጫዋቹ ዋሌት እንጨምራለን
        player.balance += withdraw.amount
        db.commit()
        
        return {"success": True, "message": "የገንዘብ ማውጫ ጥያቄው ውድቅ ተደርጓል፣ ብሩ ወደ ተጫዋቹ ተመልሷል!"}

    return {"success": False, "message": "የማይታወቅ ትዕዛዝ!"}
