import sqlite3
from config import DB_FILE
import json
from config import PARSED_MESSAGES_FILE, RAW_MESSAGES_FILE

def show_stats():
    # Статистика из базы данных
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM ads")
    total_in_db = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM ads WHERE location IS NOT NULL")
    with_location = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM ads WHERE price IS NOT NULL")
    with_price = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM ads WHERE deal_type IS NOT NULL")
    with_deal_type = c.fetchone()[0]
    
    conn.close()
    
    # Статистика из файлов
    try:
        with open(RAW_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            raw_messages = json.load(f)
            current_batch_size = len(raw_messages)
    except:
        current_batch_size = 0
        
    try:
        with open(PARSED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            parsed_messages = json.load(f)
            total_parsed = len(parsed_messages)
    except:
        total_parsed = 0
    
    print("\n=== Статистика обработки ===")
    print(f"Записей в базе данных: {total_in_db}")
    print(f"Записей с локацией: {with_location}")
    print(f"Записей с ценой: {with_price}")
    print(f"Записей с типом сделки: {with_deal_type}")
    print(f"\nВсего обработано сообщений: {total_parsed}")
    print(f"Текущий размер пакета: {current_batch_size}")
    
if __name__ == '__main__':
    show_stats() 