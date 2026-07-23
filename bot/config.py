"""Конфигурация бота: токен, список админов, путь к БД.

Значения читаются из переменных окружения (.env поддерживается через
python-dotenv, если установлен).
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

# Корень проекта (на уровень выше пакета bot/)
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path, overwrite: bool = False) -> None:
    """Простой парсер .env: KEY='value' / KEY=value."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not value:
            continue
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1].replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\").replace('\\"', '"')
        if overwrite:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)


with contextlib.suppress(ImportError):
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR / ".env.example")

# Если python-dotenv не установлен — загружаем вручную (.env приоритетнее .env.example)
_load_env_file(BASE_DIR / ".env", overwrite=True)
_load_env_file(BASE_DIR / ".env.example", overwrite=False)

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
