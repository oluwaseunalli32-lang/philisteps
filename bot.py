import logging
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Educational Content ----------
LESSONS = {
    "math": {
        "title": "Basic Algebra",
        "content": (
            "An equation is a statement that two expressions are equal.\n\n"
            "Example: 2x + 3 = 7\n"
            "To solve for x, subtract 3 from both sides: 2x = 4\n"
            "Then divide by 2: x = 2"
        ),
    },
    "science": {
        "title": "The Water Cycle",
        "content": (
            "The water cycle describes how water moves through the environment.\n\n"
            "1. Evaporation: Water turns into vapor.\n"
            "2. Condensation: Vapor forms clouds.\n"
            "3. Precipitation: Rain or snow falls.\n"
            "4. Collection: Water gathers in rivers and oceans."
        ),
    },
    "history": {
        "title": "Ancient Civilizations",
        "content": (
            "Ancient Egypt developed along the Nile around 3100 BCE.\n"
            "They built pyramids, developed hieroglyphics, and created a calendar.\n"
            "The civilization lasted for over 3,000 years."
        ),
    },
}

QUIZ_QUESTIONS = [
    {
        "question": "What is 2 + 2?",
        "options": ["3", "4", "5"],
        "answer": "4",
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Venus", "Mars", "Jupiter"],
        "answer": "Mars",
    },
    {
        "question": "Who wrote 'Romeo and Juliet'?",
        "options": ["Charles Dickens", "William Shakespeare", "Jane Austen"],
        "answer": "William Shakespeare",
    },
]

# ---------- Helpers ----------
def get_lesson_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for choosing a lesson."""
    keyboard = [
        [InlineKeyboardButton("Math", callback_data="lesson_math")],
        [InlineKeyboardButton("Science", callback_data="lesson_science")],
        [InlineKeyboardButton("History", callback_data="lesson_history")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_quiz_keyboard(question_index: int) -> InlineKeyboardMarkup:
    """Keyboard for answering a quiz question."""
    q = QUIZ_QUESTIONS[question_index]
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"quiz_{question_index}_{opt}")]
        for opt in q["options"]
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------- Command Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with educational options."""
    text = (
        "👋 Welcome to the Educational Bot!\n\n"
        "I can help you learn new things.\n"
        "Use the buttons below or the commands:\n"
        "/lesson – Browse lessons\n"
        "/quiz – Take a short quiz\n"
        "/help – Show this message again"
    )
    keyboard = [
        [InlineKeyboardButton("📚 Browse Lessons", callback_data="browse_lessons")],
        [InlineKeyboardButton("❓ Take a Quiz", callback_data="start_quiz")],
    ]
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the lesson selection keyboard."""
    await update.message.reply_text(
        "Choose a subject:", reply_markup=get_lesson_keyboard()
    )


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the quiz with a random question."""
    idx = random.randint(0, len(QUIZ_QUESTIONS) - 1)
    context.user_data["quiz_index"] = idx
    q = QUIZ_QUESTIONS[idx]
    await update.message.reply_text(
        f"❓ {q['question']}",
        reply_markup=get_quiz_keyboard(idx),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Repeat the welcome message."""
    await start(update, context)


# ---------- Callback Query Handlers ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # ----- Lesson browsing -----
    if data == "browse_lessons":
        await query.edit_message_text(
            "Choose a subject:", reply_markup=get_lesson_keyboard()
        )
        return

    if data.startswith("lesson_"):
        key = data.split("_", 1)[1]
        lesson = LESSONS.get(key)
        if lesson:
            await query.edit_message_text(
                f"📖 *{lesson['title']}*\n\n{lesson['content']}",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text("Lesson not found.")
        return

    # ----- Quiz -----
    if data == "start_quiz":
        idx = random.randint(0, len(QUIZ_QUESTIONS) - 1)
        context.user_data["quiz_index"] = idx
        q = QUIZ_QUESTIONS[idx]
        await query.edit_message_text(
            f"❓ {q['question']}",
            reply_markup=get_quiz_keyboard(idx),
        )
        return

    if data.startswith("quiz_"):
        _, idx_str, selected = data.split("_", 2)
        idx = int(idx_str)
        correct = QUIZ_QUESTIONS[idx]["answer"]
        if selected == correct:
            feedback = "✅ Correct!"
        else:
            feedback = f"❌ Sorry, the correct answer is: {correct}"
        # After feedback, offer to take another quiz or go back.
        keyboard = [
            [InlineKeyboardButton("🔄 Another Question", callback_data="start_quiz")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
        await query.edit_message_text(
            f"{feedback}\n\nWould you like to try another question?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # ----- Main menu shortcut -----
    if data == "main_menu":
        text = (
            "👋 Main Menu\n\n"
            "Use the buttons below:\n"
            "/lesson – Browse lessons\n"
            "/quiz – Take a quiz\n"
            "/help – Show this message"
        )
        keyboard = [
            [InlineKeyboardButton("📚 Browse Lessons", callback_data="browse_lessons")],
            [InlineKeyboardButton("❓ Take a Quiz", callback_data="start_quiz")],
        ]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return


# ---------- Main ----------
def main() -> None:
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lesson", lesson_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("help", help_command))

    # Callback query handler for all inline buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Educational bot is starting (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
