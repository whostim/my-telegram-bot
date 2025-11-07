# Простой скрипт для исправления ошибок отступов
with open('universal_search_bot.py', 'r') as f:
    content = f.read()

# Исправляем конкретные проблемные места
content = content.replace(
    '''if formatted_date:
                response += f"   🔗 {article['url']}''',
    '''if formatted_date:
                        response += f"   📅 {formatted_date}"
                response += f"   🔗 {article['url']}'''
)

# Сохраняем исправленный файл
with open('universal_search_bot_fixed.py', 'w') as f:
    f.write(content)

print("✅ Файл исправлен! Создан universal_search_bot_fixed.py")
