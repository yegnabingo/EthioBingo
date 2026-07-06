import os
import requests
from telebot import TeleBot, types

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (Configuration)
# --------------------------------------------------------------------------
# 💡 [ማስታወሻ] የአንተን ቦት ቶክን እና የቴሌግራም ID ቁጥርህን እዚህ አስገባ
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # ከ BotFather ያገኘኸውን ቶክን እዚህ ተካ
ADMIN_TELEGRAM_ID = "YOUR_PERSONAL_TELEGRAM_ID"  # የአንተን የቴሌግራም ID ቁጥር እዚህ ተካ

# የ FastAPI Backend ዩአርኤል (URL) - Railway ላይ ሲሆን የረይልዌይ ሊንክህን ታደርገዋለህ
BACKEND_URL = "http://127.0.0.1:8000"  

bot = TeleBot(BOT_TOKEN)

print("🎰 የቢንጎ ቴሌግራም ቦት በሰላም ስራ ጀምሯል...")

# --------------------------------------------------------------------------
# 🚀 1. ተጫዋቾች ቦቱን ሲያስጀምሩ (/start) የሚኒ አፑን ሊንክ መላኪያ
# --------------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    # 🎰 ተጫዋቾች በቀጥታ ወደ ቢንጎ ጌሙ የሚገቡበት የ Web App ቁልፍ ማዘጋጀት
    markup = types.InlineKeyboardMarkup()
    # የጌምህን የፊት ገጽ ሊንክ (Frontend Web Link) እዚህ "URL_TO_YOUR_MINI_APP" በሚለው ተካው
    mini_app_url = "https://your-bingo-frontend-link.web.app" 
    
    game_button = types.InlineKeyboardButton(
        text="🎰 ቢንጎ ተጫወት (Play Bingo)", 
        web_app=types.WebAppInfo(url=mini_app_url)
    )
    markup.add(game_button)

    welcome_text = (
        f"እንኳን ደህና መጡ {user_name} ወደ እውነተኛው የኢትዮጵያ ቢንጎ ካሲኖ (Bingo Casino)! 🇪🇹✨\n\n"
        "ከታች ያለውን ቁልፍ ተጭነው መጫወት እና ማሸነፍ ይችላሉ። መልካም እድል!"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=markup)


# --------------------------------------------------------------------------
# 🛠️ 2. አድሚኑ ቁልፎቹን ሲጫን (Approve/Reject) የሚፈጽመው ዋና ሎጂክ
# --------------------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_dep_', 'rej_dep_', 'app_wit_', 'rej_wit_')))
def handle_admin_actions(call):
    # 🔒 የደህንነት ማረጋገጫ፡ ጥያቄው የመጣው ከትክክለኛው አድሚን መሆኑን ቼክ ማድረግ
    if str(call.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.answer_callback_query(call.id, "❌ ይቅርታ፣ ይህንን ትዕዛዝ ለመፈጸም ፈቃድ የለዎትም!")
        return

    # መረጃውን መበተን (ለምሳሌ፦ app_dep_5 -> ['app', 'dep', '5'])
    action_data = call.data.split('_')
    action = action_data[0]    # 'app' (Approve) ወይም 'rej' (Reject)
    tx_type = action_data[1]   # 'dep' (Deposit) ወይም 'wit' (Withdraw)
    target_id = action_data[2]  # የዲፖዚት ወይም የዊዝድሮው ሰንጠረዥ ID ቁጥር

    # ሀ. ለዲፖዚት (ገንዘብ ማስገቢያ) ማጽደቂያ ከሆነ
    if tx_type == "dep":
        url = f"{BACKEND_URL}/api/deposit/admin/approve"
        payload = {
            "deposit_id": int(target_id),
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": str(ADMIN_TELEGRAM_ID)
        }
    # ለ. ለዊዝድሮው (ገንዘብ ማውጫ) ማጽደቂያ ከሆነ
    else:
        url = f"{BACKEND_URL}/api/withdraw/admin/approve"
        payload = {
            "withdraw_id": int(target_id),
            "action": "APPROVE" if action == "app" else "REJECT",
            "admin_telegram_id": str(ADMIN_TELEGRAM_ID)
        }

    # 🔗 ጥያቄውን ወደ FastAPI Backend መላክ
    try:
        response = requests.post(url, json=payload)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("success"):
            status_text = "🟢 ተቀብለህ አጽድቀኸዋል (APPROVED)" if action == "app" else "🔴 ውድቅ አድርገኸዋል (REJECTED)"
            
            # አድሚኑ የመረጠውን ውሳኔ እዛው መልዕክቱ ላይ ማሳየት (እንዳይደጋገም ቁልፎቹን ማጥፋት)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{call.message.text}\n\n<b>🔄 የውሳኔ ሁኔታ፦ {status_text}!</b>",
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "✅ በተሳካ ሁኔታ ተፈጽሟል!")
        else:
            error_msg = res_data.get('message', 'ያልታወቀ ስህተት')
            bot.answer_callback_query(call.id, f"❌ ስህተት ሰርቨር ላይ ተፈጥሯል፡ {error_msg}")
            
    except Exception as e:
        print(f"የአድሚን ውሳኔ ስህተት፡ {str(e)}")
        bot.answer_callback_query(call.id, "❌ ከባክአንድ (Backend) ሰርቨር ጋር መገናኘት አልተቻለም!")


# --------------------------------------------------------------------------
# 🔄 ቦቱ በቋሚነት እንዲሰራ እና መልዕክቶችን እንዲያዳምጥ ማድረግ
# --------------------------------------------------------------------------
if __name__ == "__main__":
    bot.infinity_polling()
ከ
