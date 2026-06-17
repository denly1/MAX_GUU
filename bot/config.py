"""Конфигурация бота: токен, список админов, путь к БД.

Значения читаются из переменных окружения (.env поддерживается через
python-dotenv, если установлен).
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

with contextlib.suppress(ImportError):
    from dotenv import load_dotenv

    load_dotenv()

# Корень проекта (на уровень выше пакета bot/)
BASE_DIR = Path(__file__).resolve().parent.parent

#: Токен бота MAX
BOT_TOKEN: str = os.getenv("MAX_BOT_TOKEN", "").strip()

#: Путь к файлу базы данных SQLite
DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "data/bot.db")

#: Папка для медиа (мемы, шаблоны и пр.)
ASSETS_DIR: Path = BASE_DIR / "assets"

#: Папка для генерируемых выгрузок (excel)
EXPORTS_DIR: Path = BASE_DIR / "data" / "exports"


def _parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        with contextlib.suppress(ValueError):
            ids.add(int(part))
    return ids


#: Идентификаторы «bootstrap»-администраторов (получают роль admin автоматически)
ADMIN_IDS: set[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))


def ensure_dirs() -> None:
    """Создаёт необходимые директории, если их нет."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
