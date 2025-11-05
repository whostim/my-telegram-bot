import os
import asyncio
from aiohttp import web
import universal_search_bot

async def handle(request):
    return web.Response(text="🚀 Новостной бот работает! Отправьте сообщение в Telegram боту.")

async def start_bot():
    """Запускает бота в том же цикле событий"""
    await universal_search_bot.main()

async def init_app():
    """Инициализирует приложение"""
    app = web.Application()
    app.router.add_get('/', handle)
    
    # Запускаем бота в фоне
    asyncio.create_task(start_bot())
    
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    web.run_app(init_app(), host='0.0.0.0', port=port)
