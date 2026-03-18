#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram бот для управления процессом сопоставления категорий
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class CommissionBot:
    """
    Telegram бот для работы с категоризатором ставок
    """
    
    def __init__(self, token, app_instance):
        """
        Инициализация бота
        
        Args:
            token: токен Telegram бота
            app_instance: экземпляр главного приложения
        """
        self.token = token
        self.app = app_instance
        self.application = None
        self.user_data = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        welcome_message = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Я бот для сопоставления категорий Ozon со ставками комиссии.\n\n"
            "📌 **Доступные команды:**\n"
            "/start - показать это сообщение\n"
            "/help - справка по использованию\n"
            "/status - проверить статус системы\n"
            "/process - запустить обработку с текущими файлами\n"
            "/download - скачать последний результат\n\n"
            "📁 **Как использовать:**\n"
            "1. Отправьте мне файл categories_template.xlsx\n"
            "2. Отправьте мне файл catcom.xlsx\n"
            "3. Используйте /process для запуска обработки\n"
            "4. Используйте /download для скачивания результата"
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "🆘 **Справка по использованию**\n\n"
            "**Команды:**\n"
            "• `/start` - приветствие\n"
            "• `/help` - эта справка\n"
            "• `/status` - статус загруженных файлов\n"
            "• `/process` - запустить обработку\n"
            "• `/download` - скачать результат\n\n"
            "**Файлы:**\n"
            "Отправьте мне файлы в формате Excel (.xlsx):\n"
            "• `categories_template.xlsx` - шаблон категорий\n"
            "• `catcom.xlsx` - файл со ставками\n\n"
            "После загрузки обоих файлов используйте `/process`"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        user_id = update.effective_user.id
        user_files = self.user_data.get(user_id, {})
        
        categories_file = user_files.get('categories')
        commissions_file = user_files.get('commissions')
        
        status_text = "📊 **Статус загруженных файлов:**\n\n"
        
        if categories_file:
            status_text += f"✅ categories_template.xlsx\n"
            status_text += f"   Имя: {categories_file['name']}\n"
            status_text += f"   Размер: {categories_file['size']} KB\n"
        else:
            status_text += "❌ categories_template.xlsx - не загружен\n"
        
        status_text += "\n"
        
        if commissions_file:
            status_text += f"✅ catcom.xlsx\n"
            status_text += f"   Имя: {commissions_file['name']}\n"
            status_text += f"   Размер: {commissions_file['size']} KB\n"
        else:
            status_text += "❌ catcom.xlsx - не загружен\n"
        
        status_text += "\n"
        
        if categories_file and commissions_file:
            status_text += "✅ Все файлы загружены! Используйте /process для обработки."
        else:
            status_text += "⚠️ Ожидаю загрузки недостающих файлов."
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def process_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /process - запуск обработки"""
        user_id = update.effective_user.id
        user_files = self.user_data.get(user_id, {})
        
        categories_file = user_files.get('categories')
        commissions_file = user_files.get('commissions')
        
        if not categories_file or not commissions_file:
            await update.message.reply_text(
                "❌ Не все файлы загружены!\n"
                "Используйте /status для проверки."
            )
            return
        
        await update.message.reply_text(
            "🔄 Начинаю обработку файлов...\n"
            "Это может занять несколько минут."
        )
        
        try:
            # Сохраняем временные файлы
            temp_dir = Path(f'temp_{user_id}')
            temp_dir.mkdir(exist_ok=True)
            
            cats_path = temp_dir / 'categories_template.xlsx'
            coms_path = temp_dir / 'catcom.xlsx'
            output_path = temp_dir / 'comcat.xlsx'
            
            # Сохраняем файлы из памяти
            with open(cats_path, 'wb') as f:
                f.write(categories_file['content'])
            with open(coms_path, 'wb') as f:
                f.write(commissions_file['content'])
            
            # Обновляем пути в приложении
            self.app.input_files['categories'] = str(cats_path)
            self.app.input_files['commissions'] = str(coms_path)
            self.app.output_file = str(output_path)
            
            # Запускаем обработку
            result = self.app.run_console()
            
            if result == 0:
                # Отправляем результат
                await update.message.reply_document(
                    document=open(output_path, 'rb'),
                    filename='comcat.xlsx',
                    caption="✅ Обработка завершена успешно!"
                )
                
                # Сохраняем результат в user_data
                with open(output_path, 'rb') as f:
                    self.user_data[user_id]['result'] = {
                        'content': f.read(),
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                await update.message.reply_text("❌ Ошибка при обработке файлов.")
            
            # Очищаем временные файлы
            import shutil
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            logger.error(f"Error processing files: {e}")
    
    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /download - скачивание результата"""
        user_id = update.effective_user.id
        user_data = self.user_data.get(user_id, {})
        
        result = user_data.get('result')
        if not result:
            await update.message.reply_text(
                "❌ Результат не найден!\n"
                "Сначала загрузите файлы и выполните /process"
            )
            return
        
        # Отправляем результат
        import io
        file_obj = io.BytesIO(result['content'])
        file_obj.name = 'comcat.xlsx'
        
        await update.message.reply_document(
            document=file_obj,
            filename='comcat.xlsx',
            caption=f"✅ Результат от {result['timestamp']}"
        )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик получения файлов"""
        user_id = update.effective_user.id
        document = update.message.document
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        
        file_name = document.file_name
        
        # Проверяем тип файла
        if not file_name.endswith('.xlsx'):
            await update.message.reply_text("❌ Пожалуйста, отправьте файл в формате .xlsx")
            return
        
        # Получаем содержимое файла
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        
        # Определяем тип файла по имени
        if 'categories' in file_name.lower() or 'template' in file_name.lower():
            self.user_data[user_id]['categories'] = {
                'name': file_name,
                'content': file_content,
                'size': len(file_content) // 1024
            }
            await update.message.reply_text(f"✅ Файл категорий загружен: {file_name}")
            
        elif 'catcom' in file_name.lower() or 'commissions' in file_name.lower():
            self.user_data[user_id]['commissions'] = {
                'name': file_name,
                'content': file_content,
                'size': len(file_content) // 1024
            }
            await update.message.reply_text(f"✅ Файл со ставками загружен: {file_name}")
            
        else:
            await update.message.reply_text(
                "❌ Не удалось определить тип файла.\n"
                "Ожидаемые имена: categories_template.xlsx или catcom.xlsx"
            )
            return
        
        # Проверяем, загружены ли оба файла
        if ('categories' in self.user_data[user_id] and 
            'commissions' in self.user_data[user_id]):
            await update.message.reply_text(
                "✅ Все файлы загружены!\n"
                "Используйте /process для запуска обработки."
            )
    
    async def run(self):
        """Запуск бота"""
        # Создаем приложение
        self.application = Application.builder().token(self.token).build()
        
        # Регистрируем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("process", self.process_command))
        self.application.add_handler(CommandHandler("download", self.download_command))
        
        # Регистрируем обработчик документов
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Запускаем бота
        print("🤖 Бот запущен и готов к работе!")
        print("Нажмите Ctrl+C для остановки")
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Оставляем бота работающим
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Остановка бота...")
            await self.application.stop()