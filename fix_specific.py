with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Ищем строку 419 и исправляем ее
for i in range(len(lines)):
    if i == 418:  # строка 419 (индекс 418)
        line = lines[i]
        # Исправляем проблему с кавычками и скобками
        if "'' if time_elem else ''," in line:
            lines[i] = line.replace("'' if time_elem else '',", "'',")
        # Ищем незакрытые скобки
        if line.count('(') > line.count(')'):
            lines[i] = line.rstrip() + ')' * (line.count('(') - line.count(')')) + '\n'

with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Конкретная строка исправлена!")
