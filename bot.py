import logging
import asyncio
import json
import os
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    Defaults,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Constants ----------
CHOOSE_LANG, ASK_REGISTERED, SLOT_MACHINE = range(3)
USERS_FILE = "users.json"
MANILA_TZ = ZoneInfo("Asia/Manila")
REGISTER_URL = "https://qtfeh.777haha.cloud/register.html"
SLOT_IMAGE_PATH = "slot_machine.jpeg"

# ---------- Translations ----------
TEXTS = {
    "en": {
        "choose_lang": "Please choose your language:",
        "hook": "You're 1 click away from getting 50,000 pesos!",
        "click_register": "Click the button below to register:",
        "btn_register": "Click here to register",
        "ask_registered": "Have you registered so I can send you which game to play to win 50,000 pesos?",
        "btn_yes": "Yes, let's play",
        "btn_no": "No, I haven't",
        "slot_intro": "This is the slot machine to play.",
        "slot_caption": "Here is the slot machine.",
        "slot_found_btn": "Found it",
        "slot_found_text": "Once you find it, click the button below to proceed.",
        "instructions": (
            "✅ <b>Deposit 100 pesos now.</b>\n\n"
            "Then bet twice with just <b>1 peso</b>.\n\n"
            "Wait for 5 seconds and bet with <b>1.5 pesos</b> "
            "which will unlock god mode on the machine.\n\n"
            "Enjoy and win now!"
        ),
        "chance_register": "This is your chance to register. Click the button below:",
        "ask_again": "Have you registered now?",
        "btn_play_now": "Play now",
        "reminders": [
            "🤔 Have you registered yet? It only takes a minute to unlock your 50,000 pesos shot!",
            "🎰 Have you spun the wheel today? Your luck could change in one spin!",
            "💰 50,000 pesos is still waiting for you. One click could change everything.",
            "🔥 Players are winning right now — don't miss tonight's hot streaks!",
            "⏰ Quick reminder: your 50,000 pesos bonus is still available. Tap below to claim it!",
            "🏆 Ready to play like a pro? Register now and I'll send you the winning game.",
            "🎁 Your free entry hasn't been used yet — 50,000 pesos could be yours today!",
            "👀 Didn't you want to win today? One tap is all it takes to get started."
        ]
    },
    "tl": {
        "choose_lang": "Pumili ng wika:",
        "hook": "Isa ka na lang na click ang layo sa pagkuha ng 50,000 pesos!",
        "click_register": "I-click ang button sa ibaba para mag-register:",
        "btn_register": "Mag-register dito",
        "ask_registered": "Naka-register ka na ba para mapadala ko kung anong laro ang pwede mong laruin para manalo ng 50,000 pesos?",
        "btn_yes": "Oo, maglaro na tayo",
        "btn_no": "Hindi pa",
        "slot_intro": "Ito ang slot machine na pwede mong laruin.",
        "slot_caption": "Narito ang slot machine.",
        "slot_found_btn": "Nakita ko na",
        "slot_found_text": "Kapag nakita mo na, i-click ang button sa ibaba para magpatuloy.",
        "instructions": (
            "✅ <b>Mag-deposit ng 100 pesos ngayon.</b>\n\n"
            "Pagkatapos, mag-bet ng dalawang beses gamit ang <b>1 peso</b>.\n\n"
            "Maghintay ng 5 segundo at mag-bet ng <b>1.5 pesos</b> "
            "para ma-unlock ang god mode sa machine.\n\n"
            "Mag-enjoy at manalo na!"
        ),
        "chance_register": "Ito na ang pagkakataon mo para mag-register. I-click ang button sa ibaba:",
        "ask_again": "Naka-register ka na ba ngayon?",
        "btn_play_now": "Maglaro na",
        "reminders": [
            "🤔 Naka-register ka na ba? Isang minuto lang para ma-unlock ang 50,000 pesos!",
            "🎰 Nag-spin ka na ba ng wheel ngayong araw? Baka mabago ng isang spin ang swerte mo!",
            "💰 Hinihintay ka pa rin ng 50,000 pesos. Isang click lang ang katapat.",
            "🔥 Maraming nananalo ngayon — huwag palampasin ang magandang streak ngayong gabi!",
            "⏰ Paalala lang: available pa ang 50,000 pesos bonus mo. I-tap sa ibaba para makuha!",
            "🏆 Ready ka na bang maglaro? Mag-register na at ipapadala ko ang panalong laro.",
            "🎁 Hindi mo pa nagagamit ang free entry mo — baka mapasaiyo na ang 50,000 pesos ngayon!",
            "👀 Hindi mo ba gustong manalo ngayon? Isang tap lang para makapagsimula."
        ]
    }
}

# ---------- User persistence (Now stores Chat ID -> Language) ----------
def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def register_user(chat_id: int, lang: str, context: ContextTypes.DEFAULT_TYPE):
    users = context.application.bot_data.setdefault("users", {})
    users[str(chat_id)] = lang  # JSON keys must be strings
    save_users(users)

# ---------- Message tracking ----------
async def track(msg, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("msg_ids", []).append(msg.message_id)
    return msg

async def delete_old_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int, keep=None):
    keep = keep or set()
    for mid in list(context.user_data.get("msg_ids", [])):
        if mid in keep:
            continue
        try:
            await context.bot.delete_message(chat_id, mid)
        except Exception as e:
            pass # Ignore errors if message is already deleted or too old
    context.user_data["msg_ids"] = [m for m in context.user_data.get("msg_ids", []) if m in keep]

# ---------- Flow Functions ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: Asks for language first."""
    user = update.effective_user
    logger.info(f"/start from {user.id}")
    context.user_data.clear()

    try:
        await update.message.delete()
    except Exception:
        pass

    chat_id = update.effective_chat.id

    # Language selection buttons
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Tagalog", callback_data="lang_tl")
        ]
    ]
    m = await context.bot.send_message(
        chat_id,
        "Please choose your language / Pumili ng wika:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await track(m, context)
    return CHOOSE_LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves language and begins the actual flow."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    # Determine language from callback data
    lang = "en" if query.data == "lang_en" else "tl"
    context.user_data["lang"] = lang
    register_user(chat_id, lang, context)
    
    # Get text based on language
    t = TEXTS[lang]
    new_ids = set()

    # 1) Hook message
    m1 = await context.bot.send_message(chat_id, t["hook"])
    await track(m1, context); new_ids.add(m1.message_id)

    # 2) Wait 2s -> register button
    await asyncio.sleep(2)
    keyboard = [[InlineKeyboardButton(t["btn_register"], url=REGISTER_URL)]]
    m2 = await context.bot.send_message(
        chat_id, t["click_register"], reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await track(m2, context); new_ids.add(m2.message_id)

    # 3) Wait 4s -> Yes/No buttons
    await asyncio.sleep(4)
    keyboard = [[
        InlineKeyboardButton(t["btn_yes"], callback_data="registered_yes"),
        InlineKeyboardButton(t["btn_no"], callback_data="registered_no"),
    ]]
    m3 = await context.bot.send_message(
        chat_id, t["ask_registered"], reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await track(m3, context); new_ids.add(m3.message_id)

    # Delete the language selection prompt and previous messages
    await delete_old_messages(context, chat_id, keep=new_ids)
    return ASK_REGISTERED

async def handle_registered_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = context.user_data.get("lang", "en")
    t = TEXTS[lang]
    
    new_ids = set()

    m = await context.bot.send_message(chat_id, t["slot_intro"])
    await track(m, context); new_ids.add(m.message_id)

    try:
        with open(SLOT_IMAGE_PATH, "rb") as photo:
            m = await context.bot.send_photo(chat_id, photo=photo, caption=t["slot_caption"])
    except FileNotFoundError:
        m = await context.bot.send_message(chat_id, "[Image missing]")
    await track(m, context); new_ids.add(m.message_id)

    keyboard = [[InlineKeyboardButton(t["slot_found_btn"], callback_data="found_it")]]
    m = await context.bot.send_message(
        chat_id, t["slot_found_text"], reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await track(m, context); new_ids.add(m.message_id)

    await delete_old_messages(context, chat_id, keep=new_ids)
    return SLOT_MACHINE

async def handle_registered_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = context.user_data.get("lang", "en")
    t = TEXTS[lang]
    
    new_ids = set()

    keyboard = [[InlineKeyboardButton(t["btn_register"], url=REGISTER_URL)]]
    m = await context.bot.send_message(
        chat_id, t["chance_register"], reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await track(m, context); new_ids.add(m.message_id)

    keyboard = [[
        InlineKeyboardButton(t["btn_yes"], callback_data="registered_yes"),
        InlineKeyboardButton(t["btn_no"], callback_data="registered_no"),
    ]]
    m = await context.bot.send_message(
        chat_id, t["ask_again"], reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await track(m, context); new_ids.add(m.message_id)

    await delete_old_messages(context, chat_id, keep=new_ids)
    return ASK_REGISTERED

async def handle_found_it(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = context.user_data.get("lang", "en")
    t = TEXTS[lang]

    m = await context.bot.send_message(chat_id, t["instructions"], parse_mode="HTML")
    await track(m, context)

    await delete_old_messages(context, chat_id, keep={m.message_id})
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# ---------- Reminder ----------
async def send_rotating_reminder(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    idx = app.bot_data.get("reminder_index", 0)
    
    users = app.bot_data.get("users", {})
    if not users:
        return

    # Log which reminder number we are on
    logger.info(f"Sending reminder index {idx} to {len(users)} users.")
    
    for chat_id_str, lang in users.items():
        lang_data = TEXTS.get(lang, TEXTS["en"]) # Fallback to English if lang missing
        text = lang_data["reminders"][idx % len(lang_data["reminders"])]
        
        keyboard = [
            [InlineKeyboardButton(lang_data["btn_register"], url=REGISTER_URL)],
            [InlineKeyboardButton(lang_data["btn_play_now"], callback_data="reminder_play")],
        ]
        
        try:
            await context.bot.send_message(
                int(chat_id_str), 
                text, 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.warning(f"Reminder failed for {chat_id_str}: {e}")

    # Increment index for the next round (5 hours later)
    app.bot_data["reminder_index"] = (idx + 1) % 8

async def handle_reminder_play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass
    return await start(update, context)

# ---------- Main ----------
def main() -> None:
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN env var is not set.")

    application = (
        Application.builder()
        .token(TOKEN)
        .defaults(Defaults(tzinfo=MANILA_TZ))
        .build()
    )

    application.bot_data["users"] = load_users()
    application.bot_data["reminder_index"] = 0

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_LANG: [
                CallbackQueryHandler(set_language, pattern="^lang_(en|tl)$"),
            ],
            ASK_REGISTERED: [
                CallbackQueryHandler(handle_registered_yes, pattern="^registered_yes$"),
                CallbackQueryHandler(handle_registered_no,  pattern="^registered_no$"),
            ],
            SLOT_MACHINE: [
                CallbackQueryHandler(handle_found_it, pattern="^found_it$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_reminder_play, pattern="^reminder_play$"))

    if application.job_queue:
        application.job_queue.run_repeating(
            send_rotating_reminder,
            interval=18000,   # 5 hours
            first=60,         # First ping 60s after boot (for testing)
            name="five_hour_rotating_reminder",
        )

    logger.info("Bot starting (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
