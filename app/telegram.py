import os
import sys
import requests
import threading  # 💡 የባክኤንድ ጥያቄ ቦቱን Freeze እንዳያደርገው በThread ለማሰራት
from datetime import datetime
from telebot import TeleBot, types

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (Railway ላይ ከተጫኑት Variables ብቻ የሚያነቡ)
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip().replace("@", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")

# 🔗 የባክኤንድ አድራሻ (ሁሉም ከ SERVER_URL ተነስተው በVariable ብቻ ይሰራሉ)
SERVER_URL = os.getenv("SERVER_URL", "https://web-production-fd82a.up.railway.app").rstrip('/')
BACKEND_URL = SERVER_URL
MINI_APP_URL = SERVER_URL

# 🖼️ የማቀባበያ ምስል ሊንክ
WELCOME_IMAGE_URL = f"https://web-production-fd82a.up.railway.app/static/images/welcome.png"

bot = TeleBot(BOT_TOKEN)

print(f"🎰 የYegnaኛ Bingo ቦት (@{BOT_USERNAME}) በሰላም ስራ ጀምሯል...")
print("TELEGRAM MODULE LOADED")


# 👥 ጀርባ ላይ አዲስ ተጫዋች በሪፈራል ጭምር የሚመዘግብ የ Thread ተግባር
def register_user_background(telegram_id, telegram_name, first_name, referred_by=None):
    register_api_url = f"{BACKEND_URL}/api/users/register"
    params = {
        "telegram_id": str(telegram_id),
        "telegram_name": telegram_name,
        "first_name": first_name
    }
    if referred_by:
        params["referred_by"] = str(referred_by)
        
    try:
        response = requests.post(register_api_url, params=params, timeout=10)
        print(f"📡 Backend Register Response: {response.json()}")
    except Exception as e:
        print(f"❌ Failed to register user in background: {e}")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    telegram_id = message.from_user.id
    user_name = message.from_user.username if message.from_user.username else f"User_{str(telegram_id)[:5]}"
    first_name = message.from_user.first_name if message.from_user.first_name else "ተጫዋች"

    # 1️⃣ ከሊንኩ ላይ የጋባዥ ID (args) መኖሩን መፈተሽ (ለምሳሌ /start ref_123456)
    referred_by = None
    msg_text_parts = message.text.split()
    if len(msg_text_parts) > 1:
        ref_arg = msg_text_parts[1]
        if ref_arg.startswith("ref_"):
            referred_by = ref_arg.replace("ref_", "").strip()
        else:
            referred_by = ref_arg.strip()
            
        # የራሱን ID መጋበዣ ሊንክ መጠቀም እንዳይችል መከላከያ
        if str(referred_by) == str(telegram_id):
            referred_by = None

    # 2️⃣ ምዝገባውን ቦቱን ሳይቀዘቅዝ (Freeze ሳይሆን) በThread ጀርባ ላይ ማከናወን
    threading.Thread(
        target=register_user_background,
        args=(telegram_id, user_name, first_name, referred_by),
        daemon=True
    ).start()

    # 3️⃣ የራሱን የጓደኛ መጋበዣ (Referral) ሊንክ በ Variable ብቻ ማዘጋጀት
    my_referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"

    # 4️⃣ ማራኪ የሰላምታ እና የሪፈራል ማብራሪያ ጽሑፍ በአንድ ላይ
    welcome_text = (
        f"👋 ሰላም <b>{first_name}</b>፣ ወደ <b>የኛ ቢንጎ (Yegna Bingo)</b> እንኳን በደህና መጡ! 🎉\n\n"
        "ኢትዮጵያ ውስጥ ምርጡን የቢንጎ ጨዋታ በቴሌግራም ሚኒ አፕ በቀላሉ ይጫወቱ። "
        "ገንዘብ ማስገባት፣ ማውጣት እና የደራሽ (Jackpot) ሽልማቶችን በሙሉ እውስጥ ያገኛሉ! 💰\n\n"
        "🎁 <b>የዕለታዊ ስጦታ፦</b> ሚኒ አፑን በከፈቱ ቁጥር የ 10 ETB ነፃ መጫወቻ ስጦታ ያገኛሉ!\n\n"
        "👥 <b>የጓደኛ መጋበዣ ፕሮግራም፦</b>\n"
        "ይህንን የእርሶን መጋበዣ ሊንክ ለወዳጅዎ ያጋሩ፤ አንድ ሰው በእርሶ ሊንክ ሲመዘገብ "
        "<b>የ 10 ETB መጫወቻ ቦነስ (Gift Coin)</b> ወዲያውኑ ወደ አካውንትዎ ይገባል! 🎉\n\n"
        f"🔗 <b>የእርሶ መጋበዣ ሊንክ፦</b>\n<code>{my_referral_link}</code>"
    )

    # 5️⃣ የኢንላይን ቁልፎች (የሚኒ አፕ እና የሊንክ ማጋሪያ)
    markup = types.InlineKeyboardMarkup()
    
    # 🎮 ሚኒ አፑን የሚከፍት ቁልፍ
    btn_play = types.InlineKeyboardButton(text="🎮 Open Mini App (ክፈት)", web_app=types.WebAppInfo(url=MINI_APP_URL))
    
    # 🔗 ሊንኩን በቀጥታ በቴሌግራም ለጓደኞች ለማጋራት
    share_url = f"https://t.me/share/url?url={my_referral_link}&text=የቢንጎ%20ጌም%20ተጫውተህ%20ገንዘብ%20እንድታሸንፍ%20ጋብዤሃለሁ!%20በሊንኩ%20ገብተህ%20ተመዝገብ፦"
    btn_share = types.InlineKeyboardButton(text="🔗 Share Link (ለጓደኛህ አጋራ)", url=share_url)
    
    markup.add(btn_play, btn_share)

    try:
        # 🖼️ ምስሉን፣ ፅሁፉን እና ቁልፎቹን በአንድ ላይ መላክ
        bot.send_photo(
            chat_id, 
            photo=WELCOME_IMAGE_URL, 
            caption=welcome_text, 
            parse_mode="HTML", 
            reply_markup=markup
        )
    except Exception as e:
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


# 🛠️ የአድሚን ማፅደቂያ/መሰረዣ ቁልፎች
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
