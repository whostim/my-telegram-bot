with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Исправляем проблему с отступами после if
for i in range(len(lines)):
    line = lines[i]
    
    # Ищем строки с if, после которых идет строка без правильного отступа
    if 'if ' in line and line.strip().startswith('if '):
        # Проверяем следующую строку
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            # Если следующая строка не имеет отступа, это ошибка
            if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                # Добавляем правильный отступ к следующей строке
                current_indent = len(line) - len(line.lstrip())
                lines[i + 1] = ' ' * (current_indent + 4) + next_line.lstrip()

# Записываем исправленный файл
with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Отступы после if исправлены!")
