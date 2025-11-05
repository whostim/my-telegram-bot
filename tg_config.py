import os
from dotenv import load_dotenv

load_dotenv()

class TelegramConfig:
    # Данные для Telegram API (получить на my.telegram.org)
    API_ID = os.getenv('API_ID', '')
    API_HASH = os.getenv('API_HASH', '')
    
    # Каналы для мониторинга (добавьте нужные каналы)
    TELEGRAM_CHANNELS = [
        'ru_epr',                    # Пример канала про ЭПР
        'regulatory_sandbox_ru',     # Пример канала про регуляторные песочницы
        'digital_economy_news',      # Цифровая экономика
        'law_innovation',            # Правовые инновации
        'startup_rus',               # Стартапы и инновации
        'tech_law_rus',              # Технологии и право
        'fintech_rus',               # Финтех
        'blockchain_rus',            # Блокчейн и крипто
        'ai_rus',                    # Искусственный интеллект
        'gov_digital',               # Цифровое правительство
    ]
    
    # Ключевые слова для поиска
    KEYWORDS = [
        'ЭПР', 'эпр',
        'экспериментальный правовой режим',
        'регуляторная песочница', 
        'цифровая песочница',
        'правовой эксперимент',
        'регуляторный эксперимент',
        'инновационный режим',
        'песочница',
        'sandbox',
        'регуляторная гибкость'
    ]
