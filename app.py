import os
import asyncio
from aiohttp import web
import universal_search_bot

async def handle(request):
    return web.Response(text="🚀 Бот работает")

async def start_bot():
    try:
        print("Starting bot...")
        await universal_search_bot.main()
    except Exception as e:
        print(f"Bot error: {e}")

if __name__ == '__main__':
    # Создаем приложение
    app = web.Application()
    app.router.add_get('/', handle)
    
    # Запускаем бота в фоне
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 5000))
    web.run_app(app, host='0.0.0.0', port=port, print=lambda x: None)
