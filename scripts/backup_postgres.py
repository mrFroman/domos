#!/usr/bin/env python3
"""
Скрипт для автоматического бэкапа PostgreSQL
Можно запускать как из Docker контейнера, так и напрямую
"""

import os
import sys
import subprocess
import glob
from datetime import datetime, timedelta
from pathlib import Path

# Переменные окружения
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "domos")
POSTGRES_USER = os.getenv("POSTGRES_USER", "domos")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups/postgres")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "7"))

def log(message):
    """Логирование с временной меткой"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def create_backup():
    """Создает бэкап PostgreSQL"""
    # Создаем директорию для бэкапов если её нет
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    
    # Формат имени файла: domos_YYYY-MM-DD_HH-MM-SS.sql.gz
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(BACKUP_DIR, f"domos_{timestamp}.sql.gz")
    
    log(f"Начинаем создание бэкапа PostgreSQL...")
    log(f"База: {POSTGRES_DB}, Хост: {POSTGRES_HOST}:{POSTGRES_PORT}")
    
    # Устанавливаем переменную окружения для пароля
    env = os.environ.copy()
    env["PGPASSWORD"] = POSTGRES_PASSWORD
    
    # Создаем бэкап используя pg_dump
    try:
        cmd = [
            "pg_dump",
            "-h", POSTGRES_HOST,
            "-p", POSTGRES_PORT,
            "-U", POSTGRES_USER,
            "-d", POSTGRES_DB,
            "--format=custom",
            "--compress=9",
            "--file", backup_file,
            "--verbose"
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Получаем размер файла
        file_size = os.path.getsize(backup_file)
        file_size_mb = file_size / (1024 * 1024)
        
        log(f"✅ Бэкап успешно создан: {backup_file}")
        log(f"Размер бэкапа: {file_size_mb:.2f} MB")
        
        return backup_file
        
    except subprocess.CalledProcessError as e:
        log(f"❌ Ошибка при создании бэкапа: {e}")
        log(f"Stderr: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)

def cleanup_old_backups():
    """Удаляет бэкапы старше RETENTION_DAYS дней"""
    log(f"Удаляем бэкапы старше {RETENTION_DAYS} дней...")
    
    backup_pattern = os.path.join(BACKUP_DIR, "domos_*.sql.gz")
    backup_files = glob.glob(backup_pattern)
    
    if not backup_files:
        log("Бэкапы не найдены")
        return
    
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted_count = 0
    
    for backup_file in backup_files:
        try:
            # Получаем время модификации файла
            file_time = datetime.fromtimestamp(os.path.getmtime(backup_file))
            
            if file_time < cutoff_date:
                os.remove(backup_file)
                deleted_count += 1
                log(f"Удален старый бэкап: {os.path.basename(backup_file)}")
        except Exception as e:
            log(f"⚠️ Ошибка при удалении {backup_file}: {e}")
    
    if deleted_count > 0:
        log(f"✅ Удалено старых бэкапов: {deleted_count}")
    else:
        log("Старые бэкапы не найдены")

def list_backups():
    """Показывает список текущих бэкапов"""
    backup_pattern = os.path.join(BACKUP_DIR, "domos_*.sql.gz")
    backup_files = sorted(glob.glob(backup_pattern), reverse=True)
    
    if backup_files:
        log(f"Текущие бэкапы (последние 7):")
        for backup_file in backup_files[:7]:
            file_size = os.path.getsize(backup_file)
            file_size_mb = file_size / (1024 * 1024)
            file_time = datetime.fromtimestamp(os.path.getmtime(backup_file))
            log(f"  - {os.path.basename(backup_file)} ({file_size_mb:.2f} MB, {file_time.strftime('%Y-%m-%d %H:%M:%S')})")
    else:
        log("Бэкапы не найдены")

if __name__ == "__main__":
    try:
        # Проверяем наличие необходимых переменных
        if not POSTGRES_PASSWORD:
            log("❌ Ошибка: POSTGRES_PASSWORD не установлен")
            sys.exit(1)
        
        # Создаем бэкап
        create_backup()
        
        # Удаляем старые бэкапы
        cleanup_old_backups()
        
        # Показываем список бэкапов
        list_backups()
        
        log("Готово!")
        
    except KeyboardInterrupt:
        log("Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
