import logging
import sqlite3
import asyncio
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
from telegram.error import BadRequest

# Попытка импорта из config.py, если не найден - используем захардкоженный токен
try:
    from config import TELEGRAM_BOT_TOKEN
    TOKEN = TELEGRAM_BOT_TOKEN
except ImportError:
    TOKEN = "7555815142:AAHy-gudCxhKIs07RyEc8esG9qHOcLm8EbA"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
DEAL_TYPE, LOCATION, BUDGET, ROOMS, SEARCH_RESULTS = range(5)

# User data keys
DEAL = 'deal_type'
LOC = 'location'
BUD = 'budget'
RMS = 'rooms'
RESULTS = 'search_results'
PAGE = 'current_page'

# Configuration
ITEMS_PER_PAGE = 10
BIG_CITIES = ['лимассол', 'пафос', 'ларнака', 'limassol', 'paphos', 'larnaca']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about the deal type."""
    context.user_data.clear()  # Clear any previous data
    
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда", callback_data='rent')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Привет! Я помогу найти недвижимость на Кипре.\n'
        'Выберите тип сделки:',
        reply_markup=reply_markup
    )
    return DEAL_TYPE

async def deal_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected deal type and asks for location."""
    query = update.callback_query
    await query.answer()
    
    context.user_data[DEAL] = query.data
    
    await query.edit_message_text(
        text="Выбрана аренда ✅\n\n"
             "Введите город поиска (например: Лимассол, Пафос, Ларнака, Айя-Напа):"
    )
    return LOCATION

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for budget."""
    context.user_data[LOC] = update.message.text.strip()
    
    await update.message.reply_text(
        f"Город: {update.message.text} ✅\n\n"
        "Введите максимальный бюджет в EUR (например: 1500):"
    )
    return BUDGET

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the budget and asks for number of rooms."""
    try:
        budget_value = int(update.message.text.strip())
        context.user_data[BUD] = budget_value
        
        await update.message.reply_text(
            f"Бюджет: до {budget_value} EUR ✅\n\n"
            "Введите количество комнат (например: 2) или 0 для любого количества:"
        )
        return ROOMS
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректное число для бюджета:"
        )
        return BUDGET

async def rooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the number of rooms and performs the search."""
    try:
        rooms_value = int(update.message.text.strip())
        context.user_data[RMS] = rooms_value
        
        await update.message.reply_text(
            f"Комнат: {rooms_value if rooms_value > 0 else 'любое количество'} ✅\n\n"
            "🔍 Ищу подходящие варианты..."
        )
        
        return await process_search(update, context)
        
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректное число для количества комнат:"
        )
        return ROOMS

async def process_search(update, context):
    """Выполняет поиск в базе данных и отправляет результаты."""
    try:
        # Проверяем наличие файла базы данных
        import os
        if not os.path.exists('ads.db'):
            await update.message.reply_text("Ошибка: база данных не найдена.")
            return ConversationHandler.END
            
        conn = sqlite3.connect('ads.db')
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        # Проверяем существование таблицы ads
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ads'")
        if not cursor.fetchone():
            conn.close()
            await update.message.reply_text("Ошибка: таблица ads не найдена в базе данных.")
            return ConversationHandler.END
        
        # Получаем параметры поиска
        location_input = context.user_data.get(LOC, '').lower()
        budget = context.user_data.get(BUD, 0)
        rooms = context.user_data.get(RMS, 0)
        
        # Расширенное сопоставление городов
        city_mapping = {
            'лимассол': ['лимассол', 'limassol', 'лимасол', 'limmasol'],
            'пафос': ['пафос', 'paphos', 'пафоc', 'pafos'],
            'ларнака': ['ларнака', 'larnaca', 'ларнaка', 'larnaka'],
            'айя-напа': ['айя-напа', 'ayia napa', 'айя напа', 'agia napa', 'айянапа'],
            'никосия': ['никосия', 'nicosia', 'никoсия', 'lefkosia'],
            'протарас': ['протарас', 'protaras', 'прoтарас'],
            'фамагуста': ['фамагуста', 'famagusta', 'фамагустa']
        }
        
        # Находим подходящие варианты названия города
        location_variants = []
        for city, variants in city_mapping.items():
            if any(variant in location_input for variant in variants):
                location_variants.extend(variants)
                break
        
        if not location_variants:
            location_variants = [location_input]
        
        # Формируем SQL запрос
        location_conditions = []
        params = []
        
        for variant in location_variants:
            location_conditions.append("LOWER(location) LIKE ?")
            params.append(f"%{variant}%")
        
        location_clause = " OR ".join(location_conditions)
        
        # Основной запрос
        query = f"""
        SELECT * FROM ads 
        WHERE ({location_clause})
        AND price > 0 AND price <= ?
        """
        params.append(budget)
        
        if rooms > 0:
            query += " AND rooms = ?"
            params.append(rooms)
        
        query += " ORDER BY price ASC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            await update.message.reply_text(
                f"😔 К сожалению, не найдено объявлений по вашим критериям:\n"
                f"📍 Локация: {location_input}\n"
                f"💰 Бюджет: до {budget} EUR\n"
                f"🛏 Комнат: {rooms if rooms > 0 else 'любое количество'}\n\n"
                f"Попробуйте изменить параметры поиска."
            )
            return ConversationHandler.END
        
        # Сохраняем результаты
        context.user_data[RESULTS] = results
        context.user_data[PAGE] = 0
        
        # Определяем стратегию показа результатов
        location_lower = location_input.lower()
        is_big_city = any(city in location_lower for city in BIG_CITIES)
        
        if is_big_city and len(results) > ITEMS_PER_PAGE:
            # Для больших городов используем пагинацию
            await send_paginated_results(update, context, 0)
            return SEARCH_RESULTS
        else:
            # Для маленьких городов показываем все сразу
            await send_all_results(update, context, results)
            # КРИТИЧНО: Остаёмся в состоянии SEARCH_RESULTS для работы кнопок
            return SEARCH_RESULTS
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        await update.message.reply_text("Ошибка при обращении к базе данных.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"An error occurred during DB search: {e}")
        await update.message.reply_text("Произошла ошибка при поиске. Попробуйте еще раз.")
        return ConversationHandler.END

async def send_paginated_results(update, context, page_num):
    """Отправляет результаты постранично с кнопками навигации."""
    try:
        all_results = context.user_data.get(RESULTS, [])
        if not all_results:
            await update.message.reply_text("Ошибка: результаты поиска не найдены.")
            return

        total_results = len(all_results)
        
        start_idx = page_num * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_results)
        page_results = all_results[start_idx:end_idx]
        
        # Отправляем информацию о количестве найденных результатов
        if page_num == 0:
            location = context.user_data.get(LOC, '')
            budget = context.user_data.get(BUD, 0)
            rooms = context.user_data.get(RMS, 0)
            
            await update.message.reply_text(
                f"🎉 Найдено {total_results} объявлений!\n"
                f"📍 {location}\n"
                f"💰 До {budget} EUR\n"
                f"🛏 {rooms if rooms > 0 else 'Любое количество'} комнат\n\n"
                f"Показываю {ITEMS_PER_PAGE} объявлений на странице:"
            )
        
        # Отправляем объявления группами по 3-5 в одном сообщении
        group_size = 5
        for i in range(0, len(page_results), group_size):
            group = page_results[i:i + group_size]
            msg_parts = []
            
            for idx, row in enumerate(group, start_idx + i + 1):
                link = f"https://t.me/kipr_arenda/{row['message_id']}"
                # Сокращаем локацию для компактности
                location_short = str(row['location'])[:30] + ('...' if len(str(row['location'])) > 30 else '')
                msg_parts.append(f"{idx}. {location_short}\n💰 {row['price']} EUR | 🛏 {row['rooms']} комн.\n{link}")
            
            msg = "\n\n".join(msg_parts)
            
            try:
                await update.message.reply_text(msg, disable_web_page_preview=True)
                await asyncio.sleep(0.3)  # Пауза между сообщениями
            except BadRequest as e:
                if "Text is too long" in str(e):
                    # Если сообщение все еще слишком длинное, отправляем по одному
                    for idx, row in enumerate(group, start_idx + i + 1):
                        link = f"https://t.me/kipr_arenda/{row['message_id']}"
                        location_short = str(row['location'])[:30] + ('...' if len(str(row['location'])) > 30 else '')
                        short_msg = f"{idx}. {location_short}\n💰 {row['price']} EUR | 🛏 {row['rooms']} комн.\n{link}"
                        await update.message.reply_text(short_msg, disable_web_page_preview=True)
                        await asyncio.sleep(0.2)
                else:
                    raise e
        
        # Показываем кнопки навигации
        keyboard = []
        
        if end_idx < total_results:
            # Есть еще результаты
            keyboard.append([InlineKeyboardButton("📄 Показать еще", callback_data=f"next_{page_num + 1}")])
        else:
            # Это последняя страница
            await update.message.reply_text(
                f"✨ Это все найденные объявления!\n\n"
                f"🎯 Показано {total_results} из {total_results} результатов\n"
                f"📊 Критерии поиска:\n"
                f"• Локация: {context.user_data.get(LOC, 'Не указана')}\n"
                f"• Бюджет: до {context.user_data.get(BUD, 0)} EUR\n"
                f"• Комнат: {context.user_data.get(RMS, 0) if context.user_data.get(RMS, 0) > 0 else 'любое количество'}\n\n"
                f"Что дальше?"
            )
        
        keyboard.extend([
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")],
            [InlineKeyboardButton("❌ Завершить", callback_data="end")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        page_info = f"Страница {page_num + 1}, показано {start_idx + 1}-{end_idx} из {total_results}"
        await update.message.reply_text(page_info, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in send_paginated_results: {e}")
        await update.message.reply_text("Ошибка при отправке результатов.")

async def send_all_results(update, context, results):
    """Отправляет все результаты для маленьких городов."""
    count = len(results)
    location = context.user_data.get(LOC, '')
    budget = context.user_data.get(BUD, 0)
    rooms = context.user_data.get(RMS, 0)
    
    await update.message.reply_text(
        f"🎉 Найдено {count} объявлений в {location}!\n"
        f"💰 До {budget} EUR | 🛏 {rooms if rooms > 0 else 'Любое количество'} комнат"
    )
    
    # Отправляем объявления группами
    group_size = 3
    for i in range(0, len(results), group_size):
        group = results[i:i + group_size]
        msg_parts = []
        
        for idx, row in enumerate(group, i + 1):
            link = f"https://t.me/kipr_arenda/{row['message_id']}"
            location_short = str(row['location'])[:35] + ('...' if len(str(row['location'])) > 35 else '')
            msg_parts.append(f"{idx}. {location_short}\n💰 {row['price']} EUR | 🛏 {row['rooms']} комн.\n{link}")
        
        msg = "\n\n".join(msg_parts)
        
        try:
            await update.message.reply_text(msg, disable_web_page_preview=True)
            await asyncio.sleep(0.3)
        except BadRequest as e:
            if "Text is too long" in str(e):
                # Отправляем по одному
                for idx, row in enumerate(group, i + 1):
                    link = f"https://t.me/kipr_arenda/{row['message_id']}"
                    location_short = str(row['location'])[:35] + ('...' if len(str(row['location'])) > 35 else '')
                    short_msg = f"{idx}. {location_short}\n💰 {row['price']} EUR | 🛏 {row['rooms']} комн.\n{link}"
                    await update.message.reply_text(short_msg, disable_web_page_preview=True)
                    await asyncio.sleep(0.2)
            else:
                raise e
    
    # Финальное сообщение с кнопками
    keyboard = [
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")],
        [InlineKeyboardButton("❌ Завершить", callback_data="end")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✨ Показаны все найденные объявления!\n"
        f"Всего: {count} результатов",
        reply_markup=reply_markup
    )

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles pagination button clicks."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("next_"):
        page_num = int(query.data.split("_")[1])
        context.user_data[PAGE] = page_num
        # Создаем объект update с message вместо callback_query для send_paginated_results
        class MockUpdate:
            def __init__(self, message):
                self.message = message
        
        mock_update = MockUpdate(query.message)
        await send_paginated_results(mock_update, context, page_num)
        return SEARCH_RESULTS
    elif query.data == "new_search":
        # Clear user data and start new search
        context.user_data.clear()
        
        # Обновляем исходное сообщение
        try:
            await query.edit_message_text("🔍 Начинаем новый поиск!")
        except:
            pass
        
        # Отправляем новое сообщение с кнопками выбора типа сделки
        keyboard = [
            [InlineKeyboardButton("🏠 Аренда", callback_data='rent')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text='Выберите тип сделки:',
            reply_markup=reply_markup
        )
        return DEAL_TYPE
    elif query.data == "end":
        # End conversation
        context.user_data.clear()
        
        try:
            await query.edit_message_text("👋 До свидания! Для нового поиска используйте команду /start")
        except:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👋 До свидания! Для нового поиска используйте команду /start"
            )
        return ConversationHandler.END
    
    return SEARCH_RESULTS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        '👋 Поиск отменен. Напишите /start чтобы начать заново.'
    )
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DEAL_TYPE: [CallbackQueryHandler(deal_type)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
            ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, rooms)],
            SEARCH_RESULTS: [CallbackQueryHandler(handle_pagination)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()