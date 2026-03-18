#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главный запускающий файл для сопоставления категорий и ставок комиссии
Поддерживает работу как в консольном режиме, так и через Telegram бота
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime
import importlib.util
from pathlib import Path

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    # Загружаем .env файл
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
    print("✅ Загружен файл .env")
except ImportError:
    print("⚠️ python-dotenv не установлен, используем переменные окружения системы")
    pass

# Проверка наличия зависимостей
def check_dependencies():
    """Проверка установленных зависимостей"""
    required_packages = ['pandas', 'numpy', 'openpyxl', 'fuzzywuzzy', 'dotenv']
    missing_packages = []
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            if package == 'dotenv':
                package = 'python-dotenv'
            missing_packages.append(package)
    
    if missing_packages:
        print("=" * 60)
        print("❌ ОШИБКА: Отсутствуют необходимые зависимости")
        print("=" * 60)
        print(f"Не найдены: {', '.join(missing_packages)}")
        print("\nУстановите зависимости командой:")
        print("  pip install -r requirements.txt")
        print("=" * 60)
        return False
    
    return True

# Импортируем вспомогательные модули
try:
    from utils.file_utils import FileManager
    from utils.category_matcher import CategoryMatcher
    from utils.telegram_bot import CommissionBot
except ImportError as e:
    print(f"❌ Ошибка импорта вспомогательных модулей: {e}")
    print("Убедитесь, что файлы utils/file_utils.py, utils/category_matcher.py и utils/telegram_bot.py существуют")
    sys.exit(1)


class CommissionMapperApp:
    """
    Главный класс приложения для сопоставления категорий и ставок комиссии
    """
    
    def __init__(self):
        self.start_time = datetime.now()
        self.file_manager = FileManager()
        self.matcher = None
        self.bot = None
        
        # Получаем пути из переменных окружения или используем значения по умолчанию
        self.input_files = {
            'categories': os.getenv('CATEGORIES_FILE', 'data/categories_template.xlsx'),
            'commissions': os.getenv('COMMISSIONS_FILE', 'data/catcom.xlsx')
        }
        self.output_file = os.getenv('OUTPUT_FILE', 'output/comcat.xlsx')
        self.debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Токен бота
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        
    def print_header(self):
        """Вывод заголовка приложения"""
        print("=" * 70)
        print(" 🏷️  КАТЕГОРИЗАТОР СТАВОК КОМИССИИ OZON")
        print("=" * 70)
        print(f"Старт: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.debug:
            print("🔧 Режим: ОТЛАДКА")
        print("-" * 70)
        
    def print_footer(self):
        """Вывод завершающей информации"""
        elapsed = datetime.now() - self.start_time
        print("-" * 70)
        print(f"Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Время выполнения: {elapsed.total_seconds():.2f} сек")
        print("=" * 70)
        
    def check_input_files(self):
        """Проверка наличия входных файлов"""
        print("\n📁 Проверка входных файлов:")
        
        all_files_exist = True
        for name, path in self.input_files.items():
            exists = self.file_manager.check_file_exists(path)
            status = "✅" if exists else "❌"
            print(f"  {status} {path} ({name})")
            if not exists:
                all_files_exist = False
        
        if not all_files_exist:
            print("\n❌ Отсутствуют необходимые файлы!")
            return False
        
        return True
    
    def load_data(self):
        """Загрузка данных из файлов"""
        print("\n📊 Загрузка данных:")
        
        # Загружаем категории
        categories_df = self.file_manager.load_categories(self.input_files['categories'])
        if categories_df is None:
            return False
        
        # Загружаем комиссии
        commissions_df = self.file_manager.load_commissions(self.input_files['commissions'])
        if commissions_df is None:
            return False
        
        # Создаем объект для сопоставления
        self.matcher = CategoryMatcher(categories_df, commissions_df)
        
        print(f"  ✅ Загружено {len(categories_df)} категорий")
        print(f"  ✅ Загружено {len(commissions_df)} записей со ставками")
        
        return True
    
    def process_matching(self):
        """Процесс сопоставления категорий"""
        print("\n🔄 Сопоставление категорий:")
        
        # Обрабатываем категории
        result_df, stats = self.matcher.process_categories()
        
        # Выводим статистику
        print(f"  ✅ Полное совпадение: {stats['matched']}")
        print(f"  ⚠️ Частичное совпадение: {stats['partial']}")
        print(f"  ❌ Не найдено: {stats['not_found']}")
        
        # Сохраняем не найденные категории
        if stats['not_found'] > 0:
            self.file_manager.save_unmatched(stats['unmatched_list'])
        
        self.result_df = result_df
        return True
    
    def save_result(self):
        """Сохранение результатов"""
        print("\n💾 Сохранение результатов:")
        
        # Создаем выходную директорию, если её нет
        os.makedirs(os.path.dirname(self.output_file) if os.path.dirname(self.output_file) else '.', exist_ok=True)
        
        # Сохраняем основной файл
        success = self.file_manager.save_result(self.result_df, self.output_file)
        
        if success:
            # Получаем информацию о файле
            file_size = self.file_manager.get_file_size(self.output_file)
            print(f"  ✅ {self.output_file} ({file_size:.2f} MB)")
            
            # Сохраняем также в CSV для удобства
            csv_file = self.output_file.replace('.xlsx', '.csv')
            self.result_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"  ✅ {csv_file} (CSV копия)")
            
            return True
        else:
            return False
    
    def run_console(self):
        """Запуск в консольном режиме"""
        self.print_header()
        
        # Проверяем зависимости
        if not check_dependencies():
            return 1
        
        # Проверяем файлы
        if not self.check_input_files():
            return 1
        
        # Загружаем данные
        if not self.load_data():
            return 1
        
        # Выполняем сопоставление
        if not self.process_matching():
            return 1
        
        # Сохраняем результат
        if not self.save_result():
            return 1
        
        self.print_footer()
        return 0
    
    async def run_bot(self):
        """Запуск Telegram бота"""
        if not self.bot_token:
            print("❌ TELEGRAM_BOT_TOKEN не найден в .env файле!")
            print("Получите токен у @BotFather и добавьте его в .env")
            return 1
        
        print("\n🤖 Запуск Telegram бота...")
        self.bot = CommissionBot(self.bot_token, self)
        
        try:
            await self.bot.run()
        except Exception as e:
            print(f"❌ Ошибка при запуске бота: {e}")
            return 1
        
        return 0
    
    def run(self, mode='console'):
        """
        Запуск приложения в указанном режиме
        
        Args:
            mode: режим работы ('console' или 'bot')
        """
        if mode == 'console':
            return self.run_console()
        elif mode == 'bot':
            # Запускаем асинхронную функцию
            return asyncio.run(self.run_bot())
        else:
            print(f"❌ Неизвестный режим: {mode}")
            return 1


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Сопоставление категорий Ozon со ставками комиссии',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py                      # консольный режим
  python main.py --mode bot            # запуск Telegram бота
  python main.py --mode console        # консольный режим (по умолчанию)
  python main.py --categories my_cats.xlsx --commissions my_coms.xlsx
  python main.py --verbose
        """
    )
    
    parser.add_argument(
        '--mode', '-m',
        type=str,
        choices=['console', 'bot'],
        default='console',
        help='Режим работы: console (консоль) или bot (Telegram бот)'
    )
    
    parser.add_argument(
        '--categories', '-c',
        type=str,
        help='Путь к файлу с категориями (переопределяет .env)'
    )
    
    parser.add_argument(
        '--commissions', '-mc',
        type=str,
        help='Путь к файлу со ставками комиссии (переопределяет .env)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Путь для выходного файла (переопределяет .env)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод информации'
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    # Получаем аргументы командной строки
    args = parse_arguments()
    
    # Создаем приложение
    app = CommissionMapperApp()
    
    # Переопределяем пути из аргументов командной строки, если они указаны
    if args.categories:
        app.input_files['categories'] = args.categories
    if args.commissions:
        app.input_files['commissions'] = args.commissions
    if args.output:
        app.output_file = args.output
    
    # Устанавливаем режим отладки
    if args.verbose:
        app.debug = True
    
    # Запускаем в нужном режиме
    sys.exit(app.run(mode=args.mode))