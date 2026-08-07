import os
import sys
import time
import requests
import threading  # 💡 የባክኤንድ ጥያቄ ቦቱን Freeze እንዳያደርገው በThread ለማሰራት
from datetime import datetime
from telebot import TeleBot, types
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (Railway ላይ ከተጫኑት Variables ብቻ የሚያነቡ)
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip().replace("@", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")

# 🔗 የባክኤንድ አድራሻ (ከ Railway ወደ Render ተቀይሯል)
SERVER_URL = os.getenv("SERVER_URL", "https://ethiobingo-jk6x.onrender.com").rstrip('/')
BACKEND_URL = SERVER_URL
MINI_APP_URL = SERVER_URL

# 🖼️ የማቀባበያ ምስል ሊንክ
WELCOME_IMAGE_URL = f"{SERVER_URL}/static/images/welcome.png.jpeg"

bot = TeleBot(BOT_TOKEN)

# የቴሌግራም ተጠቃሚዎችን ጊዜያዊ የሪፈራል መረጃ መያዣ Dictionary
USER_REF_CACHE = {}

# 📢 የማስታወቂያ ጽሑፍ
PROMO_TEXT = """🚨 ዛሬ የእርስዎ ቀን ሊሆን ይችላል! 🚨 

🎁 50% FIRST DEPOSIT BONUS

🎮 Yegna Bingo ይቀላቀሉ
🏆 ዕድልዎን ይሞክሩ!

🏆 በየሳምንቱ ለከፍተኛ ተጫዋቾች የሚሰጥ ልዩ ሽልማት ይዟል!

🎁 Daily Bonus
👥 Referral Bonus

👥 Official Group
https://t.me/Yegna_Bingo_Gift_Group

📢 Official Channel
https://t.me/Yegna_Bingo_public

☎️ Customer Support
👤 @YegnaaBingo_Support
📞 +251 95 598 9803

🔥 Yegna Bingo — ዛሬ ይጫወቱ፣ ዛሬ ያሸንፉ! 🍀💚"""

print(f"🎰 የYegnaኛ Bingo ቦት (@{BOT_USERNAME}) በሰላም ስራ ጀምሯል...")
print("TELEGRAM MODULE LOADED")


# 👥 ጀርባ ላይ አዲስ ተጫዋች በስልክ ቁጥር እና በሪፈራል ጭምር የሚመዘግብ የ Thread ተግባር
def register_user_background(telegram_id, telegram_name, first_name, phone_number=None, referred_by=None):
    register_api_url = f"{BACKEND_URL}/api/users/register"
    payload = {
        "telegram_id": str(telegram_id),
        "telegram_name": telegram_name,
        "first_name": first_name,
        "phone_number": str(phone_number) if phone_number else None,
        "referred_by": str(referred_by) if referred_by else None
    }
        
    try:
        response = requests.post(register_api_url, json=payload, timeout=10)
        print(f"📡 Backend Register Response: {response.json()}")
    except Exception as e:
        print(f"❌ Failed to register user in background: {e}")


# 📢 ማስታወቂያ ለሁሉም ተጠቃሚዎች መላኪያ ፋንክሽን (የተስተካከለ እና ደህንነቱ የተጠበቀ)
def broadcast_promo_message():
    print("📢 የማስታወቂያ ፕሮሞሽን ለተጠቃሚዎች መላክ ተጀምሯል...")
    
    user_ids = []
    # 1. ከባክኤንድ ዳታቤዝ የሁሉንም ተጠቃሚዎች ID ማምጣት
    try:
        res = requests.get(f"{BACKEND_URL}/api/users/all_ids", timeout=10)
        if res.status_code == 200:
            data = res.json()
            # የ API መልስ array ወይም object እንደሆነ መለየት
            if isinstance(data, list):
                user_ids = data
            elif isinstance(data, dict):
                user_ids = data.get("user_ids", [])
            print(f"📊 በአጠቃላይ {len(user_ids)} ተጠቃሚዎች ከዳታቤዝ ተገኝተዋል")
        else:
            print(f"⚠️ ከባክኤንድ User IDs ማምጣት አልተቻለም Status: {res.status_code}")
    except Exception as e:
        print(f"❌ ከባክኤንድ ጋር መገናኘት አልተቻለም፦ {e}")

    if not user_ids:
        print("⚠️ ምንም የሚላክላቸው ተጠቃሚዎች አልተገኙም!")
        return

    success_count = 0
    fail_count = 0

    # 2. ለተጠቃሚዎች በየተራ መላክ
    for u_id in user_ids:
        if not u_id:
            continue
        try:
            target_chat_id = str(u_id).strip()
            bot.send_message(target_chat_id, PROMO_TEXT, disable_web_page_preview=True)
            success_count += 1
            time.sleep(0.05)  # Telegram Rate Limit እንዳይይዘን ትንሽ ማረፍ
        except Exception as e:
            # 💡 ቦቱን Block ላደረጉ ወይም ለአጠፉ አካውንቶች Exception ተይዞ ያልፋል
            fail_count += 1
            print(f"⚠️ ለ User ID {u_id} ማስታወቂያ መላክ አልተቻለም (Skipped)፦ {e}")

    print(f"🎉 ማስታወቂያ ተልኮ ተጠናቋል! ስኬታማ፦ {success_count}፣ የከሸፉ፦ {fail_count}")


# ⏰ Scheduler ማዘጋጀት (ቀን 4:00፣ 8:00፣ 10:00 እና ማታ 12:00፣ 2:00፣ 4:00)
def start_promo_scheduler():
    ethiopia_tz = pytz.timezone("Africa/Addis_Ababa")
    scheduler = BackgroundScheduler(timezone=ethiopia_tz)

    # የኢትዮጵያ ሰዓት ወደ 24h format (ቀን 4=10, ቀን 8=14, ቀን 10=16, ማታ 12=18, ማታ 2=20, ማታ 4=22)
    scheduled_hours = [10, 14, 16, 18, 20, 22]

    for hour in scheduled_hours:
        scheduler.add_job(
            broadcast_promo_message,
            trigger="cron",
            hour=hour,
            minute=0
        )

    scheduler.start()
    print("⏰ የማስታወቂያ Scheduler በስኬት ተጀምሯል (በየቀኑ ቀን 4, 8, 10 እና ማታ 12, 2, 4 ይልካል)!")


# 1️⃣ /start ሲባል የሚመጣ መልእክት
@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_id = message.from_user.id

    # ከሊንኩ ላይ የጋባዥ ID (args) መኖሩን መፈተሽ
    msg_text_parts = message.text.split()
    if len(msg_text_parts) > 1:
        ref_arg = msg_text_parts[1]
        referred_by = ref_arg.replace("ref_", "").strip() if ref_arg.startswith("ref_") else ref_arg.strip()
        if str(referred_by) != str(telegram_id):
            USER_REF_CACHE[telegram_id] = referred_by

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_register = types.KeyboardButton("📝 Register Now")
    markup.add(btn_register)

    welcome_msg = (
        "🎉 እንኳን በሰላም ወደ ቴሌግራም ገፃችን መጡ\n\n"
        "ለመቀጠል መጀመሪያ ይመዝገቡ ወይም ከታች Register Now የሚለውን ይጫኑ ።"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)


# 2️⃣ "📝 Register Now" ሲጫኑ የስልክ ቁጥር ጥያቄ ማሳያ
@bot.message_handler(func=lambda message: message.text == "📝 Register Now")
def ask_contact(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_contact = types.KeyboardButton("📱 Share Contact", request_contact=True)
    markup.add(btn_contact)

    bot.send_message(
        message.chat.id, 
        "📱 ከታች ያለውን Share contact የሚለውን ይጫኑ", 
        reply_markup=markup
    )


# 3️⃣ ተጠቃሚው የስልክ ቁጥሩን (Contact) ሲልከው
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    telegram_id = message.from_user.id
    phone_number = message.contact.phone_number
    user_name = message.from_user.username if message.from_user.username else f"User_{str(telegram_id)[:5]}"
    first_name = message.from_user.first_name if message.from_user.first_name else message.from_user.username

    # የተቀመጠ ሪፈራል ካለ ማምጣት
    referred_by = USER_REF_CACHE.pop(telegram_id, None)

    # ጀርባ ላይ ወደ ባክኤንድ የመመዝገብ/የማዘመን ስራ
    threading.Thread(
        target=register_user_background,
        args=(telegram_id, user_name, first_name, phone_number, referred_by),
        daemon=True
    ).start()

    # የቆዩ የኪቦርድ ቁልፎችን ማጥፊያ
    remove_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(chat_id, "✅ ስልክ ቁጥርዎ በስኬት ተመዝግቧል!", reply_markup=remove_keyboard)

    # የሪፈራል ሊንክ እና የሰላምታ መረጃ መላክ
    my_referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"

    welcome_text = (
        f"👋 ሰላም <b>{first_name}</b>፣ ወደ <b>የኛ ቢንጎ (Yegna Bingo)</b> እንኳን በደህና መጡ! 🎉\n\n"
        "ኢትዮጵያ ውስጥ ምርጡን የቢንጎ ጨዋታ በቴሌግራም ሚኒ አፕ በቀላሉ ይጫወቱ። "
        "ገንዘብ ማስገባት፣ ማውጣት እና የደራሽ (Jackpot) ሽልማቶችን በሙሉ እውስጥ ያገኛሉ! 💰\n\n"
        "🎁 <b>የዕለታዊ ስጦታ፦</b> ሚኒ አፑን በከፈቱ ቁጥር የ 10 ETB ነፃ መጫወቻ ስጦታ ያገኛሉ!\n\n"
        "👥 <b>የጓደኛ መጋበዣ ፕሮግራም፦</b>\n"
        "ይህንን የእርሶን መጋበዣ ሊንክ ለወዳጅዎ ያጋሩ፤ አንድ ሰው በእርሶ ሊንክ ሲመዘገብ "
        "<b>የ 2.0 ETB መጫወቻ ቦነስ (Gift Coin)</b> ወዲያውኑ ወደ አካውንትዎ ይገባል! 🎉\n\n"
        f"🔗 <b>የእርሶ መጋበዣ ሊንክ፦</b>\n<code>{my_referral_link}</code>"
    )

    markup = types.InlineKeyboardMarkup()
    btn_play = types.InlineKeyboardButton(text="🎮 Open Mini App (ክፈት)", web_app=types.WebAppInfo(url=MINI_APP_URL))
    share_url = f"https://t.me/share/url?url={my_referral_link}&text=የቢንጎ%20ጌም%20ተጫውተህ%20ገንዘብ%20እንድታሸንፍ%20ጋብዤሃለሁ!%20በሊንኩ%20ገብተህ%20ተመዝገብ፦"
    btn_share = types.InlineKeyboardButton(text="🔗 Share Link (ለጓደኛህ አጋራ)", url=share_url)
    
    markup.add(btn_play, btn_share)

    try:
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
                    reply_markup=None
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
    action = action_data[0]
    tx_type = action_data[1]
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
    # Scheduler ማስጀመር
    start_promo_scheduler()
    print("🚀 Telegram module initialized in Webhook mode. Polling disabled.")
