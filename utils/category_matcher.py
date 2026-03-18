#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для сопоставления категорий со ставками комиссии
"""

import re
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from collections import Counter, defaultdict
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CategoryMatcher:
    """
    Класс для сопоставления категорий с подходящими ставками комиссии
    """
    
    def __init__(self, categories_df, commissions_df):
        """
        Инициализация с данными
        
        Args:
            categories_df: DataFrame с категориями
            commissions_df: DataFrame со ставками комиссии
        """
        self.categories_df = categories_df.copy()
        self.commissions_df = commissions_df.copy()
        
        # Ценовые диапазоны
        self.price_ranges = [
            'до 100 руб.',
            'свыше 100 до 300 руб.',
            'свыше 300 до 1500 руб.',
            'свыше 1500 до 5000 руб.',
            'свыше 5000 до 10 000 руб.',
            'свыше 10 000 руб.'
        ]
        
        # Стоп-слова для фильтрации
        self.stop_words = {
            'и', 'в', 'на', 'с', 'для', 'по', 'от', 'до', 'и', 'а', 
            'но', 'или', 'из', 'у', 'к', 'о', 'про', 'без', 'над',
            'под', 'за', 'при', 'через', 'после', 'во', 'об', 'не',
            'нет', 'да', 'это', 'что', 'как', 'так', 'все', 'еще',
            'уже', 'был', 'была', 'были', 'быть', 'себя', 'для', 'fresh'
        }
        
        # Создаем карту для быстрого поиска
        logger.info("Построение карты сопоставления...")
        self.commission_map = self._build_commission_map()
        self.keyword_index = self._build_keyword_index()
        
        logger.info(f"Построено {len(self.commission_map)} записей в карте")
        logger.info(f"Построено {len(self.keyword_index)} ключевых слов")
    
    def _normalize_text(self, text):
        """
        Нормализация текста для сравнения
        
        Args:
            text: исходный текст
            
        Returns:
            нормализованный текст
        """
        if not isinstance(text, str):
            return ''
        
        # Приводим к нижнему регистру
        text = text.lower()
        
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Удаляем знаки препинания и спецсимволы
        text = re.sub(r'[^\w\s-]', '', text)
        
        # Заменяем дефисы на пробелы
        text = text.replace('-', ' ')
        
        # Удаляем цифры в начале (если есть)
        text = re.sub(r'^\d+\s*', '', text)
        
        return text.strip()
    
    def _extract_keywords(self, text):
        """
        Извлечение ключевых слов из текста
        
        Args:
            text: исходный текст
            
        Returns:
            список ключевых слов
        """
        if not isinstance(text, str):
            return []
        
        # Нормализуем текст
        text = self._normalize_text(text)
        
        # Разбиваем на слова
        words = text.split()
        
        # Фильтруем стоп-слова и короткие слова
        keywords = [w for w in words if len(w) > 2 and w not in self.stop_words]
        
        # Добавляем биграммы для важных комбинаций
        bigrams = []
        for i in range(len(keywords) - 1):
            bigram = f"{keywords[i]} {keywords[i+1]}"
            bigrams.append(bigram)
        
        # Объединяем униграммы и биграммы
        all_keywords = keywords + bigrams
        
        return list(set(all_keywords))  # Убираем дубликаты
    
    def _build_commission_map(self):
        """
        Построение карты для быстрого поиска ставок
        
        Returns:
            словарь для поиска
        """
        commission_map = {}
        
        for idx, row in self.commissions_df.iterrows():
            category = str(row['Категория']) if pd.notna(row['Категория']) else ''
            product_type = str(row['Тип товара']) if pd.notna(row['Тип товара']) else ''
            
            # Нормализуем
            cat_norm = self._normalize_text(category)
            type_norm = self._normalize_text(product_type)
            
            # Получаем ставки для всех ценовых диапазонов
            rates = []
            
            # Определяем колонки с ценовыми диапазонами
            price_cols = []
            for col in self.commissions_df.columns:
                if 'руб' in str(col) or 'цена' in str(col).lower() or any(str(i) in str(col) for i in range(10)):
                    if col not in ['Категория', 'Тип товара']:
                        price_cols.append(col)
            
            # Если не нашли ценовые колонки, берем все после первых двух
            if not price_cols and len(self.commissions_df.columns) > 2:
                price_cols = self.commissions_df.columns[2:]
            
            for col in price_cols[:6]:  # Берем максимум 6 ценовых диапазонов
                if col in row and pd.notna(row[col]):
                    try:
                        # Преобразуем в проценты (умножаем на 100)
                        rate = float(row[col]) * 100
                        rates.append(round(rate, 2))
                    except (ValueError, TypeError):
                        rates.append(None)
                else:
                    rates.append(None)
            
            # Дополняем до 6 элементов
            while len(rates) < 6:
                rates.append(None)
            
            # Сохраняем по разным ключам
            key1 = cat_norm
            key2 = f"{cat_norm} {type_norm}".strip() if type_norm else cat_norm
            
            if key1:
                commission_map[key1] = rates
            if key2 != key1 and key2:
                commission_map[key2] = rates
            
            # Сохраняем также полную строку
            full_str = f"{category} {product_type}".strip()
            full_norm = self._normalize_text(full_str)
            if full_norm and full_norm not in commission_map:
                commission_map[full_norm] = rates
        
        return commission_map
    
    def _build_keyword_index(self):
        """
        Построение индекса ключевых слов
        
        Returns:
            словарь: ключевое слово -> список ставок
        """
        keyword_index = defaultdict(list)
        
        for key, rates in self.commission_map.items():
            keywords = self._extract_keywords(key)
            for kw in keywords:
                keyword_index[kw].append((key, rates))
        
        return keyword_index
    
    def _find_exact_match(self, text):
        """
        Поиск точного совпадения
        
        Args:
            text: текст для поиска
            
        Returns:
            список ставок или None
        """
        if not text:
            return None
        
        norm_text = self._normalize_text(text)
        
        # Прямое совпадение
        if norm_text in self.commission_map:
            return self.commission_map[norm_text]
        
        # Проверяем вхождение
        for key, rates in self.commission_map.items():
            if norm_text and key and (norm_text in key or key in norm_text):
                return rates
        
        return None
    
    def _find_fuzzy_match(self, text, threshold=70):
        """
        Поиск нечеткого совпадения
        
        Args:
            text: текст для поиска
            threshold: порог схожести
            
        Returns:
            список ставок или None
        """
        if not text:
            return None
        
        norm_text = self._normalize_text(text)
        best_match = None
        best_score = 0
        
        for key, rates in self.commission_map.items():
            if not key:
                continue
                
            score = fuzz.ratio(norm_text, key)
            
            # Учитываем частичное совпадение
            partial_score = fuzz.partial_ratio(norm_text, key)
            score = max(score, partial_score)
            
            if score > best_score and score > threshold:
                best_score = score
                best_match = rates
        
        if best_match:
            logger.debug(f"Найдено нечеткое совпадение (схожесть {best_score}%): {norm_text[:50]}...")
        
        return best_match
    
    def _find_keyword_match(self, text):
        """
        Поиск по ключевым словам
        
        Args:
            text: текст для поиска
            
        Returns:
            список ставок или None
        """
        if not text:
            return None
        
        keywords = self._extract_keywords(text)
        
        if not keywords:
            return None
        
        # Собираем все совпадения
        matches = []
        for kw in keywords:
            if kw in self.keyword_index:
                matches.extend(self.keyword_index[kw])
        
        if not matches:
            return None
        
        # Группируем по ставкам
        rate_counter = Counter()
        for key, rates in matches:
            if rates:
                rate_counter[tuple(rates)] += 1
        
        # Берем наиболее частый вариант
        if rate_counter:
            best_rates = list(rate_counter.most_common(1)[0][0])
            logger.debug(f"Найдено по ключевым словам: {best_rates}")
            return best_rates
        
        return None
    
    def _find_best_match(self, category, subcategory, full_path):
        """
        Поиск наилучшего совпадения для категории
        
        Args:
            category: название категории
            subcategory: название подкатегории
            full_path: полный путь
            
        Returns:
            список ставок или None
        """
        # Формируем строки для поиска
        main_str = str(category) if pd.notna(category) else ''
        sub_str = str(subcategory) if pd.notna(subcategory) else ''
        path_str = str(full_path) if pd.notna(full_path) else ''
        
        # Комбинируем строки
        combined_str = f"{main_str} {sub_str} {path_str}".strip()
        
        # Извлекаем последний элемент пути (самую конкретную категорию)
        last_path = ''
        if '/' in path_str:
            parts = path_str.split('/')
            last_path = parts[-1] if parts else ''
        
        # Стратегии поиска в порядке приоритета
        strategies = [
            ('последний элемент пути', last_path),
            ('полный путь', combined_str),
            ('категория + подкатегория', f"{main_str} {sub_str}".strip()),
            ('основная категория', main_str),
            ('подкатегория', sub_str)
        ]
        
        # Пробуем точное совпадение
        for strategy_name, text in strategies:
            if text and len(text) > 2:
                rates = self._find_exact_match(text)
                if rates and any(rates):
                    logger.debug(f"Точное совпадение ({strategy_name}): {text[:50]}...")
                    return rates
        
        # Пробуем нечеткое совпадение
        for strategy_name, text in strategies:
            if text and len(text) > 3:
                rates = self._find_fuzzy_match(text)
                if rates and any(rates):
                    logger.debug(f"Нечеткое совпадение ({strategy_name})")
                    return rates
        
        # Пробуем поиск по ключевым словам
        rates = self._find_keyword_match(combined_str)
        if rates and any(rates):
            logger.debug("Совпадение по ключевым словам")
            return rates
        
        return None
    
    def process_categories(self):
        """
        Обработка всех категорий и проставление ставок
        
        Returns:
            tuple: (обновленный DataFrame, словарь со статистикой)
        """
        logger.info("Начало обработки категорий...")
        
        # Создаем колонки для комиссий
        for price_range in self.price_ranges:
            col_name = f'Комиссия {price_range}'
            self.categories_df[col_name] = None
        
        # Статистика
        stats = {
            'matched': 0,
            'partial': 0,
            'not_found': 0,
            'unmatched_list': []
        }
        
        # Обрабатываем каждую категорию
        total = len(self.categories_df)
        for idx, row in self.categories_df.iterrows():
            if idx % 100 == 0 and idx > 0:
                logger.info(f"Обработано {idx}/{total} категорий")
            
            category = row.get('Категория', '')
            subcategory = row.get('Подкатегория', '')
            full_path = row.get('Полный путь', '')
            
            # Ищем ставку
            rates = self._find_best_match(category, subcategory, full_path)
            
            if rates:
                # Заполняем ставки
                filled = 0
                for i, rate in enumerate(rates):
                    if i < len(self.price_ranges) and rate is not None:
                        col_name = f'Комиссия {self.price_ranges[i]}'
                        self.categories_df.at[idx, col_name] = round(rate, 2)
                        filled += 1
                
                if filled >= 3:
                    stats['matched'] += 1
                elif filled > 0:
                    stats['partial'] += 1
                else:
                    stats['not_found'] += 1
                    self._add_to_unmatched(stats['unmatched_list'], row)
            else:
                stats['not_found'] += 1
                self._add_to_unmatched(stats['unmatched_list'], row)
        
        # Подсчет итогов
        stats['total'] = total
        stats['matched_percent'] = round(stats['matched'] / total * 100, 2) if total > 0 else 0
        stats['partial_percent'] = round(stats['partial'] / total * 100, 2) if total > 0 else 0
        stats['not_found_percent'] = round(stats['not_found'] / total * 100, 2) if total > 0 else 0
        
        logger.info(f"Обработка завершена. Совпадений: {stats['matched']}, "
                   f"Частичных: {stats['partial']}, Не найдено: {stats['not_found']}")
        
        return self.categories_df, stats
    
    def _add_to_unmatched(self, unmatched_list, row):
        """
        Добавление категории в список не найденных
        
        Args:
            unmatched_list: список для добавления
            row: строка с категорией
        """
        unmatched_list.append({
            'Категория': str(row.get('Категория', '')),
            'Основная категория': str(row.get('Основная категория', '')),
            'Подкатегория': str(row.get('Подкатегория', '')),
            'Полный путь': str(row.get('Полный путь', ''))
        })
    
    def get_statistics(self):
        """
        Получение подробной статистики
        
        Returns:
            словарь со статистикой
        """
        total = len(self.categories_df)
        commission_cols = [col for col in self.categories_df.columns if 'Комиссия' in col]
        
        # Подсчет заполненных ячеек
        filled_cells = 0
        total_cells = 0
        for col in commission_cols:
            filled = self.categories_df[col].notna().sum()
            filled_cells += filled
            total_cells += total
        
        stats = {
            'total_categories': total,
            'categories_with_commission': self.categories_df[commission_cols].notna().any(axis=1).sum(),
            'coverage_percent': round(self.categories_df[commission_cols].notna().any(axis=1).sum() / total * 100, 2) if total > 0 else 0,
            'filled_cells': filled_cells,
            'total_cells': total_cells,
            'fill_percent': round(filled_cells / total_cells * 100, 2) if total_cells > 0 else 0,
            'price_ranges': commission_cols
        }
        
        return stats
    
    def export_unmatched_for_review(self, filename='unmatched_for_review.csv'):
        """
        Экспорт не найденных категорий для ручной проверки
        
        Args:
            filename: имя файла для сохранения
        """
        # Запускаем обработку для получения списка не найденных
        _, stats = self.process_categories()
        
        if stats['unmatched_list']:
            df_unmatched = pd.DataFrame(stats['unmatched_list'])
            df_unmatched.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"Список для ручной проверки сохранен в {filename}")
            logger.info(f"Всего записей: {len(df_unmatched)}")
    
    def manual_match(self, category_name, commission_rates):
        """
        Ручное добавление соответствия
        
        Args:
            category_name: название категории
            commission_rates: список ставок для всех ценовых диапазонов
        """
        norm_name = self._normalize_text(category_name)
        self.commission_map[norm_name] = commission_rates
        
        # Обновляем индекс ключевых слов
        keywords = self._extract_keywords(category_name)
        for kw in keywords:
            self.keyword_index[kw].append((norm_name, commission_rates))
        
        logger.info(f"Добавлено ручное соответствие: {category_name}")