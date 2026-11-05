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
ASK_REGISTERED, SLOT_MACHINE = range(2)
USERS_FILE = "users.json"
MANILA_TZ = ZoneInfo("Asia/Manila")
REGISTER_URL = "https://example.com/register"   # 🔁 REPLACE WITH YOUR URL

# ⬇️ CHANGE THIS if your file is named slot_machine.jpg instead
SLOT_IMAGE_PATH = "slot_machine.jpeg"

# ---------- Rotating reminder messages ----------
REMINDERS = [
    "🤔 Have you registered yet? It only takes a minute to unlock your 50,000 pesos shot!",
    "🎰 Have you spun the wheel today? Your luck could change in one spin!",
    "💰 50,000 pesos is still waiting for you. One click could change everything.",
    "🔥 Players are winning right now — don't miss tonight's hot streaks!",
    "⏰ Quick reminder: your 50,000 pesos bonus is still available. Tap below to claim it!",
    "🏆 Ready to play like a pro? Register now and I'll send you the winning game.",
    "🎁 Your free entry hasn't been used yet — 50,000 pesos could be yours today!",
    "👀 Didn't you want to win today? One tap is all it takes to get started.",
]

# ---------- User persistence ----------
def load_users() -> set:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_users(users: set):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

def register_user(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    users = context.application.bot_data.setdefault("users", set())
    if chat_id not in users:
        users.add(chat_id)
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
            logger.warning(f"Could not delete message {mid}: {e}")
    context.user_data["msg_ids"] = [m for m in context.user_data.get("msg_ids", []) if m in keep]

# ---------- Conversation handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"/start from {user.id}")
    register_user(user.id, context)
    context.user_data.clear()

    try:
        await update.message.delete()
    except Exception:
        pass

    chat_id = update.effective_chat.id

    m1 = await context.bot.send_message(chat_id, "You're 1 click away from getting 50,000 pesos!")
    await track(m1, context)

    await asyncio.sleep(2)
    keyboard = [[InlineKeyboardButton("Click here to register", url=REGISTER_URL)]]
    m2 = await context.bot.send_message(
        chat_id,
        "Click the button below to register:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m2, context)

    await asyncio.sleep(4)
    keyboard = [[
        InlineKeyboardButton("Yes, let's play", callback_data="registered_yes"),
        InlineKeyboardButton("No, I haven't", callback_data="registered_no"),
    ]]
    m3 = await context.bot.send_message(
        chat_id,
        "Have you registered so I can send you which game to play to win 50,000 pesos?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m3, context)
    return ASK_REGISTERED


async def handle_registered_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    new_ids = set()

    m = await context.bot.send_message(chat_id, "This is the slot machine to play.")
    await track(m, context); new_ids.add(m.message_id)

    # Send the JPEG file
    try:
        with open(SLOT_IMAGE_PATH, "rb") as photo:
            m = await context.bot.send_photo(
                chat_id,
                photo=photo,
                caption="Here is the slot machine.",
            )
    except FileNotFoundError:
        logger.error(f"{SLOT_IMAGE_PATH} missing — sending text fallback.")
        m = await context.bot.send_message(chat_id, "[Image of slot machine would appear here]")
    await track(m, context); new_ids.add(m.message_id)

    keyboard = [[InlineKeyboardButton("Found it", callback_data="found_it")]]
    m = await context.bot.send_message(
        chat_id,
        "Once you find it, click the button below to proceed.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m, context); new_ids.add(m.message_id)

    await delete_old_messages(context, chat_id, keep=new_ids)
    return SLOT_MACHINE


async def handle_registered_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    new_ids = set()

    keyboard = [[InlineKeyboardButton("Click here to register", url=REGISTER_URL)]]
    m = await context.bot.send_message(
        chat_id,
        "This is your chance to register. Click the button below:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m, context); new_ids.add(m.message_id)

    keyboard = [[
        InlineKeyboardButton("Yes, let's play", callback_data="registered_yes"),
        InlineKeyboardButton("No, I haven't", callback_data="registered_no"),
    ]]
    m = await context.bot.send_message(
        chat_id,
        "Have you registered now?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m, context); new_ids.add(m.message_id)

    await delete_old_messages(context, chat_id, keep=new_ids)
    return ASK_REGISTERED


async def handle_found_it(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    instructions = (
        "✅ <b>Deposit 100 pesos now.</b>\n\n"
        "Then bet twice with just <b>1 peso</b>.\n\n"
        "Wait for 5 seconds and bet with <b>1.5 pesos</b> "
        "which will unlock god mode on the machine.\n\n"
        "Enjoy and win now!"
    )
    m = await context.bot.send_message(chat_id, instructions, parse_mode="HTML")
    await track(m, context)

    await delete_old_messages(context, chat_id, keep={m.message_id})
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ---------- Rotating 5-hour reminder ----------
async def send_rotating_reminder(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    idx = app.bot_data.get("reminder_index", 0)
    text = REMINDERS[idx % len(REMINDERS)]
    app.bot_data["reminder_index"] = (idx + 1) % len(REMINDERS)

    logger.info(f"Reminder #{idx + 1}/{len(REMINDERS)} — sending to {len(app.bot_data.get('users', []))} user(s).")

    keyboard = [
        [InlineKeyboardButton("Click here to register", url=REGISTER_URL)],
        [InlineKeyboardButton("Play now", callback_data="reminder_play")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    users = list(app.bot_data.get("users", set()))
    for chat_id in users:
        try:
            await context.bot.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"Reminder failed for {chat_id}: {e}")


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

    # Warn early if image is missing so it doesn't fail silently in production
    if not os.path.exists(SLOT_IMAGE_PATH):
        logger.warning(f"⚠️  {SLOT_IMAGE_PATH} not found in project root — bot will send a text fallback.")

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
            first=60,         # first ping 60s after boot (for testing)
            name="five_hour_rotating_reminder",
        )

    logger.info("Bot starting (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
