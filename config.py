import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    
    # Ключевые слова для поиска
    KEYWORDS = [
        'экспериментальный правовой режим',
        'регуляторная песочница',
        'ЭПР',
        'цифровая песочница', 
        'инновационный правовой режим',
        'правовой эксперимент',
        'регуляторный песок',
        'sandbox',
        'регуляторная гибкость',
        'правовой режим',
        'инновационное право',
        'технологический эксперимент'
    ]
    
    # Telegram каналы для мониторинга (можно добавить любые)
    TELEGRAM_CHANNELS = [
        'rt_russian',
        'rian_ru',
        'tass_agency',
        'meduzalive',
        'lentach',
        'breakingmash',
        'readovkanews',
        'bazabazon',
        'ostorozhno_novosti',
        'netgazeti',
        'digital_gov_ru',
        'minfin_russia',
        'cbr_official',
        'government_rus',
        'duma_gov_ru',
        'economy_gov_ru',
        'vcru',
        'rbcdaily',
        'vedomosti',
        'kommersant_news'
    ]
    
    # RSS источники
    RSS_SOURCES = [
        'https://lenta.ru/rss/news',
        'https://www.vedomosti.ru/rss/news',
        'https://www.kommersant.ru/RSS/news.xml',
        'https://ria.ru/export/rss2/index.xml',
        'https://tass.ru/rss/v2.xml',
        'https://www.interfax.ru/rss.asp',
        'https://rg.ru/inc/rss/news.xml',
        'https://www.m24.ru/rss.xml',
        'https://www.rbc.ru/rssfeed/news.rss',
        'https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru'
    ]
