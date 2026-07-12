import os
import sys
import requests
import threading  # 💡 የባክኤንድ ጥያቄ ቦቱን Freeze እንዳያደርገው በThread ለማሰራት
from telebot import TeleBot, types

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (ቀጥተኛ እና አስተማማኝ)
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")

# 🔗 የባክኤንድ አድራሻ
SERVER_URL = os.getenv("SERVER_URL", "https://web-production-fd82a.up.railway.app").rstrip('/')
BACKEND_URL = SERVER_URL
MINI_APP_URL = SERVER_URL

bot = TeleBot(BOT_TOKEN)

print(f"🎰 የYegnaኛ Bingo ቦት (@{BOT_USERNAME}) በሰላም ስራ ጀምሯል...")

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
            # 💡 ፊክስ፦ በዳታቤዝህ ላይ ያለው ኮለም 'wallet' ስለሆነ ከ balance ወደ wallet ተቀይሯል
            wallet_amount = user_obj.get("wallet", 0.0) 
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
        print(f"📝 Response Body: {response.text}")

        try:
            res_data = response.json()
        except:
            res_data = {"success": False, "message": response.text}

        if response.status_code == 200 and res_data.get("success"):
            print(f"✅ Action successfully handled by backend for ID #{target_id}")
            
            # 💡 ፊክስ፦ ውሳኔው በተሳካ ሁኔታ ሲጠናቀቅ አድሚኑ ጋር ያለውን የቴሌግራም መልዕክት ሁኔታ ይቀይረዋል
            status_text = "✅ ጸድቋል (Approved)" if action == "app" else "❌ ውድቅ ተደርጓል (Rejected)"
            type_text = "የገንዘብ ማስገቢያ" if tx_type == "dep" else "የገንዘብ ማውጫ"
            
            updated_msg = f"{call.message.text}\n\n====================\n⚖️ **ውሳኔ፦** {status_text}"
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=updated_msg,
                reply_markup=None  # የአፕሩቭ በተኖቹን ያጠፋቸዋል
            )
        else:
            error_detail = res_data.get('message', f'HTTP Error {response.status_code}')
            bot.send_message(call.message.chat.id, f"❌ ሰርቨሩ ጥያቄውን አልተቀበለውም፦ {error_detail}")
    except Exception as e:
        print("Admin Action Error:", e)
        bot.send_message(call.message.chat.id, f"❌ ወደ ባክኤንድ መገናኘት አልተቻለም፦ {str(e)}")


# 🛠️ አድሚኑ የቴሌግራም ላይ Approved/Reject ቁልፍ ሲጫን
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_dep_', 'rej_dep_', 'app_wit_', 'rej_wit_')))
def handle_admin_actions(call):
    
    try:
        bot.answer_callback_query(callback_query_id=call.id, text="⏳ ውሳኔዎ በሂደት ላይ ነው...")
    except Exception as e:
        print(f"⚠️ Callback answer error: {e}")
    
    admin_id_str = str(call.from_user.id).strip()
    action_data = call.data.split('_')
    action = action_data[0]    # 'app' ወይም 'rej'
    tx_type = action_data[1]   # 'dep' ወይም 'wit'
    target_id = int(action_data[2])

    # 2. ዩአርኤል እና ፔይሎድ ማዘጋጀት
    if tx_type == "dep":
        url = f"{BACKEND_URL}/api/deposit/admin/approve"
        payload = {
            "deposit_id": target_id, 
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": admin_id_str,
            "message_id": call.message.message_id,
            "admin_password": ADMIN_PASSWORD
        }
    else:
        url = f"{BACKEND_URL}/api/withdraw/admin/approve"
        payload = {
            "withdraw_id": target_id, 
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": admin_id_str,
            "message_id": call.message.message_id,
            "admin_password": ADMIN_PASSWORD
        }

    headers = {"Content-Type": "application/json"}

    print(f"📡 Requesting: {url} with Payload: {payload}")
    
    # 3️⃣ ጥያቄውን በጀርባ (Background Thread) መላክ
    threading.Thread(
        target=send_admin_action_to_backend, 
        args=(call, url, payload, headers, target_id, action, tx_type),
        daemon=True
    ).start()


if __name__ == "__main__":
    bot.infinity_polling(
        skip_pending=True,
        timeout=60
    )
