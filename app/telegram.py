import os
import sys
import requests
import threading  # 💡 የባክኤንድ ጥያቄ ቦቱን Freeze እንዳያደርገው በThread ለማሰራት
from datetime import datetime
from telebot import TeleBot, types

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (ቀጥተኛ እና አስተማማኝ)
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")

# 🔗 የባክኤንድ አድራሻ
SERVER_URL = os.getenv("SERVER_URL", "https://web-production-fd82a.up.railway.app").rstrip('/')
BACKEND_URL = SERVER_URL
MINI_APP_URL = SERVER_URL

# 🖼️ የማቀባበያ ምስል ሊንክ (የ Yegna Bingo ሎጎ ወይም የምስሉ URL)
WELCOME_IMAGE_URL = f"{MINI_APP_URL}/static/images/welcome.png"

bot = TeleBot(BOT_TOKEN)

print(f"🎰 የYegnaኛ Bingo ቦት (@{BOT_USERNAME}) በሰላም ስራ ጀምሯል...")
print("TELEGRAM MODULE LOADED")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    # 🎮 የ ሚኒ አፕ (WebApp) ቁልፍ ብቻ መፍጠሪያ (ሌሎቹ በተኖች በሙሉ ፀድተዋል)
    markup = types.InlineKeyboardMarkup()
    btn_play = types.InlineKeyboardButton(text="🎮 Play Bingo (ተጫወት)", web_app=types.WebAppInfo(url=MINI_APP_URL))
    markup.add(btn_play)

    # 📝 ማራኪ የሰላምታ ጽሑፍ
    welcome_text = (
        f"👋 ሰላም {user_name}፣ ወደ <b>የኛ ቢንጎ (Yegna Bingo)</b> እንኳን በደህና መጡ! 🎉\n\n"
        "ኢትዮጵያ ውስጥ ምርጡን የቢንጎ ጨዋታ በቴሌግራም ሚኒ አፕ በቀላሉ ይጫወቱ። "
        "ገንዘብ ማስገባት፣ ማውጣት እና የደራሽ (Jackpot) ሽልማቶችን በሙሉ እውስጥ ያገኛሉ! 💰"
    )

    try:
        # 🖼️ መጀመሪያ ምስሉን ከጽሑፉ እና ከበተኑ ጋር አንድ ላይ ይልካል
        bot.send_photo(
            chat_id, 
            photo=WELCOME_IMAGE_URL, 
            caption=welcome_text, 
            parse_mode="HTML", 
            reply_markup=markup
        )
    except Exception as e:
        # ምስሉ ስታቲክ ላይ ባይገኝ እንኳ ቦቱ እንዳይቆም በጽሑፍ ብቻ ይልካል
        print(f"⚠️ የሰላምታ ምስል መላክ አልተቻለም፦ {e}")
        bot.send_message(chat_id, welcome_text, parse_mode="HTML", reply_markup=markup)


# 🛠️ ማስተካከያ ሎጂክ ለባክኤንድ ጥያቄ (Thread ውስጥ የሚሮጥ)
def send_admin_action_to_backend(call, url, payload, headers, target_id, action, tx_type):
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"📊 Response Status: {response.status_code}")
        
        try:
            res_data = response.json()
        except:
            res_data = {"success": False, "message": response.text}

        if response.status_code == 200 and res_data.get("success"):
            print(f"✅ Action successfully handled by backend for ID #{target_id}")
            
            label = "Deposit" if tx_type == "dep" else "Withdrawal"
            alert_text = f"✅ {label} #{target_id} approved successfully!" if action == "approve" else f"❌ {label} #{target_id} rejected & balance refunded"
            try:
                bot.answer_callback_query(call.id, text=alert_text, show_alert=True)
            except:
                pass
            
            status_emoji = "✅" if action == "approve" else "❌"
            status_text = "APPROVED" if action == "approve" else "REJECTED"
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
            
            new_text = f"{call.message.text}\n\n{status_emoji} <b>{status_text} at {current_time} UTC</b>"
            
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=new_text,
                    parse_mode="HTML",
                    reply_markup=None  # ቁልፎቹን ያጠፋል
                )
            except Exception as edit_err:
                print(f"⚠️ Telegram message edit minor issue: {edit_err}")
                
        else:
            error_detail = res_data.get('message', f'HTTP Error {response.status_code}')
            try:
                bot.answer_callback_query(call.id, text=f"❌ ስህተት (ባክኤንድ)፦ {error_detail}", show_alert=True)
            except:
                pass
    except Exception as e:
        print("Admin Action Error:", e)
        try:
            bot.answer_callback_query(call.id, text="⚠️ ከባክኤንድ ሰርቨር ጋር መገናኘት አልተቻለም።", show_alert=True)
        except:
            pass


# 🛠️ የአድሚን ማፅደቂያ/መሰረዣ ቁልፎች (ይህ እንዳለ ይቀጥላል)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_dep_', 'reject_dep_', 'approve_with_', 'reject_with_')))
def handle_admin_actions(call):
    try:
        bot.answer_callback_query(callback_query_id=call.id, text="⏳ ውሳኔዎ በሂደት ላይ ነው...")
    except:
        pass
    
    admin_id_str = str(call.from_user.id).strip()
    action_data = call.data.split('_')
    action = action_data[0]    # 'approve' ወይም 'reject'
    tx_type = action_data[1]   # 'dep' ወይም 'with'
    target_id = int(action_data[2])

    if tx_type == "dep":
        backend_action = "APPROVE" if action == "approve" else "REJECT"
        url = f"{BACKEND_URL}/api/deposit/admin/approve"
        payload = {
            "deposit_id": target_id, 
            "action": backend_action,
            "admin_telegram_id": admin_id_str,
            "message_id": call.message.message_id,
            "admin_password": ADMIN_PASSWORD
        }
    else:
        backend_action = "APPROVE" if action == "approve" else "REJECT"
        url = f"{BACKEND_URL}/api/withdraw/admin/approve"
        payload = {
            "withdraw_id": target_id, 
            "action": backend_action,
            "admin_telegram_id": admin_id_str,
            "message_id": call.message.message_id,
            "admin_password": ADMIN_PASSWORD
        }

    headers = {"Content-Type": "application/json"}
    print(f"📡 Requesting: {url}")
    
    threading.Thread(
        target=send_admin_action_to_backend, 
        args=(call, url, payload, headers, target_id, action, tx_type),
        daemon=True
    ).start()

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
