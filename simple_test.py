print("✅ Python работает!")

try:
    import dotenv
    print("✅ python-dotenv установлен")
except ImportError:
    print("❌ python-dotenv НЕ установлен")

try:
    import aiogram
    print("✅ aiogram установлен")
except ImportError:
    print("❌ aiogram НЕ установлен")
