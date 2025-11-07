# Полное исправление ВСЕХ проблем с отступами после if formatted_date
with open('universal_search_bot.py', 'r') as f:
    content = f.read()

# Находим ВСЕ места где есть проблема и исправляем их
import re

# Исправляем первый тип проблемы
content = re.sub(
    r'if formatted_date:\s*\n\s*response \+= f"   🔗 {article\[\'url\'\]}',
    'if formatted_date:\\n                        response += f"   📅 {formatted_date}"\\n                    response += f"   🔗 {article[\'url\']}',
    content
)

# Исправляем второй тип проблемы  
content = re.sub(
    r'if article\.get\(\'date\'\):\s*\n\s+formatted_date = format_date\(article\[\'date\'\]\)\s*\n\s+if formatted_date:\s*\n\s+response \+= f"   🔗 {article\[\'url\'\]}',
    'if article.get(\'date\'):\\n                    formatted_date = format_date(article[\'date\'])\\n                    if formatted_date:\\n                        response += f"   📅 {formatted_date}"\\n                    response += f"   🔗 {article[\'url\']}',
    content
)

with open('universal_search_bot_fixed6.py', 'w') as f:
    f.write(content)

print("✅ Все проблемные места исправлены ядерным методом!")
