# Точечное исправление ошибки на строке 744
with open('universal_search_bot_fixed.py', 'r') as f:
    lines = f.readlines()

# Исправляем конкретную проблему
for i in range(len(lines)):
    if i >= 743 and i < 746:  # Около строки 744
        if 'if formatted_date:' in lines[i]:
            # Проверяем следующую строку
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Если следующая строка не имеет правильного отступа, исправляем
                if not next_line.strip().startswith('response +=') or '📅' not in next_line:
                    # Вставляем недостающую строку
                    indent = ' ' * 24
                    lines.insert(i + 1, f'{indent}response += f"   📅 {formatted_date}"\n')
                    break

# Записываем исправленный файл
with open('universal_search_bot_fixed2.py', 'w') as f:
    f.writelines(lines)

print("✅ Файл исправлен! Создан universal_search_bot_fixed2.py")
