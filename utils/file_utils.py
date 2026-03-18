#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Вспомогательный модуль для работы с файлами
"""

import os
import pandas as pd
import json
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileManager:
    """
    Класс для управления файловыми операциями
    """
    
    def __init__(self):
        self.start_time = datetime.now()
    
    def check_file_exists(self, filepath):
        """
        Проверка существования файла
        
        Args:
            filepath: путь к файлу
            
        Returns:
            True если файл существует, иначе False
        """
        exists = os.path.isfile(filepath)
        if not exists:
            logger.warning(f"Файл не найден: {filepath}")
        return exists
    
    def get_file_size(self, filepath):
        """
        Получение размера файла в MB
        
        Args:
            filepath: путь к файлу
            
        Returns:
            размер файла в MB
        """
        if self.check_file_exists(filepath):
            size_bytes = os.path.getsize(filepath)
            size_mb = size_bytes / (1024 * 1024)
            return size_mb
        return 0
    
    def load_categories(self, filepath):
        """
        Загрузка файла с категориями
        
        Args:
            filepath: путь к файлу категорий
            
        Returns:
            DataFrame с категориями или None в случае ошибки
        """
        try:
            # Проверяем расширение файла
            if filepath.endswith('.xlsx'):
                df = pd.read_excel(filepath)
            elif filepath.endswith('.csv'):
                df = pd.read_csv(filepath, encoding='utf-8-sig')
            else:
                logger.error(f"Неподдерживаемый формат файла: {filepath}")
                return None
            
            logger.info(f"Загружен файл категорий: {filepath}")
            logger.info(f"Количество строк: {len(df)}")
            logger.info(f"Колонки: {list(df.columns)}")
            
            # Проверяем наличие необходимых колонок
            required_cols = ['Категория', 'Основная категория', 'Подкатегория', 'Полный путь']
            existing_cols = [col for col in required_cols if col in df.columns]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"В файле категорий отсутствуют колонки: {missing_cols}")
                logger.info(f"Доступные колонки: {existing_cols}")
            
            # Заполняем пропущенные значения
            df = df.fillna('')
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки категорий: {e}")
            return None
    
    def load_commissions(self, filepath):
        """
        Загрузка файла со ставками комиссии
        
        Args:
            filepath: путь к файлу со ставками
            
        Returns:
            DataFrame со ставками или None в случае ошибки
        """
        try:
            # Пропускаем первые 2 строки с метаданными
            if filepath.endswith('.xlsx'):
                df = pd.read_excel(filepath, header=2)
            elif filepath.endswith('.csv'):
                # Для CSV пропускаем первые 2 строки
                df = pd.read_csv(filepath, encoding='utf-8-sig', skiprows=2)
            else:
                logger.error(f"Неподдерживаемый формат файла: {filepath}")
                return None
            
            logger.info(f"Загружен файл со ставками: {filepath}")
            logger.info(f"Количество записей: {len(df)}")
            logger.info(f"Колонки: {list(df.columns)}")
            
            # Переименовываем колонки для удобства
            new_columns = []
            for i, col in enumerate(df.columns):
                if i == 0:
                    new_columns.append('Категория')
                elif i == 1:
                    new_columns.append('Тип товара')
                else:
                    # Сохраняем оригинальные названия ценовых диапазонов
                    if pd.notna(col):
                        new_columns.append(str(col).strip())
                    else:
                        new_columns.append(f'Цена_{i-1}')
            
            if len(new_columns) == len(df.columns):
                df.columns = new_columns
            
            # Заполняем пропущенные значения
            df = df.fillna('')
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки ставок: {e}")
            return None
    
    def save_result(self, df, filepath):
        """
        Сохранение результата в Excel файл
        
        Args:
            df: DataFrame с результатами
            filepath: путь для сохранения
            
        Returns:
            True если успешно, иначе False
        """
        try:
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(os.path.abspath(filepath)) if os.path.dirname(filepath) else '.', exist_ok=True)
            
            # Сохраняем в Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Категории', index=False)
                
                # Добавляем лист с информацией
                info_df = pd.DataFrame({
                    'Параметр': [
                        'Дата создания',
                        'Всего категорий',
                        'Найдено ставок',
                        'Ценовые диапазоны'
                    ],
                    'Значение': [
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        len(df),
                        df.filter(like='Комиссия').notna().any(axis=1).sum(),
                        ', '.join([col for col in df.columns if 'Комиссия' in col])
                    ]
                })
                info_df.to_excel(writer, sheet_name='Информация', index=False)
            
            logger.info(f"Результат сохранен: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения результата: {e}")
            return False
    
    def save_unmatched(self, unmatched_list, filename='unmatched_categories.json'):
        """
        Сохранение списка не найденных категорий в JSON
        
        Args:
            unmatched_list: список не найденных категорий
            filename: имя файла для сохранения
        """
        try:
            # Формируем данные для сохранения
            data = {
                'timestamp': datetime.now().isoformat(),
                'total_unmatched': len(unmatched_list),
                'categories': unmatched_list
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Список не найденных категорий сохранен в {filename}")
            logger.info(f"Всего не найдено: {len(unmatched_list)}")
            
        except Exception as e:
            logger.error(f"Не удалось сохранить список не найденных категорий: {e}")
    
    def load_unmatched(self, filename='unmatched_categories.json'):
        """
        Загрузка списка не найденных категорий из JSON
        
        Args:
            filename: имя файла для загрузки
            
        Returns:
            список не найденных категорий или None
        """
        try:
            if self.check_file_exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                logger.info(f"Загружен список не найденных категорий из {filename}")
                logger.info(f"Всего записей: {data.get('total_unmatched', 0)}")
                
                return data.get('categories', [])
        except Exception as e:
            logger.error(f"Не удалось загрузить список не найденных категорий: {e}")
        
        return None
    
    def create_backup(self, filepath):
        """
        Создание резервной копии файла
        
        Args:
            filepath: путь к файлу
            
        Returns:
            путь к резервной копии или None
        """
        try:
            if not self.check_file_exists(filepath):
                return None
            
            # Создаем имя для backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{filepath}.backup_{timestamp}"
            
            # Копируем файл
            import shutil
            shutil.copy2(filepath, backup_path)
            
            logger.info(f"Создана резервная копия: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return None