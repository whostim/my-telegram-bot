import os
import asyncio
import logging
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания состояния бота
bot_task = None

async def handle(request):
    return web.Response(text="🚀 Бот работает! Используйте Telegram бота.")

async def start_bot():
    """Запускает бота"""
    try:
        import universal_search_bot
        logger.info("Starting Telegram bot...")
        await universal_search_bot.main()
    except Exception as e:
        logger.error(f"Bot error: {e}")

async def on_startup(app):
    """Запускается при старте приложения"""
    global bot_task
    if bot_task is None:
        bot_task = asyncio.create_task(start_bot())

async def on_shutdown(app):
    """Запускается при остановке приложения"""
    global bot_task
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass

def create_app():
    app = web.Application()
    app.router.add_get('/', handle)
    
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)
