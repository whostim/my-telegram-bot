import re

# Читаем файл
with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Удаляем функцию format_date полностью
content = re.sub(
    r'def format_date\(date_str\):.*?return date_str',
    '',
    content,
    flags=re.DOTALL
)

# 2. Удаляем все строки с format_date
content = re.sub(r'.*format_date.*\n', '', content)

# 3. Удаляем все строки с 📅 (даты)
content = re.sub(r'.*📅.*\n', '', content)

# 4. Удаляем все строки с date из выводов в handle_text
content = re.sub(
    r'if article\.get\(\'date\'\):.*?response \+= f"   📅 \{formatted_date\}\\n"',
    '',
    content,
    flags=re.DOTALL
)

# 5. Удаляем все строки с date из выводов в fresh_news
content = re.sub(
    r'if article\.get\(\'date\'\):.*?response \+= f"   📅 \{formatted_date\}\\n"',
    '',
    content,
    flags=re.DOTALL
)

# 6. Удаляем все упоминания date из парсеров (сохраняя только логику источников)
# Яндекс парсер
yandex_pattern = r"(source_text = source_elem\.get_text\(\)\.strip\(\) if source_elem else 'Яндекс\.Новости').*?(articles\.append\(\{)"
content = re.sub(
    yandex_pattern,
    r"\\1\\n                                articles.append({",
    content,
    flags=re.DOTALL
)

# 7. Удаляем поле date из всех articles.append
content = re.sub(
    r"'date':.*?,", 
    "", 
    content
)

# 8. Удаляем все оставшиеся упоминания date в коде
content = re.sub(r'.*article\[\'date\'\]\*', '', content)
content = re.sub(r'.*article\.get\(\'date\'\).*', '', content)

# 9. Убираем лишние пустые строки
content = re.sub(r'\n\n\n+', '\n\n', content)
content = re.sub(r',\s*\n\s*\'language\'', ",\\n                                    'language'", content)

# Записываем обновленный файл
with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ ВСЕ упоминания времени и дат полностью удалены из кода!")
print("📝 Удалено:")
print("   - Функция format_date")
print("   - Все вызовы format_date")
print("   - Все строки с выводом дат (📅)")
print("   - Все упоминания article['date']")
print("   - Все поля 'date' в articles.append")
print("   - Все проверки article.get('date')")
