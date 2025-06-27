import json

with open('parsed_messages.json', 'r', encoding='utf-8') as f:
    content = f.read()
    print(f"Количество строк в файле: {len(content.splitlines())}")
    
    data = json.loads(content)
    print(f"Количество сообщений в файле: {len(data)}")
    print(f"Первый message_id: {data[0].get('message_id')}")
    print(f"Последний message_id: {data[-1].get('message_id')}") 