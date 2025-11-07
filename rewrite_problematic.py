with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Находим и переписываем проблемный блок articles.append
in_append_block = False
new_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # Ищем начало блока articles.append
    if 'articles.append({' in line and not in_append_block:
        in_append_block = True
        append_block = [line]
        
        # Собираем весь блок до закрывающей скобки
        j = i + 1
        while j < len(lines) and '})' not in lines[j]:
            append_block.append(lines[j])
            j += 1
        
        if j < len(lines):
            append_block.append(lines[j])
        
        # Проверяем блок на синтаксические ошибки
        block_text = ''.join(append_block)
        
        # Исправляем распространенные ошибки
        if "'' if time_elem else ''" in block_text:
            block_text = block_text.replace("'' if time_elem else '',", "'',")
        
        # Убеждаемся, что скобки сбалансированы
        open_braces = block_text.count('{')
        close_braces = block_text.count('}')
        if open_braces != close_braces:
            block_text = block_text.rstrip() + '}' * (open_braces - close_braces) + '\n'
        
        new_lines.append(block_text)
        i = j + 1
    else:
        new_lines.append(line)
        i += 1

# Записываем исправленный файл
with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Проблемный блок переписан!")
