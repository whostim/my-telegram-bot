import re

with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем только строки с выводом дат, не трогая структуру словарей
content = re.sub(r'.*📅.*\n', '', content)
content = re.sub(r"if article\.get\('date'\):.*?response \\+= f\"   📅 \\{formatted_date\}\\\\n\"", '', content, flags=re.DOTALL)

with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Безопасно удалены строки вывода дат")
