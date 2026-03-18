# test_imports.py
"""
Простой скрипт для проверки правильности импортов
"""

def test_imports():
    """Проверка импорта всех модулей"""
    print("🔍 Проверка импортов...")
    
    try:
        import pandas as pd
        print("✅ pandas")
    except ImportError as e:
        print(f"❌ pandas: {e}")
    
    try:
        import numpy as np
        print("✅ numpy")
    except ImportError as e:
        print(f"❌ numpy: {e}")
    
    try:
        from fuzzywuzzy import fuzz
        print("✅ fuzzywuzzy")
    except ImportError as e:
        print(f"❌ fuzzywuzzy: {e}")
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv")
    except ImportError as e:
        print(f"❌ python-dotenv: {e}")
    
    try:
        from telegram import Update
        print("✅ python-telegram-bot")
    except ImportError as e:
        print(f"❌ python-telegram-bot: {e}")
    
    print("\n📁 Проверка модулей проекта:")
    
    try:
        from utils.file_utils import FileManager
        print("✅ utils.file_utils")
    except ImportError as e:
        print(f"❌ utils.file_utils: {e}")
    
    try:
        from utils.category_matcher import CategoryMatcher
        print("✅ utils.category_matcher")
    except ImportError as e:
        print(f"❌ utils.category_matcher: {e}")
    
    try:
        from utils.telegram_bot import CommissionBot
        print("✅ utils.telegram_bot")
    except ImportError as e:
        print(f"❌ utils.telegram_bot: {e}")
    
    print("\n✨ Проверка завершена!")

if __name__ == "__main__":
    test_imports()