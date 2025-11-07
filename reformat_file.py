import re

with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Временная замена для сохранения строк с комментариями
lines = content.split('\n')
formatted_lines = []

indent_level = 0
for line in lines:
    stripped = line.strip()
    
    # Уменьшаем отступ для закрывающих блоки строк
    if stripped.startswith(('return', 'break', 'continue', 'pass')) or \
       stripped in ('else:', 'elif', 'except:', 'finally:'):
        indent_level = max(0, indent_level - 1)
    
    # Уменьшаем отступ для строк, закрывающих блоки
    if stripped and not stripped.startswith(('#', '"""', "'''")) and \
       not any(stripped.startswith(kw) for kw in ['def ', 'class ', 'async def ', '@']) and \
       not stripped.endswith(':'):
        # Проверяем, не должна ли эта строка быть с меньшим отступом
        pass
    
    # Форматируем строку с правильным отступом
    if stripped:
        formatted_line = ' ' * (indent_level * 4) + stripped
    else:
        formatted_line = ''
    
    formatted_lines.append(formatted_line)
    
    # Увеличиваем отступ для строк, начинающих блоки
    if stripped.endswith(':'):
        indent_level += 1

# Собираем обратно
formatted_content = '\n'.join(formatted_lines)

with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.write(formatted_content)

print("✅ Файл полностью переформатирован!")
