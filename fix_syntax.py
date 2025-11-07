import re

with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем проблемный блок с articles.append
# Исправляем неправильную структуру словаря
content = re.sub(
    r"articles\.append\(\{.*?'':.*?if time_elem else '',.*?\}\)",
    lambda match: re.sub(r"'' if time_elem else '',", "'',", match.group()),
    content,
    flags=re.DOTALL
)

# Ищем другой возможный паттерн с неправильными скобками
content = re.sub(
    r"articles\.append\(\{[^}]*(?:'[^']*'[^}]*)*?\)",
    lambda match: match.group().replace(')', '})') if match.group().count('{') > match.group().count('}') else match.group(),
    content
)

# Записываем исправленный файл
with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Синтаксические ошибки исправлены!")
