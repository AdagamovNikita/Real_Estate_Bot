# Real Estate Bot для Кипра

Telegram бот для поиска недвижимости на Кипре из канала @kipr_arenda.

## Описание

Бот помогает пользователям найти подходящую недвижимость на Кипре на основе их критериев:
- Тип сделки (аренда/покупка)
- Местоположение
- Бюджет
- Количество комнат

Бот использует LLM (Mistral 7B) для обработки естественного языка и предоставляет прямые ссылки на объявления в Telegram канале.

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/AdagamovNikita/Real_Estate_Bot.git
cd Real_Estate_Bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `config.py` с вашими токенами:
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
MISTRAL_API_KEY = "your_mistral_api_key"
```

4. Запустите скрипты для сбора данных:
```bash
python telegram_fetcher.py
python llm_extractor.py
python db_writer.py
```

5. Запустите бота:
```bash
python bot.py
```

## Структура проекта

- `bot.py` - Основной файл Telegram бота
- `telegram_fetcher.py` - Скрипт для получения сообщений из канала
- `llm_extractor.py` - Обработка сообщений с помощью LLM
- `db_writer.py` - Запись данных в базу данных
- `config.py` - Конфигурационный файл (не включен в репозиторий)
- `requirements.txt` - Зависимости Python

## Возможности

- Интерактивный диалог с пользователем
- Поиск по критериям: тип сделки, местоположение, бюджет, количество комнат
- Интеграция с LLM для понимания естественного языка
- Прямые ссылки на объявления в Telegram канале
- База данных SQLite для хранения объявлений

## Технологии

- Python 3.8+
- python-telegram-bot
- SQLite
- Mistral 7B API
- Telegram API 