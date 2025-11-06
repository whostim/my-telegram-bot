#!/bin/bash

echo "🔍 Проверяем зависимости..."

# Проверяем каждую зависимость
for package in aiohttp aiogram beautifulsoup4 python-dotenv; do
    if ! python3 -c "import $package" 2>/dev/null; then
        echo "📦 Устанавливаем $package..."
        pip3 install $package
    fi
done

echo "✅ Все зависимости установлены"
echo "🚀 Запускаем бота..."
python3 universal_search_bot.py
