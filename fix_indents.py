import re

# Читаем файл
with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Функция для определения уровня отступа
def get_indent_level(line):
    return len(line) - len(line.lstrip())

# Исправляем отступы
fixed_lines = []
for i, line in enumerate(lines):
    # Пропускаем пустые строки
    if line.strip() == '':
        fixed_lines.append(line)
        continue
    
    # Получаем текущий уровень отступа
    current_indent = get_indent_level(line)
    
    # Проверяем, является ли строка docstring с неправильным отступом
    if '"""' in line or "'''" in line:
        # Проверяем контекст - если это docstring функции/класса, должен быть отступ
        if i > 0 and any(keyword in lines[i-1] for keyword in ['def ', 'class ', 'async def ']):
            expected_indent = get_indent_level(lines[i-1])
            if current_indent != expected_indent:
                line = ' ' * expected_indent + line.lstrip()
    
    # Проверяем другие распространенные случаи неправильных отступов
    stripped = line.lstrip()
    if (stripped.startswith('def ') or stripped.startswith('class ') or 
        stripped.startswith('async def ') or stripped.startswith('@')):
        # Эти строки должны быть на уровне 0 отступа
        if current_indent > 0:
            line = stripped
    
    fixed_lines.append(line)

# Записываем исправленный файл
with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ Отступы исправлены!")
