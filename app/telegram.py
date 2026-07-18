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

bot = TeleBot(BOT_TOKEN)

print("🔥 CALLBACK RECEIVED")
print(call.data)
print(f"🎰 የYegnaኛ Bingo ቦት (@{BOT_USERNAME}) በሰላም ስራ ጀምሯል...")
print("TELEGRAM STARTED")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_play = types.InlineKeyboardButton(text="🎰 Play Now", web_app=types.WebAppInfo(url=MINI_APP_URL))
    btn_balance = types.InlineKeyboardButton(text="💰 Check Balance", callback_data="check_balance")
    btn_deposit = types.InlineKeyboardButton(text="🏦 Make a Deposit", callback_data="start_deposit")
    btn_support = types.InlineKeyboardButton(text="Support 📞", url="https://t.me/cartelabingo_support")

    markup.add(btn_play)
    markup.add(btn_balance, btn_deposit)
    markup.add(btn_support)

    welcome_text = (
        f"👋 Welcome to Yegna Bingo, {user_name}!\n\n"
        "🎰 Grab Your Cartela, Join the Game, and Let the Fun Begin!"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "check_balance")
def inline_check_balance(call):
    try:
        bot.answer_callback_query(callback_query_id=call.id)
    except:
        pass

    telegram_id = str(call.from_user.id)
    url = f"{BACKEND_URL}/api/users/{telegram_id}" 
    
    try:
        response = requests.get(url, timeout=15)
        try:
            res_data = response.json()
        except:
            res_data = {"success": False, "message": response.text}

        if response.status_code == 200 and res_data.get("success"):
            user_obj = res_data.get("user", {})
            wallet_amount = user_obj.get("balance", 0.0) 
            bot.send_message(call.message.chat.id, f"💰 ያሎት ቀሪ ሂሳብ (Balance)፦ {wallet_amount} ETB")
        else:
            bot.send_message(call.message.chat.id, "❌ ተጠቃሚዎ አልተመዘገበም፣ እባክዎ መጀመሪያ ሚኒ አፑን ይክፈቱ!")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ የባላንስ መረጃን ለማምጣት አልተቻለም፦ {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "start_deposit")
def callback_deposit(call):
    try:
        bot.answer_callback_query(callback_query_id=call.id)
    except:
        pass
    bot.send_message(call.message.chat.id, "ℹ️ ዝቅተኛው የማስገቢያ መጠን 50 ETB ነው።")
    msg = bot.send_message(call.message.chat.id, "እባክዎ ማስገባት የሚፈልጉትን የብር መጠን በቁጥር ብቻ ያስገቡ፦")
    bot.register_next_step_handler(msg, process_deposit_amount)

def process_deposit_amount(message):
    chat_id = message.chat.id
    amount_text = message.text

    if not amount_text.isdigit() or int(amount_text) < 50:
        msg = bot.send_message(chat_id, "❌ የተሳሳተ የብር መጠን! እባክዎ ከ50 የሚበልጥ ቁጥር ያስገቡ፦")
        bot.register_next_step_handler(msg, process_deposit_amount)
        return

    markup = types.InlineKeyboardMarkup()
    payment_url = f"{MINI_APP_URL}?page=deposit&amount={amount_text}"
    btn_pay = types.InlineKeyboardButton(text="Manual-Payment 📲", web_app=types.WebAppInfo(url=payment_url))
    markup.add(btn_pay)

    bot.send_message(chat_id, f"💰 የ {amount_text} ETB ማስተላለፊያ ፎርም ለመክፈት ከታች ያለውን ቁልፍ ይጫኑ፦", reply_markup=markup)


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


# 🛠️ ፊክስ፦ አድሚኑ ቁልፍ ሲጫን (ከባክኤንዱ 'approve_dep_' እና 'reject_dep_' Callback መረጃ ጋር እንዲገጣጠም የተደረገ)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_dep_', 'reject_dep_', 'approve_with_', 'reject_with_')))
def handle_admin_actions(call):
    try:
        # Loading... ክብ ማሽከርከሩን ወዲያውኑ ያጠፋዋል
        bot.answer_callback_query(callback_query_id=call.id, text="⏳ ውሳኔዎ በሂደት ላይ ነው...")
    except:
        pass
    
    admin_id_str = str(call.from_user.id).strip()
    action_data = call.data.split('_')
    action = action_data[0]    # 'approve' ወይም 'reject'
    tx_type = action_data[1]   # 'dep' (deposit) ወይም 'with' (withdraw)
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
