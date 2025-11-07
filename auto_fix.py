# Автоматическое исправление ошибок отступов
with open('universal_search_bot.py', 'r') as f:
    lines = f.readlines()

# Исправляем ошибки отступов после условий if formatted_date
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Ищем проблемные участки
    if 'if formatted_date:' in line and i + 1 < len(lines):
        next_line = lines[i + 1]
        # Проверяем, есть ли неправильный отступ на следующей строке
        if 'response += f"   🔗 {article[\'url\']}' in next_line and not next_line.startswith(' ' * 24):
            # Добавляем недостающую строку с правильным отступом
            fixed_lines.append(line)
            indent = ' ' * 24  # Правильный отступ
            fixed_lines.append(f'{indent}response += f"   📅 {formatted_date}"\n')
            i += 1  # Пропускаем следующую строку, так как мы её заменили
            continue
    
    fixed_lines.append(line)
    i += 1

# Записываем исправленный файл
with open('universal_search_bot_fixed.py', 'w') as f:
    f.writelines(fixed_lines)

print("✅ Файл исправлен! Создан universal_search_bot_fixed.py")
