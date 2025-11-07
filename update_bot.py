import re
import os

def update_bot_file():
    # Читаем текущий файл
    with open('universal_search_bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Обновляем функцию format_date
    new_format_date = '''def format_date(date_str):
    """Форматирует дату в формат дд.мм.гггг, убирает относительные форматы"""
    if not date_str:
        return ""
    
    # Убираем все относительные форматы времени
    relative_patterns = [
        r'\\d+\\s*(мес|месяц|месяцев|месяца)',
        r'\\d+\\s*(год|года|лет)',
        r'\\d+\\s*(день|дня|дней)',
        r'\\d+\\s*(недел|недели|недель)',
        r'\\d+\\s*(час|часа|часов)',
        r'\\d+\\s*(минут|минуты)',
        r'только что',
        r'вчера',
        r'сегодня',
        r'\\d+[дгмчн]',  # Сокращения: 10д, 5г, 2м и т.д.
        r'\\d+\\s*ч\\.?\\s*назад',
        r'\\d+\\s*д\\.?\\s*назад',
        r'\\d+\\s*нед\\.?\\s*назад',
        r'\\d+\\s*мес\\.?\\s*назад',
        r'\\d+\\s*г\\.?\\s*назад'
    ]
    
    for pattern in relative_patterns:
        if re.search(pattern, date_str.lower()):
            return ""
    
    # Пробуем распарсить абсолютные даты
    try:
        from datetime import datetime
        formats_to_try = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%d.%m.%Y %H:%M',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%S%z'
        ]
        
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%d.%m.%Y')
            except ValueError:
                continue
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Ошибка форматирования даты '{date_str}': {e}")
    
    return "'''
    
    # Заменяем старую функцию format_date
    content = re.sub(
        r'def format_date\(date_str\):.*?return date_str',
        new_format_date,
        content,
        flags=re.DOTALL
    )
    
    # 2. Обновляем функцию handle_text
    new_handle_text = '''@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()

    buttons = [
        "🔍 Поиск новостей",
        "🌍 Международные источники",
        "⚡ Свежие новости",
        "📊 Быстрый поиск"]
    if user_text.startswith('/') or user_text in buttons:
        return

    await message.answer(f"🔍 Ищу новости по запросу: '{user_text}'...")

    try:
        if any(word in user_text.lower()
           for word in ['russia', 'russian', 'international']):
            search_type = "international"
        else:
            search_type = "all"

        articles = await news_searcher.universal_search(user_text, search_type)

        if articles:
            russian_articles = [a for a in articles if a.get('language') == 'ru']
            english_articles = [a for a in articles if a.get('language') == 'en']

            response = f"🔍 Результаты поиска по '{user_text}':\\n\\n"

            if russian_articles and search_type != "international":
                response += "🇷🇺 Российские источники:\\n\\n"
                for i, article in enumerate(russian_articles[:4], 1):
                    response += f"{i}. {article['title']}\\n"
                    
                    # Всегда показываем источник с проверкой
                    source = article.get('source', '').strip()
                    if not source:
                        source = "Источник не указан"
                    response += f"   📰 {source}\\n"
                    
                    # Убираем дату полностью - не выводим строку с датой
                    response += f"   🔗 {article['url']}\\n\\n"

            if english_articles and search_type == "international":
                response += "🌍 Международные источники:\\n\\n"
                for i, article in enumerate(english_articles[:4], 1):
                    response += f"{i}. {article['title']}\\n"
                    
                    # Всегда показываем источник с проверкой
                    source = article.get('source', '').strip()
                    if not source:
                        source = "Источник не указан"
                    response += f"   📰 {source}\\n"
                    
                    # Убираем дату полностью - не выводим строку с датой
                    response += f"   🔗 {article['url']}\\n\\n"

            response += f"📊 Найдено статей: {len(articles)}"

        else:
            response = f"😔 По запросу '{user_text}' не найдено новостей.\\n\\n"
            response += "💡 Попробуйте изменить формулировку запроса."

        await message.answer(response)

    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        await message.answer(f"❌ Ошибка при поиске. Попробуйте другой запрос.")'''
    
    # Заменяем старую функцию handle_text
    content = re.sub(
        r'@dp.message\(\)\\s*async def handle_text\(message: types.Message\):.*?await message\.answer\(f"❌ Ошибка при поиске\. Попробуйте другой запрос\."\)',
        new_handle_text,
        content,
        flags=re.DOTALL
    )
    
    # 3. Обновляем функцию fresh_news
    new_fresh_news = '''@dp.message(lambda message: message.text == "⚡ Свежие новости")
async def fresh_news(message: types.Message):
    await message.answer("⚡ Ищу самые свежие новости")

    try:
        articles = await news_searcher.get_fresh_news_today()

        if articles:
            response = "⚡ Самые свежие новости:\\n\\n"

            for i, article in enumerate(articles, 1):
                response += f"{i}. {article['title']}\\n"
                
                # Всегда показываем источник с проверкой
                source = article.get('source', '').strip()
                if not source:
                    source = "Источник не указан"
                response += f"   📰 {source}\\n"
                
                # Убираем дату полностью - не выводим строку с датой
                response += f"   🔗 {article['url']}\\n\\n"

                if len(response) > 3500:
                    response += "... (показаны первые статьи)"
                    break

        else:
            response = "😔 Не удалось найти свежие новости за сегодня.\\n\\n"
            response += "💡 Попробуйте использовать поиск по конкретному запросу."

        await message.answer(response)

    except Exception as e:
        logger.error(f"❌ Ошибка поиска свежих новостей: {e}")
        await message.answer("❌ Ошибка при поиске свежих новостей. Попробуйте позже.")'''
    
    # Заменяем старую функцию fresh_news
    content = re.sub(
        r'@dp.message\(lambda message: message\.text == "⚡ Свежие новости"\)\\s*async def fresh_news\(message: types\.Message\):.*?await message\.answer\("❌ Ошибка при поиске свежих новостей\. Попробуйте позже\."\)',
        new_fresh_news,
        content,
        flags=re.DOTALL
    )
    
    # 4. Обновляем парсер Яндекс.Новостей для улучшения извлечения источников
    new_yandex_parser = '''    async def search_yandex_news_direct(self, query):
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://yandex.ru/news/search?text={encoded_query}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []

                    news_cards = soup.find_all('article', class_='mg-card')[:10]

                    for card in news_cards:
                        try:
                            title_elem = card.find('h2', class_='mg-card__title') or card.find('a', class_='mg-card__link')
                            if not title_elem:
                                continue

                            title = title_elem.get_text().strip()
                            link = title_elem.get('href', '')

                            if link.startswith('https://news.yandex.ru/yandsearch?'):
                                match = re.search(r'cl4url=([^&]+)', link)
                                if match:
                                    link = urllib.parse.unquote(match.group(1))
                            elif link.startswith('/'):
                                link = f"https://yandex.ru{link}"

                            source_elem = card.find('span', class_='mg-card-source__source')
                            time_elem = card.find('span', class_='mg-card-source__time')
                            desc_elem = card.find('div', class_='mg-card__annotation')

                            # Улучшенное извлечение источника
                            source_text = ""
                            if source_elem:
                                source_text = source_elem.get_text().strip()
                                # Очистка текста источника
                                source_text = re.sub(r'\\s+', ' ', source_text)
                            
                            # Если источник не найден, пробуем извлечь из URL
                            if not source_text and link:
                                try:
                                    domain = urllib.parse.urlparse(link).netloc
                                    source_text = domain.replace('www.', '').split('.')[0]
                                    source_text = source_text.capitalize()
                                except:
                                    pass
                            
                            # Значение по умолчанию
                            if not source_text:
                                source_text = "Яндекс.Новости"

                            if link and not any(
                                domain in link for domain in [
                                    'google.com/search',
                                    'yandex.ru/search']):
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'source': source_text,
                                    'date': time_elem.get_text().strip() if time_elem else '',
                                    'description': desc_elem.get_text().strip() if desc_elem else '',
                                    'language': 'ru'
                                })
                        except Exception as e:
                            logger.debug(f"Ошибка парсинга карточки Яндекс: {e}")
                            continue

                    return articles
            return []
        except Exception as e:
            logger.debug(f"Ошибка Яндекс.Новостей: {e}")
            return []'''
    
    # Заменяем старый парсер Яндекс.Новостей
    content = re.sub(
        r'async def search_yandex_news_direct\(self, query\):.*?return \[\]',
        new_yandex_parser,
        content,
        flags=re.DOTALL
    )
    
    # Записываем обновленный файл
    with open('universal_search_bot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Файл успешно обновлен!")
    print("📝 Изменения:")
    print("   - Убраны все даты из вывода")
    print("   - Улучшено отображение источников")
    print("   - Добавлена гарантированная подпись источника")
    print("   - Улучшен парсер Яндекс.Новостей")

if __name__ == "__main__":
    # Создаем резервную копию
    import shutil
    shutil.copy2('universal_search_bot.py', 'universal_search_bot_backup.py')
    print("📦 Создана резервная копия: universal_search_bot_backup.py")
    
    update_bot_file()
