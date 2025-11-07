with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем конкретный паттерн с проблемным if
# Паттерн: if условие: затем сразу response без отступа
content = re.sub(
    r'(if [^:]+:\s*)\n(response \+=)',
    r'\1\n    \2',
    content
)

# Еще один паттерн для if с пустым телом
content = re.sub(
    r'(if [^:]+:\s*)\n(\s*[^#\s])',
    r'\1\n    \2',
    content
)

with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Конкретные блоки if исправлены!")
