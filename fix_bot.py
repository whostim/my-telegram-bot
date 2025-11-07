import re

# Читаем исходный файл
with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем ошибки с отступами после условий if formatted_date
content = re.sub(
    r'if formatted_date:\nresponse \+= f"   🔗 {article\[\'url\'\]}',
    'if formatted_date:\n                        response += f"   📅 {formatted_date}"\n                    response += f"   🔗 {article[\'url\']}',
    content
)

# Исправляем первое место в функции fresh_news
content = re.sub(
    r'if article\.get\(\'date\'\):\n                    formatted_date = format_date\(article\[\'date\'\]\)\n                    if formatted_date:\n                response \+= f"   🔗 {article\[\'url\'\]}',
    'if article.get(\'date\'):\n                    formatted_date = format_date(article[\'date\'])\n                    if formatted_date:\n                        response += f"   📅 {formatted_date}"\n                response += f"   🔗 {article[\'url\']}',
    content
)

# Исправляем второе место в функции handle_text (российские источники)
content = re.sub(
    r'if article\.get\(\'date\'\):\n                        formatted_date = format_date\(article\[\'date\'\]\)\n                        if formatted_date:\n                    response \+= f"   🔗 {article\[\'url\'\]}',
    'if article.get(\'date\'):\n                        formatted_date = format_date(article[\'date\'])\n                        if formatted_date:\n                            response += f"   📅 {formatted_date}"\n                    response += f"   🔗 {article[\'url\']}',
    content
)

# Исправляем третье место в функции handle_text (международные источники)
content = re.sub(
    r'if article\.get\(\'date\'\):\n                        formatted_date = format_date\(article\[\'date\'\]\)\n                        if formatted_date:\n                    response \+= f"   🔗 {article\[\'url\'\]}',
    'if article.get(\'date\'):\n                        formatted_date = format_date(article[\'date\'])\n                        if formatted_date:\n                            response += f"   📅 {formatted_date}"\n                    response += f"   🔗 {article[\'url\']}',
    content
)

# Записываем исправленный файл
with open('universal_search_bot_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Файл успешно исправлен! Создан universal_search_bot_fixed.py")
