# Создаем исправленную версию без дат
with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем функцию format_date полностью
import re
content = re.sub(r'def format_date\(date_str\):.*?return ""\n', '', content, flags=re.DOTALL)

# Удаляем все блоки с датами из вывода
content = re.sub(
    r"if article\.get\('date'\):\s*formatted_date = format_date\(article\['date'\]\)\s*if formatted_date:\s*response \+= f\"   📅 {formatted_date}\"\\n",
    "",
    content
)

# Упрощаем вывод - убираем все упоминания дат
content = re.sub(
    r'if article\.get\(\'date\'\):\s*\n\s*formatted_date = format_date\(article\[\'date\'\]\)\s*\n\s*if formatted_date:\s*\n\s*response \+= f"   📅 {formatted_date}"\s*\n',
    '',
    content
)

with open('universal_search_bot_no_dates.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Даты убраны из вывода!")
