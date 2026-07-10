import os
import requests
from telebot import TeleBot, types

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (Configuration ከ Railway Env ይነበባሉ)
# --------------------------------------------------------------------------
# 💡 ፎልባክ ላይ ያንተን እውነተኛ መረጃዎች ማስገባት ትችላለህ
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_CHAT_ID", "YOUR_TELEGRAM_ID_HERE")

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
    btn_play = types.InlineKeyboardButton(text="🎮 Play Now", web_app=types.WebAppInfo(url=MINI_APP_URL))
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
    try:
        response = requests.get(f"{BACKEND_URL}/api/users/{telegram_id}")
        if response.status_code == 200:
            user_data = response.json()
            balance = user_data.get("wallet", 0.0) # 🛠 ከጌም ራውተር ጋር ተመጣጣኝ
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


# 🛠️ አድሚኑ (አንተ) የቴሌግራም ላይ Approved/Reject ቁልፍ ሲጫን
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_dep_', 'rej_dep_', 'app_wit_', 'rej_wit_')))
def handle_admin_actions(call):
    if str(call.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.answer_callback_query(call.id, "❌ ይቅርታ፣ ይህንን ትዕዛዝ ለመፈጸም ፈቃድ የለዎትም!")
        return

    action_data = call.data.split('_')
    action = action_data[0]    # 'app' ወይም 'rej'
    tx_type = action_data[1]   # 'dep' ወይም 'wit'
    target_id = int(action_data[2])

    if tx_type == "dep":
        url = f"{BACKEND_URL}/api/users/deposit/admin/approve"
        payload = {"deposit_id": target_id, "action": "APPROVE" if action == "app" else "REJECT"}
    else:
        url = f"{BACKEND_URL}/api/users/withdraw/admin/approve"
        payload = {"withdraw_id": target_id, "action": "APPROVE" if action == "app" else "REJECT"}

    try:
        response = requests.post(url, json=payload)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("success"):
            status_text = "🟢 APPROVED" if action == "app" else "🔴 REJECTED"
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{call.message.text}\n\n<b>🔄 የውሳኔ ሁኔታ፦ {status_text}!</b>",
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "✅ ውሳኔው በተሳካ ሁኔታ ተመዝግቧል!")
        else:
            bot.answer_callback_query(call.id, f"❌ ስህተት፦ {res_data.get('message', 'ስህተት ተከስቷል')}")
    except Exception:
        bot.answer_callback_query(call.id, "❌ ከባክአንድ ሰርቨር ጋር መገናኘት አልተቻለም!")

if __name__ == "__main__":
    bot.infinity_polling()
