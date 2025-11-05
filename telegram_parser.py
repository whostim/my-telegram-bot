import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.types import Message, Channel
import re
from tg_config import TelegramConfig

logger = logging.getLogger(__name__)

class TelegramChannelParser:
    def __init__(self):
        self.config = TelegramConfig()
        self.client = None
        
    async def setup_client(self):
        """Настройка клиента Telegram"""
        if not self.config.API_ID or not self.config.API_HASH:
            logger.error("❌ API_ID и API_HASH не установлены в .env файле")
            return False
            
        try:
            self.client = TelegramClient(
                'tg_session', 
                self.config.API_ID, 
                self.config.API_HASH
            )
            await self.client.start()
            logger.info("✅ Telegram клиент запущен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Telegram клиента: {e}")
            return False
    
    async def search_in_channels(self, query, hours_back=24, limit_per_channel=10):
        """Поиск сообщений в Telegram каналах"""
        if not self.client:
            if not await self.setup_client():
                return []
        
        results = []
        since_date = datetime.now() - timedelta(hours=hours_back)
        
        for channel in self.config.TELEGRAM_CHANNELS:
            try:
                logger.info(f"🔍 Ищу в канале: {channel}")
                
                # Получаем entity канала
                entity = await self.client.get_entity(channel)
                
                # Ищем сообщения
                async for message in self.client.iter_messages(
                    entity, 
                    limit=limit_per_channel,
                    offset_date=since_date,
                    search=query
                ):
                    if message.text:
                        # Проверяем релевантность
                        content = message.text.lower()
                        if (query.lower() in content or 
                            any(keyword in content for keyword in self.config.KEYWORDS)):
                            
                            # Форматируем текст сообщения
                            title = self.extract_title(message.text)
                            description = message.text[:200] + '...' if len(message.text) > 200 else message.text
                            
                            results.append({
                                'title': title,
                                'url': f"https://t.me/{channel}/{message.id}",
                                'source': f"Telegram: {channel}",
                                'description': description,
                                'date': message.date.strftime("%Y-%m-%d %H:%M"),
                                'timestamp': message.date.timestamp(),
                                'views': getattr(message, 'views', 0),
                                'type': 'telegram_post'
                            })
                            
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить доступ к каналу {channel}: {e}")
                continue
        
        # Сортируем по дате (сначала новые)
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results
    
    def extract_title(self, text):
        """Извлекает заголовок из текста сообщения"""
        # Берем первую строку или первые 100 символов
        lines = text.split('\n')
        for line in lines:
            if line.strip() and len(line.strip()) > 10:
                return line.strip()[:100] + '...' if len(line.strip()) > 100 else line.strip()
        
        return text[:100] + '...' if len(text) > 100 else text
    
    async def get_channel_info(self, channel_username):
        """Получение информации о канале"""
        if not self.client:
            await self.setup_client()
        
        try:
            entity = await self.client.get_entity(channel_username)
            return {
                'title': getattr(entity, 'title', 'Неизвестно'),
                'username': getattr(entity, 'username', 'Неизвестно'),
                'participants_count': getattr(entity, 'participants_count', 0),
                'description': getattr(entity, 'about', 'Описание отсутствует')
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о канале {channel_username}: {e}")
            return None
    
    async def close(self):
        """Закрытие соединения"""
        if self.client:
            await self.client.disconnect()

# Альтернативный парсер для случаев, когда нет API доступа
class SimpleTelegramParser:
    def __init__(self):
        self.config = TelegramConfig()
    
    async def search_in_channels(self, query, hours_back=24, limit_per_channel=5):
        """Упрощенный поиск (возвращает демо-данные)"""
        # Демо-данные для тестирования
        demo_posts = [
            {
                'title': f'🔍 Результаты поиска по: {query}',
                'url': f'https://t.me/s/{query}',
                'source': 'Telegram Search',
                'description': f'Используйте поиск в Telegram для нахождения каналов по запросу "{query}"',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp(),
                'views': 0,
                'type': 'search_link'
            },
            {
                'title': '📢 Каналы для мониторинга ЭПР',
                'url': 'https://t.me/ru_epr',
                'source': 'Telegram: ru_epr',
                'description': 'Канал о экспериментальных правовых режимах в России',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp(),
                'views': 0,
                'type': 'channel_recommendation'
            },
            {
                'title': '💼 Регуляторные песочницы для бизнеса',
                'url': 'https://t.me/regulatory_sandbox_ru',
                'source': 'Telegram: regulatory_sandbox_ru',
                'description': 'Новости о регуляторных песочницах и инновационном регулировании',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp(),
                'views': 0,
                'type': 'channel_recommendation'
            }
        ]
        
        # Добавляем рекомендации по ключевым словам
        keyword_recommendations = []
        for keyword in self.config.KEYWORDS:
            if keyword in query.lower():
                keyword_recommendations.append({
                    'title': f'🎯 По ключевому слову: {keyword}',
                    'url': f'https://t.me/search?q={keyword}',
                    'source': 'Telegram Global Search',
                    'description': f'Поиск по всем каналам Telegram по запросу "{keyword}"',
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'timestamp': datetime.now().timestamp(),
                    'views': 0,
                    'type': 'keyword_search'
                })
        
        return demo_posts + keyword_recommendations

# Тестирование парсера
async def test_telegram_parser():
    print("🔍 Тестируем Telegram парсер...")
    
    # Пробуем использовать основной парсер
    parser = TelegramChannelParser()
    results = await parser.search_in_channels("ЭПР", hours_back=24)
    
    if not results:
        print("⚠️ Основной парсер не нашел результатов, используем упрощенный...")
        simple_parser = SimpleTelegramParser()
        results = await simple_parser.search_in_channels("ЭПР")
    
    print(f"📊 Найдено постов: {len(results)}")
    
    for i, post in enumerate(results[:3], 1):
        print(f"{i}. {post['title']}")
        print(f"   📍 {post['source']}")
        print(f"   🔗 {post['url']}")
        print(f"   📅 {post['date']}")
        print()
    
    if parser.client:
        await parser.close()

if __name__ == "__main__":
    asyncio.run(test_telegram_parser())
