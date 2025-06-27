# main.py
import time
import json
import sys
import traceback
from telegram_fetcher import fetch_messages
from llm_extractor import process_messages
from db_writer import save_to_db, get_existing_message_ids
from config import RAW_MESSAGES_FILE, PARSED_MESSAGES_FILE
import os
import shutil

BATCH_SIZE = 50  # Размер порции для обработки LLM

def load_existing_results():
    """Загружает существующие результаты из файла"""
    try:
        with open(PARSED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data:
                last_id = data[-1]['message_id']
                print(f"📊 Последний обработанный message_id: {last_id}")
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def filter_new_messages(all_messages, existing_ids):
    """Фильтрует сообщения, оставляя только те, что идут после последнего обработанного"""
    if not existing_ids:
        return all_messages
        
    # Находим максимальный ID из существующих
    max_existing_id = max(existing_ids)
    return [msg for msg in all_messages if msg['message_id'] > max_existing_id]

def save_results_safely(results, filename):
    """Безопасное сохранение результатов с созданием бэкапа"""
    # Создаем бэкап если файл существует
    if os.path.exists(filename):
        backup_name = filename + '.backup'
        shutil.copy2(filename, backup_name)
    
    # Сохраняем новые данные во временный файл
    temp_file = filename + '.temp'
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Если сохранение прошло успешно, заменяем оригинальный файл
    os.replace(temp_file, filename)

def process_messages_in_batches(messages):
    """Обрабатывает сообщения порциями"""
    # Загружаем существующие результаты
    all_results = load_existing_results()
    
    # Получаем существующие ID
    processed_ids = {msg['message_id'] for msg in all_results}
    
    # Фильтруем сообщения, оставляя только новые
    messages = filter_new_messages(messages, processed_ids)
    
    total_messages = len(messages)
    if total_messages == 0:
        print("✅ Все сообщения уже обработаны!")
        return all_results
        
    print(f"📝 Осталось обработать: {total_messages} сообщений")
    
    for i in range(0, total_messages, BATCH_SIZE):
        batch = messages[i:i + BATCH_SIZE]
        current_batch = i//BATCH_SIZE + 1
        total_batches = (total_messages + BATCH_SIZE - 1)//BATCH_SIZE
        print(f"\nОбработка порции {current_batch} из {total_batches}")
        
        # Сохраняем текущую порцию во временный файл
        with open(RAW_MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        
        # Обрабатываем порцию
        try:
            results = process_messages()
            all_results.extend(results)
            
            # Сохраняем результаты после каждой успешной порции
            with open(PARSED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
                
            print(f"✅ Порция {current_batch}/{total_batches} обработана успешно")
            print(f"📊 Прогресс: {min(i + BATCH_SIZE, total_messages)}/{total_messages} сообщений")
            
        except Exception as e:
            print(f"❌ Ошибка при обработке порции {current_batch}/{total_batches}: {str(e)}")
            traceback.print_exc()
            continue
        
        time.sleep(2)  # Пауза между порциями
    
    return all_results

def main():
    try:
        print("🚀 Запуск обработки сообщений...")
        
        try:
            print("📥 Получение сообщений из Telegram...")
            all_messages = fetch_messages(limit=5000)
            print(f"✅ Получено {len(all_messages)} сообщений")
        except Exception as e:
            print(f"❌ Ошибка при получении сообщений из Telegram: {str(e)}")
            traceback.print_exc()
            return

        try:
            existing_ids = get_existing_message_ids()
            print(f"📊 Загружено {len(existing_ids)} ID из базы данных")
        except Exception as e:
            print(f"❌ Ошибка при получении существующих ID: {str(e)}")
            traceback.print_exc()
            return

        new_messages = filter_new_messages(all_messages, existing_ids)

        if new_messages:
            print(f"📨 Найдено {len(new_messages)} новых сообщений")
            
            print("🤖 Начинаем обработку...")
            results = process_messages_in_batches(new_messages)
            
            print("\n💾 Сохранение в базу данных...")
            try:
                save_to_db()
                print("✅ Данные успешно сохранены в базу")
            except Exception as e:
                print(f"❌ Ошибка при сохранении в базу данных: {str(e)}")
                traceback.print_exc()
                return

            print("\n✨ Обработка завершена успешно!")
        else:
            print("📭 Новых сообщений нет.")

    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        traceback.print_exc()
        return

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Завершение работы...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        traceback.print_exc() 