with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Исправляем строку 75 (индекс 74)
if len(lines) > 74:
    # Убираем лишние пробелы в начале строки
    lines[74] = lines[74].lstrip()
    
    # Если это docstring, убедимся что у него правильный отступ
    if '"""' in lines[74]:
        # Проверяем предыдущую строку чтобы определить правильный отступ
        if len(lines) > 73:
            prev_indent = len(lines[73]) - len(lines[73].lstrip())
            lines[74] = ' ' * prev_indent + lines[74].lstrip()

with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Конкретная строка исправлена!")
