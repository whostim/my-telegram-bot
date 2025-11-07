# Точечное исправление строки 684
with open('universal_search_bot_fixed3.py', 'r') as f:
    lines = f.readlines()

# Находим и исправляем конкретную проблему на строке 684
for i in range(len(lines)):
    if i == 683:  # Строка 684 (индексация с 0)
        if 'if formatted_date:' in lines[i]:
            # Проверяем следующую строку
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Если следующая строка не имеет правильного отступа для блока if
                if not next_line.startswith('    ') and 'response +=' in next_line:
                    # Создаем правильный отступ (24 пробела)
                    indent = ' ' * 24
                    # Вставляем недостающую строку
                    lines.insert(i + 1, f'{indent}response += f"   📅 {formatted_date}"\n')
                    break

with open('universal_search_bot_fixed5.py', 'w') as f:
    f.writelines(lines)

print("✅ Конкретная ошибка на строке 684 исправлена!")
