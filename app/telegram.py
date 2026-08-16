import os
import sys
import time
import requests
import threading
from datetime import datetime
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip().replace("@", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()

# 🔗 የባክኤንድ አድራሻ (ለ Render Webhook የተስተካከለ)
SERVER_URL = os.getenv("SERVER_URL", "https://ethiobingo-jk6x.onrender.com").rstrip('/')
BACKEND_URL = SERVER_URL
MINI_APP_URL = SERVER_URL

# 🖼️ የማቀባበያ ምስል ሊንክ
WELCOME_IMAGE_URL = f"{SERVER_URL}/static/images/welcome.jpeg"

bot = TeleBot(BOT_TOKEN)

# የቴሌግራም ተጠቃሚዎችን ጊዜያዊ የሪፈራል መረጃ መያዣ Dictionary
USER_REF_CACHE = {}

print(f"🎰 የYegna Bingo ቦት (@{BOT_USERNAME}) በሰላም ስራ ጀምሯል...")
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


# 📢 በThread ውስጥ የሚሮጥ ማስታወቂያ ወይም ቦነስ ለሁሉም ተጠቃሚዎች መላኪያ ፋንክሽን
def broadcast_worker(text_message, reply_markup=None):
    print("📢 የማስታወቂያ ፕሮሞሽን ለተጠቃሚዎች መላክ ተጀምሯል...")
    
    user_ids = []
    try:
        res = requests.get(f"{BACKEND_URL}/api/users/all_ids", timeout=10)
        if res.status_code == 200:
            data = res.json()
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

    for u_id in user_ids:
        if not u_id:
            continue
        try:
            target_chat_id = str(u_id).strip()
            bot.send_message(
                target_chat_id, 
                text_message, 
                parse_mode="HTML", 
                reply_markup=reply_markup, 
                disable_web_page_preview=True
            )
            success_count += 1
            time.sleep(0.04)  # Rate limit (ከ 30 msg/sec እንዳያልፍ)
        except ApiTelegramException as te:
            fail_count += 1
        except Exception as e:
            fail_count += 1

    print(f"🎉 ማስታወቂያ ተልኮ ተጠናቋል! ስኬታማ፦ {success_count}፣ የከሸፉ፦ {fail_count}")


# 1️⃣ /start ሲባል የሚመጣ መልእክት
@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_id = message.from_user.id

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

    referred_by = USER_REF_CACHE.pop(telegram_id, None)

    threading.Thread(
        target=register_user_background,
        args=(telegram_id, user_name, first_name, phone_number, referred_by),
        daemon=True
    ).start()

    remove_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(chat_id, "✅ ስልክ ቁጥርዎ በስኬት ተመዝግቧል!", reply_markup=remove_keyboard)

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


# 📢 4️⃣ ADMIN COMMAND: /broadcast <የመልእክት ጽሁፍ>
@bot.message_handler(commands=['broadcast'])
def handle_broadcast_command(message):
    telegram_id = str(message.from_user.id)
    
    if ADMIN_TELEGRAM_ID and telegram_id != ADMIN_TELEGRAM_ID:
        bot.reply_to(message, "⛔ ይህንን ማድረግ የሚችለው አድሚን ብቻ ነው!")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ እባክዎን የመልእክት ጽሁፍ ያስገቡ!\nምሳሌ፦ `/broadcast ዛሬ የ 50% ቦነስ አዘጋጅተናል!`", parse_mode="Markdown")
        return

    promo_msg = parts[1]
    bot.reply_to(message, "🚀 የማስታወቂያ መልእክቱ በጀርባ ለሁሉም ተጠቃሚዎች መላክ ተጀምሯል...")

    threading.Thread(
        target=broadcast_worker,
        args=(promo_msg, None),
        daemon=True
    ).start()


# 🎁 5️⃣ ADMIN COMMAND: /create_bonus <amount> <max_users>
@bot.message_handler(commands=['create_bonus'])
def handle_create_bonus_command(message):
    telegram_id = str(message.from_user.id)
    
    if ADMIN_TELEGRAM_ID and telegram_id != ADMIN_TELEGRAM_ID:
        bot.reply_to(message, "⛔ ይህንን ማድረግ የሚችለው አድሚን ብቻ ነው!")
        return

    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(
            message, 
            "⚠️ አጠቃቀም ስህተት ነው!\nምሳሌ፦ `/create_bonus 50 50`\n(ማለትም፦ ለ 50 ሰዎች የ 50 ብር ቦነስ)",
            parse_mode="Markdown"
        )
        return

    try:
        amount = float(parts[1])
        max_claims = int(parts[2])
    except ValueError:
        bot.reply_to(message, "❌ እባክዎን ትክክለኛ ቁጥር ያስገቡ!")
        return

    # ባክኤንድ API ላይ አዲስ ቦነስ መመዝገብ
    url = f"{BACKEND_URL}/api/users/admin/create-bonus"
    payload = {
        "admin_telegram_id": telegram_id,
        "amount": amount,
        "max_claims": max_claims
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        res_data = res.json()

        if res.status_code == 200 and res_data.get("success"):
            bonus_code = res_data.get("code")
            bot.reply_to(message, f"✅ የ {amount} ETB ቦነስ ለ {max_claims} ሰዎች ተፈጥሯል። ለሁሉም ተጠቃሚዎች መልእክቱ እየተላከ ነው...")

            # በምስሉ ላይ ያለው ዓይነት ማራኪ ቦነስ ማስታወቂያ ጽሁፍ
            promo_text = (
                f"🔥 <b>የጨዋታው ደንብ ጣሪያ ነክቷል!</b> 🎲\n\n"
                f"⚡️🔥 ሜዳው በደስ ሞቋል! Yegna Bingo ላይ አሁኑኑ ተቀላቅለው የጨዋታ ትኩሳት ጋር አብረው ይደመቁ! 🚀\n\n"
                f"ይፍጠኑ! ሻምፒዮን! ቶሎ ካልደረሱ የ Yegna Bingo ፈጣን የ <b>{amount} ETB</b> ቦነስ ስጦታ ያልቃል! 🎁"
            )

            markup = types.InlineKeyboardMarkup()
            btn_claim = types.InlineKeyboardButton(
                text="🎁 ክሌም አድርግ (Claim)", 
                callback_data=f"claim_bonus_{bonus_code}"
            )
            markup.add(btn_claim)

            # በጀርባ ለሁሉም ተጠቃሚዎች መላክ
            threading.Thread(
                target=broadcast_worker,
                args=(promo_text, markup),
                daemon=True
            ).start()
        else:
            bot.reply_to(message, f"❌ ስህተት፦ {res_data.get('message', 'ቦነስ መፍጠር አልተቻለም')}")
    except Exception as e:
        bot.reply_to(message, f"❌ ከሰርቨር ጋር መገናኘት አልተቻለም፦ {e}")


# 🎁 6️⃣ USER CALLBACK: Claim Bonus Button ሲጫኑ
@bot.callback_query_handler(func=lambda call: call.data.startswith('claim_bonus_'))
def handle_claim_bonus_callback(call):
    telegram_id = str(call.from_user.id)
    bonus_code = call.data.replace("claim_bonus_", "").strip()

    url = f"{BACKEND_URL}/api/users/claim-bonus"
    payload = {
        "telegram_id": telegram_id,
        "code": bonus_code
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        res_data = res.json()

        if res.status_code == 200 and res_data.get("success"):
            msg = res_data.get("message", "🎉 ቦነሱ በስኬት ተጨምሯል!")
            bot.answer_callback_query(
                call.id, 
                text=msg, 
                show_alert=True
            )
        else:
            msg = res_data.get("message", "ቦነሱን መቀበል አልተቻለም")
            bot.answer_callback_query(call.id, text=f"⚠️ {msg}", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, text="❌ ከሰርቨር ጋር መገናኘት አልተቻለም።", show_alert=True)


# 🛠️ የባክኤንድ ጥያቄ በThread የሚያስኬድ
def send_admin_action_to_backend(call, url, payload, headers, target_id, action, tx_type):
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        try:
            res_data = response.json()
        except:
            res_data = {"success": False, "message": response.text}

        if response.status_code == 200 and res_data.get("success"):
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
    
    threading.Thread(
        target=send_admin_action_to_backend, 
        args=(call, url, payload, headers, target_id, action, tx_type),
        daemon=True
    ).start()
