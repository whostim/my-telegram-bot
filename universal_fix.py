# Универсальное исправление всех проблем с отступами после if formatted_date:
with open('universal_search_bot.py', 'r') as f:
    content = f.read()

# Исправляем ВСЕ случаи где после if formatted_date: нет строки с датой
import re

# Паттерн для поиска проблемных мест
pattern = r'(if formatted_date:\s*\n)(\s*)(response \+= f"   🔗 {article\[\'url\'\]})'

# Замена: добавляем строку с датой
def fix_indent(match):
    before = match.group(1)  # if formatted_date:\n
    indent = match.group(2)  # существующий отступ
    response_line = match.group(3)  # строка с ссылкой
    
    # Добавляем строку с датой с тем же отступом
    fixed = before + indent + 'response += f"   📅 {formatted_date}"\n' + indent + response_line
    return fixed

content = re.sub(pattern, fix_indent, content)

with open('universal_search_bot_fixed3.py', 'w') as f:
    f.write(content)

print("✅ Все проблемные места исправлены! Создан universal_search_bot_fixed3.py")
