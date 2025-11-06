import os
import asyncio
import logging
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle(request):
    return web.Response(text="🚀 Бот работает! Используйте Telegram бота.")

async def start_bot():
    """Запускает бота в отдельном процессе"""
    try:
        import universal_search_bot
        logger.info("Starting Telegram bot...")
        await universal_search_bot.main()
    except Exception as e:
        logger.error(f"Bot error: {e}")

async def start_background_tasks(app):
    app['bot_task'] = asyncio.create_task(start_bot())

async def cleanup_background_tasks(app):
    app['bot_task'].cancel()
    await app['bot_task']

def create_app():
    app = web.Application()
    app.router.add_get('/', handle)
    
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)
