# telegram_fetcher.py
from telethon import TelegramClient, events
from telethon.tl.types import Message
from config import API_ID, API_HASH, TELEGRAM_CHANNEL, RAW_MESSAGES_FILE
import json
import os
import time
import asyncio

# Создаем клиент с сохранением сессии
client = TelegramClient('telegram_session', API_ID, API_HASH)

async def get_messages(limit=5000):
    """Получает сообщения из Telegram канала с пагинацией"""
    messages = []
    try:
        # Подключаемся к каналу
        channel = await client.get_entity(TELEGRAM_CHANNEL)
        
        # Получаем сообщения порциями по 100
        offset_id = 0
        while len(messages) < limit:
            print(f"Получено {len(messages)} сообщений...")
            
            # Получаем порцию сообщений
            batch = await client.get_messages(channel, limit=100, offset_id=offset_id)
            if not batch:
                break
                
            # Обрабатываем порцию
            for message in batch:
                if isinstance(message, Message) and message.message:
                    messages.append({
                        'message_id': message.id,
                        'date': message.date.isoformat(),
                        'text': message.message
                    })
            
            # Обновляем offset для следующей порции
            offset_id = batch[-1].id
            
            # Небольшая пауза, чтобы не перегружать API
            await asyncio.sleep(1)
            
            if len(batch) < 100:  # Достигли конца истории
                break
        
        print(f"Всего получено {len(messages)} сообщений")
        return messages
    except Exception as e:
        print(f"Ошибка при получении сообщений: {str(e)}")
        raise

def fetch_messages(limit=5000):
    """Синхронная обертка для получения сообщений"""
    with client:
        messages = client.loop.run_until_complete(get_messages(limit))
        
        # Сохраняем сообщения в файл
        with open(RAW_MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"✅ Сообщения сохранены в файл {RAW_MESSAGES_FILE}")
        return messages

if __name__ == '__main__':
    print("🔄 Начинаем получение сообщений из Telegram...")
    fetch_messages() 