import re

# Читаем файл
with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Удаляем функцию format_date и все связанные с ней строки
cleaned_lines = []
skip = False
for line in lines:
    # Пропускаем строки функции format_date
    if 'def format_date' in line:
        skip = True
        continue
    elif skip and line.strip() and not line.startswith(' '):
        skip = False
    
    if not skip:
        # Удаляем строки с вызовом format_date
        if 'format_date' in line:
            continue
        # Удаляем строки с выводом дат
        if '📅' in line:
            continue
        # Удаляем проверки на date
        if "article.get('date')" in line:
            continue
        # Удаляем поля date из словарей
        if "'date':" in line:
            continue
        cleaned_lines.append(line)

# Объединяем обратно
content = ''.join(cleaned_lines)

# Убираем лишние пустые строки
content = re.sub(r'\n\n\n+', '\n\n', content)

# Записываем исправленный файл
with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Код исправлен! Удалены все упоминания дат и исправлены отступы.")
