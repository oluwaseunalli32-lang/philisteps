import logging
import asyncio
import json
import os
import html as html_lib
from datetime import datetime
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

# Admin Telegram user IDs
ADMIN_IDS = {8297728256, 6668205975}

# ---------- Translations ----------
TEXTS = {
    "en": {
        "choose_lang": "Please choose your language:",
        "hook": "You're 1 click away to win 50,000 pesos!",
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
            "✅ Deposit 100 pesos now.\n\n"
            "Then bet twice with just 1 peso.\n\n"
            "Wait for 5 seconds and bet with 1.5 pesos "
            "which will unlock god mode on the machine.\n\n"
            "Enjoy and win now!"
        ),
        "chance_register": "This is your chance to register. Click the button below:",
        "ask_again": "Have you registered now?",
        "btn_play_now": "Play now",
        "reminders": [
            " Have you registered yet? It only takes a minute to unlock your 50,000 pesos shot!",
            " Have you spun the wheel today? Your luck could change in one spin!",
            " 50,000 pesos is still waiting for you. One click could change everything.",
            " Players are winning right now — don't miss tonight's hot streaks!",
            "⏰ Quick reminder: your 50,000 pesos bonus is still available. Tap below to claim it!",
            " Ready to play like a pro? Register now and I'll send you the winning game.",
            " Your free entry hasn't been used yet — 50,000 pesos could be yours today!",
            " Didn't you want to win today? One tap is all it takes to get started.",
        ],
    },
    "tl": {
        "choose_lang": "Pumili ng wika:",
        "hook": "Isang click na lang ang layo mo sa ₱50,000!",
        "click_register": "Pindutin ang button sa ibaba para mag-register:",
        "btn_register": "Mag-register dito",
        "ask_registered": "Nakapag-register ka na ba para masabi ko sa'yo kung anong laro ang pwedeng magpanalo sa'yo ng ₱50,000?",
        "btn_yes": "Oo, laro na tayo!",
        "btn_no": "Hindi pa",
        "slot_intro": "Ito ang slot machine na pwede mong laruin.",
        "slot_caption": "Narito ang slot machine.",
        "slot_found_btn": "Nakita ko na",
        "slot_found_text": "Kapag nakita mo na, i-click ang button sa ibaba para magpatuloy.",
        "instructions": (
            "✅ Mag-deposit ng 100 pesos ngayon.\n\n"
            "Pagkatapos, mag-bet ng dalawang beses gamit ang 1 peso.\n\n"
            "Maghintay ng 5 segundo at mag-bet ng 1.5 pesos "
            "para ma-unlock ang god mode sa machine.\n\n"
            "Mag-enjoy at manalo na!"
        ),
        "chance_register": "Ito na ang pagkakataon mo para mag-register. I-click ang button sa ibaba:",
        "ask_again": "Naka-register ka na ba ngayon?",
        "btn_play_now": "Maglaro na",
        "reminders": [
            " Naka-register ka na ba? Isang minuto lang para ma-unlock ang 50,000 pesos!",
            " Nag-spin ka na ba ng wheel ngayong araw? Baka mabago ng isang spin ang swerte mo!",
            " Hinihintay ka pa rin ng 50,000 pesos. Isang click lang ang katapat.",
            " Maraming nananalo ngayon — huwag palampasin ang magandang streak ngayong gabi!",
            "⏰ Paalala lang: available pa ang 50,000 pesos bonus mo. I-tap sa ibaba para makuha!",
            " Ready ka na bang maglaro? Mag-register na at ipapadala ko ang panalong laro.",
            " Hindi mo pa nagagamit ang free entry mo — baka mapasaiyo na ang 50,000 pesos ngayon!",
            " Hindi mo ba gustong manalo ngayon? Isang tap lang para makapagsimula.",
        ],
    },
}

# ---------- Helpers ----------
def _esc(s) -> str:
    return html_lib.escape(str(s)) if s is not None else ""

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
        json.dump(users, f, ensure_ascii=False, indent=2)

def _user_lang(entry) -> str:
    """Read a language from either a legacy string entry or a dict entry."""
    if isinstance(entry, dict):
        return entry.get("lang") or "en"
    if entry:
        return entry
    return "en"

def _user_info(entry) -> dict:
    """Normalize legacy entries into the new dict shape."""
    if isinstance(entry, dict):
        return entry
    return {
        "lang": entry,
        "username": None,
        "first_name": None,
        "started_at": None,
    }

def register_user(chat_id: int, lang: str, context: ContextTypes.DEFAULT_TYPE):
    users = context.application.bot_data.setdefault("users", {})
    uid = str(chat_id)
    entry = users.get(uid)
    if isinstance(entry, dict):
        entry["lang"] = lang
    else:
        users[uid] = {"lang": lang}
    save_users(users)

# ---------- Message tracking & deletion ----------
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
        except Exception:
            pass
    context.user_data["msg_ids"] = [
        m for m in context.user_data.get("msg_ids", []) if m in keep
    ]

# ---------- Admin helpers ----------
async def notify_admins_new_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user):
    username = f"@{user.username}" if getattr(user, "username", None) else "(no username)"
    full_name = " ".join(
        filter(None, [getattr(user, "first_name", None), getattr(user, "last_name", None)])
    ) or "(no name)"
    text = (
        "🆕 <b>New user started the bot</b>\n\n"
        f"🆔 ID: <code>{chat_id}</code>\n"
        f"👤 Username: {_esc(username)}\n"
        f"📝 Name: {_esc(full_name)}\n"
        f"🕐 Time: {datetime.now(MANILA_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    for admin_id in ADMIN_IDS:
        if admin_id == chat_id:
            continue
        try:
            await context.bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")

async def send_user_list_to_admin(context: ContextTypes.DEFAULT_TYPE, admin_chat_id: int):
    users = context.application.bot_data.get("users", {})
    total = len(users)
    if total == 0:
        await context.bot.send_message(admin_chat_id, "👥 No users have started the bot yet.")
        return

    lines = [f"👥 <b>Total users: {total}</b>"]
    for i, (uid, raw) in enumerate(users.items(), 1):
        info = _user_info(raw)
        uname = f"@{_esc(info['username'])}" if info.get("username") else "(no username)"
        name = _esc(info.get("first_name") or "")
        lang = info.get("lang") or "—"
        tag = " [ADMIN]" if int(uid) in ADMIN_IDS else ""
        lines.append(f"{i}. {uname} — <code>{uid}</code> — {name} — lang: {lang}{tag}")

    text = "\n".join(lines)

    # Split into chunks under Telegram's 4096-char limit (per line, keeps HTML valid)
    if len(text) <= 4000:
        await context.bot.send_message(admin_chat_id, text, parse_mode="HTML")
        return

    chunks, current = [], ""
    for line in lines:
        candidate = (current + "\n" + line) if current else line
        if len(candidate) > 4000 and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)

    for chunk in chunks:
        await context.bot.send_message(admin_chat_id, chunk, parse_mode="HTML")

async def admin_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Refreshing…")
    await send_user_list_to_admin(context, query.message.chat_id)

async def admin_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point — admin chooses to go through the normal user flow."""
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass
    context.user_data.clear()
    return await _send_language_selection(query.message.chat_id, context)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ADMIN_IDS:
        await update.message.reply_text("This command is admin-only.")
        return
    await send_user_list_to_admin(context, chat_id)

# ---------- Flow Functions ----------
async def _send_language_selection(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Tagalog", callback_data="lang_tl"),
        ]
    ]
    m = await context.bot.send_message(
        chat_id,
        "Please choose your language / Pumili ng wika:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m, context)
    return CHOOSE_LANG

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"!!! START COMMAND RECEIVED FROM {update.effective_user.id} !!!")
    context.user_data.clear()
    try:
        if update.message:
            await update.message.delete()
    except Exception:
        pass

    chat_id = update.effective_chat.id
    user = update.effective_user

    # Track / register the user, notify admins if this is a brand-new start
    users = context.application.bot_data.setdefault("users", {})
    uid = str(chat_id)
    if uid not in users:
        users[uid] = {
            "lang": None,
            "username": getattr(user, "username", None),
            "first_name": getattr(user, "first_name", None),
            "started_at": datetime.now(MANILA_TZ).isoformat(),
        }
        save_users(users)
        if chat_id not in ADMIN_IDS:
            await notify_admins_new_user(context, chat_id, user)

    # Admin on /start gets the current user list + controls
    if chat_id in ADMIN_IDS:
        await send_user_list_to_admin(context, chat_id)
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh list", callback_data="admin_refresh")],
            [InlineKeyboardButton("▶️ Proceed as user", callback_data="admin_proceed")],
        ]
        await context.bot.send_message(
            chat_id,
            "Admin controls:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    return await _send_language_selection(chat_id, context)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = "en" if query.data == "lang_en" else "tl"
    context.user_data["lang"] = lang
    register_user(chat_id, lang, context)
    t = TEXTS[lang]
    new_ids = set()
    m1 = await context.bot.send_message(chat_id, t["hook"])
    await track(m1, context)
    new_ids.add(m1.message_id)
    await asyncio.sleep(2)
    keyboard = [[InlineKeyboardButton(t["btn_register"], url=REGISTER_URL)]]
    m2 = await context.bot.send_message(
        chat_id,
        t["click_register"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m2, context)
    new_ids.add(m2.message_id)
    await asyncio.sleep(4)
    keyboard = [
        [
            InlineKeyboardButton(t["btn_yes"], callback_data="registered_yes"),
            InlineKeyboardButton(t["btn_no"], callback_data="registered_no"),
        ]
    ]
    m3 = await context.bot.send_message(
        chat_id,
        t["ask_registered"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m3, context)
    new_ids.add(m3.message_id)
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
    await track(m, context)
    new_ids.add(m.message_id)
    try:
        with open(SLOT_IMAGE_PATH, "rb") as photo:
            m = await context.bot.send_photo(chat_id, photo=photo, caption=t["slot_caption"])
    except FileNotFoundError:
        logger.warning(f"{SLOT_IMAGE_PATH} missing - sending text fallback.")
        m = await context.bot.send_message(chat_id, "[Image missing]")
    await track(m, context)
    new_ids.add(m.message_id)
    keyboard = [[InlineKeyboardButton(t["slot_found_btn"], callback_data="found_it")]]
    m = await context.bot.send_message(
        chat_id,
        t["slot_found_text"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m, context)
    new_ids.add(m.message_id)
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
        chat_id,
        t["chance_register"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m, context)
    new_ids.add(m.message_id)
    keyboard = [
        [
            InlineKeyboardButton(t["btn_yes"], callback_data="registered_yes"),
            InlineKeyboardButton(t["btn_no"], callback_data="registered_no"),
        ]
    ]
    m = await context.bot.send_message(
        chat_id,
        t["ask_again"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    await track(m, context)
    new_ids.add(m.message_id)
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

async def handle_reminder_play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass
    context.user_data.clear()
    return await _send_language_selection(query.message.chat_id, context)

# ---------- Reminder ----------
async def send_rotating_reminder(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    idx = app.bot_data.get("reminder_index", 0)
    users = app.bot_data.get("users", {})
    if not users:
        return
    logger.info(f"Sending reminder index {idx} to {len(users)} users.")
    for chat_id_str, raw in users.items():
        lang = _user_lang(raw)
        lang_data = TEXTS.get(lang, TEXTS["en"])
        text = lang_data["reminders"][idx % len(lang_data["reminders"])]
        keyboard = [
            [InlineKeyboardButton(lang_data["btn_register"], url=REGISTER_URL)],
            [InlineKeyboardButton(lang_data["btn_play_now"], callback_data="reminder_play")],
        ]
        try:
            await context.bot.send_message(
                int(chat_id_str), text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.warning(f"Reminder failed for {chat_id_str}: {e}")
    app.bot_data["reminder_index"] = (idx + 1) % 8

# ---------- Main (Polling) ----------
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
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(admin_proceed, pattern="^admin_proceed$"),
            CallbackQueryHandler(handle_reminder_play, pattern="^reminder_play$"),
        ],
        states={
            CHOOSE_LANG: [
                CallbackQueryHandler(set_language, pattern="^lang_(en|tl)$"),
            ],
            ASK_REGISTERED: [
                CallbackQueryHandler(handle_registered_yes, pattern="^registered_yes$"),
                CallbackQueryHandler(handle_registered_no, pattern="^registered_no$"),
            ],
            SLOT_MACHINE: [
                CallbackQueryHandler(handle_found_it, pattern="^found_it$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),  # allow /start mid-conversation to reset
        ],
        per_message=False,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CallbackQueryHandler(admin_refresh, pattern="^admin_refresh$"))

    if application.job_queue:
        application.job_queue.run_repeating(
            send_rotating_reminder,
            interval=18000,
            first=60,
            name="five_hour_rotating_reminder",
        )

    logger.info("Bot starting (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
