# llm_extractor.py
import requests
import json
import re
import time
import sys
from config import API_KEY, LLM_URL, LLM_MODEL, RAW_MESSAGES_FILE, PARSED_MESSAGES_FILE

def print_flush(*args, **kwargs):
    """Печать с принудительной очисткой буфера"""
    print(*args, **kwargs)
    sys.stdout.flush()

def extract_json_from_text(text):
    """Извлекает JSON из текста, даже если есть лишний текст до или после"""
    json_pattern = r'\{[^{}]*\}'
    match = re.search(json_pattern, text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None

def call_llm(message_text, max_retries=3, delay=2):
    """Вызов LLM с повторными попытками при ошибках"""
    prompt = (
        "Извлеки из этого объявления ключевые данные в формате JSON. "
        "Верни ТОЛЬКО JSON без дополнительного текста: "
        '{"location": "город/район", "price": "цена", "deal_type": "аренда/продажа", "rooms": "количество комнат"}. '
        f"Текст объявления: {message_text}"
    )
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(LLM_URL, headers=headers, json=data)
            response.raise_for_status()

            content = response.json()['choices'][0]['message']['content']
            
            # Пытаемся извлечь JSON из ответа
            result = extract_json_from_text(content)
            if not result:
                raise ValueError("Не удалось извлечь JSON из ответа LLM")
                
            return result
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:  # Последняя попытка
                raise
            print_flush(f"Попытка {attempt + 1} не удалась: {str(e)}. Повторная попытка через {delay} секунд...")
            time.sleep(delay)
            delay *= 2  # Увеличиваем задержку с каждой попыткой

def process_messages(start_from_message_id=None):
    """Обработка сообщений с возможностью продолжить с определенного ID"""
    print_flush("\n🔄 Загружаем сообщения из файла...")
    with open(RAW_MESSAGES_FILE, encoding='utf-8') as f:
        messages = json.load(f)
    print_flush(f"📥 Загружено {len(messages)} сообщений для обработки")

    # Загружаем существующие результаты
    try:
        with open(PARSED_MESSAGES_FILE, encoding='utf-8') as f:
            results = json.load(f)
            print_flush(f"📋 Найдено {len(results)} уже обработанных сообщений")
    except (FileNotFoundError, json.JSONDecodeError):
        results = []
        print_flush("📋 Начинаем обработку с нуля")

    # Создаем множество уже обработанных message_id
    processed_ids = {msg['message_id'] for msg in results}
    total_to_process = len([msg for msg in messages if msg['message_id'] not in processed_ids])
    print_flush(f"\n📊 Всего предстоит обработать: {total_to_process} сообщений")

    processed_count = 0
    for msg in messages:
        if msg['message_id'] in processed_ids:
            continue

        try:
            print_flush(f"\n🔄 Обрабатываем сообщение {msg['message_id']} ({processed_count + 1}/{total_to_process})")
            time.sleep(1)  # Базовая задержка между запросами
            structured = call_llm(msg['text'])
            structured['message_id'] = msg['message_id']
            results.append(structured)
            
            # Дописываем результат в конец файла
            with open(PARSED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            processed_count += 1
            print_flush(f"✅ Сообщение {msg['message_id']} успешно обработано")
            print_flush(f"📊 Прогресс: {processed_count}/{total_to_process} ({(processed_count/total_to_process*100):.1f}%)")
            
        except Exception as e:
            print_flush(f"❌ Ошибка при обработке сообщения {msg['message_id']}: {str(e)}")
            continue

    print_flush(f"\n🎉 Обработка завершена! Всего обработано {processed_count} сообщений")
    return results 

if __name__ == '__main__':
    print_flush("🚀 Запускаем обработку сообщений...")
    process_messages() 