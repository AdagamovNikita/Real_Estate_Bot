import logging
import sqlite3
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from config import TELEGRAM_BOT_TOKEN

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
DEAL, LOC, BUD, RMS = range(4)

# User data keys
DEAL_TYPE, LOCATION, BUDGET, ROOMS = "deal_type", "location", "budget", "rooms"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the deal type."""
    if context.user_data:
        context.user_data.clear()

    if not update.message:
        logger.warning("start called without a message.")
        return ConversationHandler.END
    
    keyboard = [
        [
            InlineKeyboardButton("Аренда 🏠", callback_data="rent"),
            InlineKeyboardButton("Покупка 🏡", callback_data="buy"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Здравствуйте! Я помогу вам подобрать недвижимость на Кипре. Что вас интересует?",
        reply_markup=reply_markup,
    )
    return DEAL

async def ask_for_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores deal type and asks for location."""
    query = update.callback_query
    if not query or context.user_data is None:
        logger.error("State error in ask_for_location.")
        return ConversationHandler.END

    await query.answer()
    context.user_data[DEAL_TYPE] = query.data
    deal_text = "Аренда" if query.data == "rent" else "Покупка"
    await query.edit_message_text(text=f"Вы выбрали: {deal_text}.\n\nВ каком городе или районе вы ищете?")
    return LOC

async def ask_for_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores location and asks for budget."""
    if not (update.message and update.message.text) or context.user_data is None:
        logger.error("State error in ask_for_budget.")
        return ConversationHandler.END
        
    context.user_data[LOCATION] = update.message.text
    await update.message.reply_text("Какой у вас бюджет в евро?")
    return BUD

async def ask_for_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores budget and asks for rooms."""
    if not (update.message and update.message.text) or context.user_data is None:
        logger.error("State error in ask_for_rooms.")
        return ConversationHandler.END

    text = update.message.text
    price = re.sub(r'\D', '', text)
    if not price:
        await update.message.reply_text("Пожалуйста, введите бюджет числом, например: 1500")
        return BUD
    context.user_data[BUDGET] = int(price)
    await update.message.reply_text("Сколько комнат вам нужно?")
    return RMS

async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores rooms and performs the search."""
    if not (update.message and update.message.text) or context.user_data is None:
        logger.error("State error in process_search.")
        return ConversationHandler.END
        
    text = update.message.text
    rooms = re.sub(r'\D', '', text)
    if not rooms:
        await update.message.reply_text("Пожалуйста, введите количество комнат числом, например: 2")
        return RMS
    context.user_data[ROOMS] = int(rooms)

    await update.message.reply_text("Ищу подходящие варианты, это может занять минуту...")

    try:
        if context.user_data is None: # Redundant check, but satisfies linter
             return ConversationHandler.END
        conn = sqlite3.connect('ads.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        deal_type_user = context.user_data[DEAL_TYPE]
        # Map user-facing deal type to the value stored in the database
        deal_type_db = 'аренда' if deal_type_user == 'rent' else 'продажа'

        # Keep original case for location search
        loc_pattern = f"%{context.user_data[LOCATION]}%"
        bud = context.user_data[BUDGET]
        rms = context.user_data[ROOMS]
        
        min_p = bud * 0.8
        max_p = bud * 1.2

        cursor.execute(
            """
            SELECT message_id, location, price, rooms
            FROM ads 
            WHERE deal_type = ? 
              AND LOWER(location) LIKE LOWER(?) 
              AND CAST(price AS REAL) BETWEEN ? AND ? 
              AND CAST(rooms AS INTEGER) = ?
            ORDER BY RANDOM()
            LIMIT 5
            """,
            (deal_type_db, loc_pattern, min_p, max_p, rms),
        )
        
        results = cursor.fetchall()
        conn.close()

        if not results:
            if update.message:
                await update.message.reply_text("К сожалению, по вашему запросу ничего не найдено. Попробуйте изменить параметры, введя /start")
        elif update.message:
            msg = "Нашел несколько подходящих вариантов:\n\n"
            for row in results:
                link = f"https://t.me/kipr_arenda/{row['message_id']}"
                msg += (
                    f"📍 **Место:** {row['location']}\n"
                    f"💰 **Цена:** {row['price']} EUR\n"
                    f"🛏 **Комнаты:** {row['rooms']}\n"
                    f"➡️ [Посмотреть объявление]({link})\n\n"
                )
            await update.message.reply_text(msg, parse_mode='Markdown', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"An error occurred during DB search: {e}")
        if update.message:
            await update.message.reply_text("Произошла ошибка при поиске. Попробуйте позже. /start")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    if update.message:
        await update.message.reply_text("Диалог отменен.")
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DEAL: [CallbackQueryHandler(ask_for_location)],
            LOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_budget)],
            BUD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_rooms)],
            RMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main() 