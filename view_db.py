import sqlite3
import json

def view_database():
    try:
        conn = sqlite3.connect('ads.db')
        c = conn.cursor()
        
        # Получаем список всех таблиц
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        print("\nТаблицы в базе данных:")
        for table in tables:
            print(f"- {table[0]}")
            
        # Получаем данные из таблицы ads
        print("\nСодержимое таблицы ads:")
        c.execute("SELECT * FROM ads LIMIT 5")
        rows = c.fetchall()
        if rows:
            # Получаем имена колонок
            column_names = [description[0] for description in c.description]
            print(f"\nКолонки: {', '.join(column_names)}")
            
            # Выводим первые 5 записей
            print("\nПервые 5 записей:")
            for row in rows:
                print(json.dumps(dict(zip(column_names, row)), ensure_ascii=False, indent=2))
        else:
            print("Таблица пуста")
            
        # Получаем общее количество записей
        c.execute("SELECT COUNT(*) FROM ads")
        count = c.fetchone()[0]
        print(f"\nВсего записей в таблице: {count}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {str(e)}")
    except Exception as e:
        print(f"Неожиданная ошибка: {str(e)}")

if __name__ == "__main__":
    view_database() 