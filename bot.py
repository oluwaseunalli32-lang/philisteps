import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Configuration ----------
URL = "https://qtfeh.777haha.cloud/register.html"

# Updated to use HA1.jpg through HA5.jpg
MESSAGES = [
    {
        "text": (
            "🎁 WELCOME BONUS ALERT!\n\n"
            "New player ka ba? May welcome treat para sa'yo! 🎉\n\n"
            "Sa halagang P100 deposit, puwede kang maging eligible sa up to P15,000 Welcome Bonus! 💰\n\n"
            "Check mo na ang promo mechanics para malaman kung paano mag-claim!"
        ),
        "button": "Try your luck",
        "image": "HA1.jpg"
    },
    {
        "text": (
            "🎰 WEEKEND GAMING VIBES!\n\n"
            "Weekend na! Time na para mag-relax at i-enjoy ang favorite games mo! 🔥\n\n"
            "Maraming exciting games ang puwede mong subukan. Baka mahanap mo na ang bago mong favorite! 🍀"
        ),
        "button": "Our website",
        "image": "HA2.jpg"
    },
    {
        "text": (
            "💎 100% DEPOSIT BONUS!\n\n"
            "Gusto mo ng extra gaming credits? May bonus offer para sa'yo! 🎁\n\n"
            "Mag-deposit at puwedeng makakuha ng up to 100% Deposit Bonus sa qualifying deposits!\n\n"
            "Check muna ang promo terms para alam mo kung magkano ang bonus na puwede mong makuha."
        ),
        "button": "Try your luck",
        "image": "HA3.jpg"
    },
    {
        "text": (
            "🐉 FLOATING DRAGON — BIG WIN HIGHLIGHT!\n\n"
            "🔥 P1 BET, P300,000 WIN!\n\n"
            "Grabe ang featured winning result sa Floating Dragon Hold & Spin Mobile! 💸\n\n"
            "Sa halagang P1 bet, umabot sa P300,000 ang ipinakitang panalo!\n\n"
            "Check out the game at enjoy the spins! 🎰"
        ),
        "button": "Our website",
        "image": "HA4.jpg"
    },
    {
        "text": (
            "💎 ETERNAL DIAMONDS — WIN HIGHLIGHT!\n\n"
            "🔥 P5 BET, P350,000 WIN!\n\n"
            "Solid ang featured result sa Eternal Diamonds! ✨\n\n"
            "Imagine, P5 ang bet at umabot sa P350,000 ang winning result na ipinakita!\n\n"
            "Tingnan ang game at alamin kung bakit exciting itong laruin! 🎰"
        ),
        "button": "Try your luck",
        "image": "HA5.jpg"
    }
]

# ---------- Core Functions ----------

async def send_promo_message(context: ContextTypes.DEFAULT_TYPE):
    """Sends a specific message from the list based on the job's data index."""
    job = context.job
    chat_id = job.chat_id
    index = job.data["index"]
    
    if index >= len(MESSAGES):
        return

    msg = MESSAGES[index]
    keyboard = [[InlineKeyboardButton(msg["button"], url=URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Construct the absolute path to ensure it works on Render
        image_path = os.path.join(os.path.dirname(__file__), msg["image"])
        with open(image_path, "rb") as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=msg["text"],
                reply_markup=reply_markup
            )
            logger.info(f"Sent message {index + 1}/5 to {chat_id}")
    except FileNotFoundError:
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg["text"],
            reply_markup=reply_markup
        )
        logger.warning(f"Image {msg['image']} not found. Sent text only to {chat_id}.")
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")

    # Schedule the NEXT message 1 hour later (3600 seconds)
    if index + 1 < len(MESSAGES):
        context.job_queue.run_once(
            send_promo_message,
            when=3600,
            chat_id=chat_id,
            data={"index": index + 1},
            name=f"promo_{chat_id}_{index+1}"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when a user sends /start"""
    chat_id = update.effective_chat.id
    
    # Cancel ALL existing jobs for this user to prevent double-spamming
    for job in context.job_queue.jobs():
        if getattr(job, 'chat_id', None) == chat_id:
            job.schedule_removal()

    # Send the very first message immediately
    context.job_queue.run_once(
        send_promo_message,
        when=0,
        chat_id=chat_id,
        data={"index": 0},
        name=f"promo_start_{chat_id}_0"
    )
    
    # Schedule the sequence to restart exactly 24 hours from now (86400 seconds)
    context.job_queue.run_repeating(
        restart_daily_sequence,
        interval=86400,
        first=86400,
        chat_id=chat_id,
        name=f"daily_reset_{chat_id}"
    )

async def restart_daily_sequence(context: ContextTypes.DEFAULT_TYPE):
    """Triggers the first message again the next day."""
    job = context.job
    chat_id = job.chat_id
    
    context.job_queue.run_once(
        send_promo_message,
        when=0,
        chat_id=chat_id,
        data={"index": 0},
        name=f"promo_daily_{chat_id}_0"
    )

# ---------- Main ----------
def main() -> None:
    # Render uses environment variables, this is the standard way to get the token
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    logger.info("Promo bot is starting (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
