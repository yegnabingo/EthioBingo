import os
import requests
from telebot import TeleBot, types

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (Configuration)
# --------------------------------------------------------------------------
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # ከ BotFather ያገኘኸውን ቶክን እዚህ ተካ
ADMIN_TELEGRAM_ID = "YOUR_PERSONAL_TELEGRAM_ID"  # የአንተን የቴሌግራም ID ቁጥር እዚህ ተካ
BACKEND_URL = "http://127.0.0.1:8000"  # የFastAPI ባክአንድ ዩአርኤል (ወይም የRailway ሊንክ)
MINI_APP_URL = "https://your-bingo-frontend-link.web.app" # የሚኒ አፑ የፊት ገጽ ሊንክ

bot = TeleBot(BOT_TOKEN)
user_states = {} # የተጠቃሚዎችን የብር መጠን ግብዓት ጊዜያዊ ሁኔታ መቆጣጠሪያ

print("🎰 የYegnaኛ Bingo ቦት በሰላም ስራ ጀምሯል...")

# --------------------------------------------------------------------------
# 🚀 1. /start ሲጫኑ ዋናውን ሜኑ (Keyboard) ማሳያ ሎጂክ
# --------------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    # የቦቱ ዋና የውስጥ ቁልፎች (Inline Keyboard)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_play = types.InlineKeyboardButton(text="🎮 Play Now", web_app=types.WebAppInfo(url=MINI_APP_URL))
    btn_register = types.InlineKeyboardButton(text="📝 Register", callback_data="register_user")
    btn_balance = types.InlineKeyboardButton(text="💰 Check Balance", callback_data="check_balance")
    btn_deposit = types.InlineKeyboardButton(text="🏦 Make a Deposit", callback_data="start_deposit")
    btn_support = types.InlineKeyboardButton(text="Support 📞", url="https://t.me/cartelabingo_support")
    btn_instructions = types.InlineKeyboardButton(text="📕 Instructions", callback_data="show_instructions")

    markup.add(btn_play, btn_register)
    markup.add(btn_balance, btn_deposit)
    markup.add(btn_support, btn_instructions)

    welcome_text = (
        f"👋 Welcome to Cartela Bingo, {user_name}!\n\n"
        "🎰 Every Square Counts – Grab Your Cartela, Join the Game, and Let the Fun Begin!"
    )
    
    bot.send_message(chat_id, welcome_text, reply_markup=markup)


# 🎮 ተጠቃሚው /play ሲል ወይም ሜኑ ላይ ሲነካ ቀጥታ ጌሙን እንዲከፍትለት
@bot.message_handler(commands=['play'])
def menu_play_game(message):
    markup = types.InlineKeyboardMarkup()
    btn_play = types.InlineKeyboardButton(text="🎰 ቢንጎን ክፈት (Open Bingo)", web_app=types.WebAppInfo(url=MINI_APP_URL))
    markup.add(btn_play)
    bot.send_message(message.chat.id, "ጨዋታውን ለመጀመር ከታች ያለውን ቁልፍ ይጫኑ፡", reply_markup=markup)


# 💰 ተጠቃሚው /balance ሲል ከባክአንድ ሰርቨር ላይ ባላንሱን ጠይቆ እንዲያሳይ
@bot.message_handler(commands=['balance'])
def menu_check_balance(message):
    telegram_id = str(message.from_user.id)
    try:
        response = requests.get(f"{BACKEND_URL}/api/users/{telegram_id}")
        if response.status_code == 200:
            user_data = response.json()
            balance = user_data.get("balance", 0.0)
            bot.send_message(message.chat.id, f"💰 ያሎት ቀሪ ሂሳብ (Balance)፦ {balance} ETB")
        else:
            bot.send_message(message.chat.id, "❌ ተጠቃሚዎ አልተመዘገበም፣ እባክዎ መጀመሪያ በጌሙ ውስጥ ይመዝገቡ!")
    except Exception:
        bot.send_message(message.chat.id, "⚠️ የባላንስ መረጃን ለማምጣት አልተቻለም።")


# --------------------------------------------------------------------------
# 📥 2. /deposit ወይም "Make a Deposit" ሲጫኑ የሚመጣ ፍሰት
# --------------------------------------------------------------------------
@bot.message_handler(commands=['deposit'])
def command_deposit(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "ℹ️ Here are the min you can deposit\nMin Amount: 50 ETB")
    msg = bot.send_message(chat_id, "Please enter the amount:")
    bot.register_next_step_handler(msg, process_deposit_amount)

@bot.callback_query_handler(func=lambda call: call.data == "start_deposit")
def callback_deposit(call):
    bot.send_message(call.message.chat.id, "ℹ️ Here are the min you can deposit\nMin Amount: 50 ETB")
    msg = bot.send_message(call.message.chat.id, "Please enter the amount:")
    bot.register_next_step_handler(msg, process_deposit_amount)

def process_deposit_amount(message):
    chat_id = message.chat.id
    amount_text = message.text

    if not amount_text.isdigit() or int(amount_text) < 50:
        msg = bot.send_message(chat_id, "❌ Invalid amount. Please enter a number greater than or equal to 50:")
        bot.register_next_step_handler(msg, process_deposit_amount)
        return

    markup = types.InlineKeyboardMarkup()
    payment_url = f"{MINI_APP_URL}?page=deposit&amount={amount_text}"
    btn_pay = types.InlineKeyboardButton(text="Manual-Payment 📲", web_app=types.WebAppInfo(url=payment_url))
    markup.add(btn_pay)

    bot.send_message(chat_id, "Choose Deposit Method", reply_markup=markup)


# --------------------------------------------------------------------------
# 📤 3. /withdraw ሲጫኑ የሚመጣ ፍሰት
# --------------------------------------------------------------------------
@bot.message_handler(commands=['withdraw'])
def command_withdraw(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    withdraw_url = f"{MINI_APP_URL}?page=withdraw"
    btn_withdraw = types.InlineKeyboardButton(text="Open Withdraw Form 📤", web_app=types.WebAppInfo(url=withdraw_url))
    markup.add(btn_withdraw)
    
    bot.send_message(chat_id, "የማውጫ ፎርሙን ለመክፈት ከታች ያለውን ቁልፍ ይጫኑ፡", reply_markup=markup)


# --------------------------------------------------------------------------
# 🛠️ 4. አድሚኑ ቁልፎቹን ሲጫን (Approve/Reject) የሚፈጽመው ዋና ሎጂክ
# --------------------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_dep_', 'rej_dep_', 'app_wit_', 'rej_wit_')))
def handle_admin_actions(call):
    if str(call.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.answer_callback_query(call.id, "❌ ይቅርታ፣ ይህንን ትዕዛዝ ለመፈጸም ፈቃድ የለዎትም!")
        return

    action_data = call.data.split('_')
    action = action_data[0]    # 'app' ወይም 'rej'
    tx_type = action_data[1]   # 'dep' ወይም 'wit'
    target_id = int(action_data[2])  # ID ቁጥር

    # ከአዲሱ AdminActionPayload ሞዴል ጋር በሚስማማ መልኩ Payload ማዘጋጀት
    if tx_type == "dep":
        url = f"{BACKEND_URL}/api/deposit/admin/approve"
        payload = {
            "deposit_id": target_id,
            "withdraw_id": None,
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": str(ADMIN_TELEGRAM_ID)
        }
    else:
        url = f"{BACKEND_URL}/api/withdraw/admin/approve"
        payload = {
            "deposit_id": None,
            "withdraw_id": target_id,
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": str(ADMIN_TELEGRAM_ID)
        }

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
            bot.answer_callback_query(call.id, "✅ በተሳካ ሁኔታ ተፈጽሟል!")
        else:
            bot.answer_callback_query(call.id, f"❌ ስህተት፡ {res_data.get('message', 'ያልታወቀ ስህተት')}")
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ ከባክአንድ ሰርቨር ጋር መገናኘት አልተቻለም!")


# --------------------------------------------------------------------------
# 🔄 ቦቱ በቋሚነት እንዲሰራ ማድረጊያ
# --------------------------------------------------------------------------
if __name__ == "__main__":
    bot.infinity_polling()
