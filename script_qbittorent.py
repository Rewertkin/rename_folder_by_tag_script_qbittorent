#!/usr/bin/env python3
import sys
import os
import logging
import re
from datetime import datetime

# --- Настройка логирования ---
log_file = os.path.join(os.path.expanduser("~"), "qbittorrent_post_rename_root.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Добавим вывод и в консоль для отладки
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)

def log_warning(message):
    logging.warning(message)

def sanitize_filename(name):
    """Убирает или заменяет недопустимые символы для имен файлов/папок."""
    # Убираем совсем плохие символы типа / \ : * ? " < > |
    name = re.sub(r'[\\/*?"<>|:]', '', name)
    # Можно заменить другие потенциально проблемные символы на подчеркивание,
    # но для простоты пока оставим так. Главное - убрать разделители пути.
    # Убираем пробелы в начале/конце
    return name.strip()

# --- Основная логика скрипта ---
if __name__ == "__main__":
    log_info("="*20 + " Скрипт переименования корневой папки запущен " + "="*20)
    log_info(f"Получены аргументы: {sys.argv}")

    # qBittorrent передает аргументы. Нам нужны:
    # %R - Корневой путь торрента (путь к первой папке торрента или путь сохранения, если папки нет)
    # %G - Теги (через запятую)
    # %N - Имя торрента (для логов)

    if len(sys.argv) < 4:
        log_error("Ошибка: Недостаточно аргументов. Ожидалось как минимум 3 аргумента от qBittorrent (%R, %G, %N).")
        log_info("Пример конфигурации в qBittorrent: /usr/bin/python3 /path/to/script.py \"%R\" \"%G\" \"%N\"")
        sys.exit(1)

    # Получаем аргументы
    # ВНИМАНИЕ: %R может быть равно %D (пути сохранения), если торрент НЕ создает корневую папку.
    # Нам нужно переименовывать только если %R - это действительно папка ВНУТРИ пути сохранения.
    torrent_root_path = sys.argv[1] # %R
    tags_str = sys.argv[2]          # %G
    torrent_name = sys.argv[3]      # %N

    log_info(f"Обработка торрента: {torrent_name}")
    log_info(f"Корневой путь торрента (%R): {torrent_root_path}")
    log_info(f"Полученные теги (%G): '{tags_str}'")

    # 1. Проверяем, есть ли теги
    if not tags_str:
        log_info("Теги отсутствуют. Переименование не требуется. Выход.")
        sys.exit(0)

    # Разделяем строку тегов на список и убираем пустые строки
    tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

    if not tags_list:
        log_info("Список тегов пуст после обработки. Выход.")
        sys.exit(0)

    # Берем ПЕРВЫЙ тег для переименования.
    # Если вам нужен *конкретный* тег (например, всегда начинающийся с 'kp'),
    # то здесь нужно изменить логику выбора тега из tags_list.
    # Пример: tag_to_use = next((tag for tag in tags_list if tag.startswith('kp')), None)
    tag_to_use = tags_list[0]
    log_info(f"Используется первый тег для переименования: '{tag_to_use}'")

    # Очищаем тег от недопустимых символов
    safe_tag = sanitize_filename(tag_to_use)
    if not safe_tag:
         log_warning(f"Тег '{tag_to_use}' после очистки стал пустым. Переименование отменено.")
         sys.exit(0)
    log_info(f"Очищенный тег для имени: '{safe_tag}'")


    # 2. Проверяем, является ли torrent_root_path действительно папкой и существует ли она
    if not os.path.exists(torrent_root_path):
        log_error(f"Ошибка: Корневой путь '{torrent_root_path}' не существует!")
        sys.exit(1)

    if not os.path.isdir(torrent_root_path):
        # Это может произойти, если торрент содержит только один файл, тогда %R указывает на файл.
        # В этом случае переименовывать папку не нужно (ее нет).
        log_info(f"Корневой путь '{torrent_root_path}' не является директорией (возможно, торрент из одного файла). Переименование папки не требуется. Выход.")
        sys.exit(0)

    # 3. Переименовываем папку
    try:
        parent_dir = os.path.dirname(torrent_root_path)
        current_name = os.path.basename(torrent_root_path)

        # Проверяем, не была ли папка уже переименована (содержит ли она уже этот тег)
        # Это простая проверка, можно улучшить при необходимости
        if current_name.endswith(f".{safe_tag}"):
            log_info(f"Папка '{current_name}' уже содержит тег '{safe_tag}'. Переименование не требуется. Выход.")
            sys.exit(0)

        # Формируем новое имя
        new_name = f"{current_name}.{safe_tag}"
        new_path = os.path.join(parent_dir, new_name)

        log_info(f"Текущее имя папки: {current_name}")
        log_info(f"Новое имя папки: {new_name}")
        log_info(f"Полный новый путь: {new_path}")

        # Проверяем, не существует ли уже папка/файл с новым именем
        if os.path.exists(new_path):
            log_warning(f"Предупреждение: Путь '{new_path}' уже существует. Переименование отменено, чтобы избежать конфликтов.")
            sys.exit(0)

        # Переименовываем
        os.rename(torrent_root_path, new_path)
        log_info(f"Успешно переименовано: '{torrent_root_path}' -> '{new_path}'")

    except OSError as e:
        log_error(f"Ошибка ОС при переименовании '{torrent_root_path}' в '{new_path}': {e}")
        sys.exit(1)
    except Exception as e:
        log_error(f"Непредвиденная ошибка: {e}")
        sys.exit(1)

    log_info("="*20 + " Скрипт завершен " + "="*20 + "\n")
    sys.exit(0)