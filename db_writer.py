# db_writer.py
import sqlite3
import json
import re
from config import DB_FILE, PARSED_MESSAGES_FILE
from typing import Union, List

def get_existing_message_ids():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Создаем таблицу, если она не существует
    c.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            message_id INTEGER PRIMARY KEY,
            location TEXT,
            price TEXT,
            deal_type TEXT,
            rooms TEXT
        )
    ''')
    
    c.execute("SELECT message_id FROM ads")
    rows = c.fetchall()
    conn.close()
    return set(row[0] for row in rows)

def normalize_price(price_str: Union[str, int, float, List]) -> str:
    """Нормализует цену для записи в базу данных"""
    if not price_str:
        return ""
        
    # Преобразуем в строку
    if isinstance(price_str, (int, float)):
        return str(price_str)
    elif isinstance(price_str, list):
        price_str = str(price_str[0]) if price_str else ""
        
    price_str = str(price_str).lower()
    # Удаляем все символы валют и текст
    price_str = price_str.replace('€', '').replace('eur', '').replace('euro', '')
    # Находим все числа в строке
    numbers = re.findall(r'\d+(?:[\s,.]?\d+)*', price_str)
    if not numbers:
        return ""
        
    # Берем первое число и очищаем его
    price_clean = numbers[0].replace(' ', '').replace(',', '.')
    # Если после точки больше 2 цифр, это скорее всего разделитель тысяч
    if '.' in price_clean and len(price_clean.split('.')[1]) > 2:
        price_clean = price_clean.replace('.', '')
    return price_clean

def normalize_rooms(rooms_str: Union[str, int, float, List]) -> str:
    """Нормализует количество комнат для записи в базу данных"""
    if not rooms_str:
        return ""
        
    # Преобразуем в строку
    if isinstance(rooms_str, (int, float)):
        return str(int(rooms_str))
    elif isinstance(rooms_str, list):
        rooms_str = str(rooms_str[0]) if rooms_str else ""
        
    rooms_str = str(rooms_str).lower()
    # Ищем первое число в строке
    numbers = re.findall(r'\d+', rooms_str)
    if not numbers:
        return ""
    return numbers[0]

def normalize_deal_type(deal_type: Union[str, List]) -> str:
    """Нормализует тип сделки для записи в базу данных"""
    if not deal_type:
        return ""
        
    # Преобразуем в строку
    if isinstance(deal_type, list):
        deal_type = deal_type[0] if deal_type else ""
        
    deal_type = str(deal_type).lower().strip()
    if any(word in deal_type for word in ['аренда', 'rent', 'рент']):
        return 'аренда'
    elif any(word in deal_type for word in ['продажа', 'sale', 'buy', 'купить']):
        return 'продажа'
    return deal_type

def save_to_db():
    print("Читаем данные из JSON файла...")
    with open(PARSED_MESSAGES_FILE, encoding='utf-8') as f:
        data = json.load(f)
    print(f"Прочитано {len(data)} объектов из JSON")

    print("Подключаемся к базе данных...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    print("Создаем таблицу...")
    c.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            message_id INTEGER PRIMARY KEY,
            location TEXT,
            price TEXT,
            deal_type TEXT,
            rooms TEXT
        )
    ''')

    print("Записываем данные...")
    inserted = 0
    for item in data:
        try:
            # Нормализуем данные перед записью
            price = normalize_price(item.get('price', ''))
            rooms = normalize_rooms(item.get('rooms', ''))
            deal_type = normalize_deal_type(item.get('deal_type', ''))
            
            c.execute('''
                INSERT OR REPLACE INTO ads (message_id, location, price, deal_type, rooms)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                item.get('message_id', ''),
                item.get('location', ''),
                price,
                deal_type,
                rooms
            ))
            inserted += 1
            
        except Exception as e:
            print(f"Ошибка при записи объекта {item.get('message_id', 'unknown')}: {str(e)}")
            continue

    conn.commit()
    print(f"Записано {inserted} объектов в базу данных")
    conn.close()

if __name__ == "__main__":
    save_to_db() 