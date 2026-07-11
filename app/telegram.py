import os
import requests
from telebot import TeleBot, types

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (Configuration ከ Railway Env በትክክል እንዲያነቡ ተስተካክለዋል)
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_CHAT_ID", "")).strip()

# 🔗 የባክኤንድ እና የሚኒ አፕ ሊንኮች
BACKEND_URL = "https://web-production-fd82a.up.railway.app" 
MINI_APP_URL = "https://web-production-fd82a.up.railway.app" 

bot = TeleBot(BOT_TOKEN)

print("🎰 የYegnaኛ Bingo ቦት በሰላም ስራ ጀምሯል...")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_play = types.InlineKeyboardButton(text="���� Play Now", web_app=types.WebAppInfo(url=MINI_APP_URL))
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
            balance = user_obj.get("wallet", 0.0) 
            bot.send_message(call.message.chat.id, f"💰 ያሎት ቀሪ ሂሳብ (Balance)፦ {balance} ETB")
        else:
            bot.send_message(call.message.chat.id, "❌ ተጠቃሚዎ አልተመዘገበም፣ እባክዎ መጀመሪያ ሚኒ አፑን ይክፈቱ!")
    except Exception:
        bot.send_message(call.message.chat.id, "⚠️ የባላንስ መረጃን ለማምጣት አልተቻለም።")


@bot.callback_query_handler(func=lambda call: call.data == "start_deposit")
def callback_deposit(call):
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


# 🛠️ ፊክስ 1፦ አድሚኑ (አንተ) የቴሌግራም ላይ Approved/Reject ቁልፍ ሲጫን
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_dep_', 'rej_dep_', 'app_wit_', 'rej_wit_')))
def handle_admin_actions(call):
    
    # 🛠️ ፊክስ 1a - CRITICAL: ወዲያውኑ Telegram API ን ይህን callback ን አጠናቅቅ ለማድረግ ንገር
    # ይህ ሳይሆን ከሆነ Telegram ለ 30 ሴ/ደ "Loading..." spinner ይታይ ይቀራል
    try:
        bot.answer_callback_query(call.id, "⏳ በመካሄድ ላይ ነው...")
        print("✅ Callback query answered immediately to prevent spinner freeze")
    except Exception as e:
        print(f"⚠️ Failed to answer callback query: {e}")
    
    # 🔍 መመርመሪያ መስመሮች 1 (Callback መረጃዎችን ለማየት)
    print("========== CALLBACK ==========")
    print("CALLBACK DATA:", call.data)
    print("ADMIN ID:", call.from_user.id)
    print("ENV ADMIN:", ADMIN_TELEGRAM_ID)

    admin_id_str = str(call.from_user.id).strip()
    
    if ADMIN_TELEGRAM_ID and admin_id_str != ADMIN_TELEGRAM_ID:
        error_msg = f"❌ ይቅርታ፣ ይህንን ትዕዛዝ ለመፈጸም ፈቃድ የለዎትም! (የእርስዎ ID: {admin_id_str})"
        try:
            bot.send_message(call.message.chat.id, error_msg)
        except Exception as e:
            print(f"Failed to send unauthorized message: {e}")
        return

    action_data = call.data.split('_')
    action = action_data[0]    # 'app' ወይም 'rej'
    tx_type = action_data[1]   # 'dep' ወይም 'wit'
    target_id = int(action_data[2])

    if tx_type == "dep":
        url = f"{BACKEND_URL}/api/deposit/admin/approve"
        payload = {
            "deposit_id": target_id, 
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": admin_id_str,
            "message_id": call.message.message_id
        }
    else:
        url = f"{BACKEND_URL}/api/withdraw/admin/approve"
        payload = {
            "withdraw_id": target_id, 
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": admin_id_str,
            "message_id": call.message.message_id
        }

    # 🔍 መመርመሪያ መስመሮች 2 (ከመላኩ በፊት ዩአርኤል እና ፔይሎድ ለማየት)
    print("POST URL:", url)
    print("PAYLOAD:", payload)

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        # 🔍 መመርመሪያ መስመሮች 3 (ከተላከ በኋላ ሰርቨሩ የመለሰውን ለማየት)
        print("STATUS:", response.status_code)
        print("BODY:", response.text)

        try:
            res_data = response.json()
        except:
            res_data = {"success": False, "message": response.text}

        if response.status_code == 200 and res_data.get("success"):
            print("✅ Admin Action successfully processed by backend.")
        else:
            error_detail = res_data.get('message', 'Unknown Error')
            print(f"❌ Backend returned error: {error_detail}")
            bot.send_message(call.message.chat.id, f"❌ ስህተት፦ {error_detail}")

    except Exception as e:
        print("Admin Action Error:", e)
        bot.send_message(call.message.chat.id, "❌ ከባክኤንድ ሰርቨር ጋር መገናኘት አልተቻለም (Server Error)")


if __name__ == "__main__":
    bot.infinity_polling(
        skip_pending=True,
        timeout=60
    )
