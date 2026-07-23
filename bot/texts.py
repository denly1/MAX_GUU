"""Тексты и статические данные бота, загружаемые из .env (или .env.example).

Все пользовательские строки, FAQ, справочники, контакты, шаблоны и подписи
вынесены в переменные окружения, чтобы их можно было править на сервере без
пересборки кода.

Значения хранятся в формате JSON внутри single-quoted .env:
    BOT_NAME='"Бот | Обучение служением"'
    FAQ_ITEMS='[["Вопрос","Ответ"],...]'
"""

from __future__ import annotations

import json
import os

from . import config  # noqa: F401 - ensures env files are loaded


def _get(name: str):
    raw = os.getenv(name)
    if raw is None:
        raise RuntimeError(
            f"Missing environment variable {name}. "
            f"Make sure {config.BASE_DIR / '.env'} or "
            f"{config.BASE_DIR / '.env.example'} exists and contains {name}."
        )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in environment variable {name}: {exc}") from exc


BOT_NAME: str = _get("BOT_NAME")
WELCOME_TEXT: str = _get("WELCOME_TEXT")
REGISTRATION_DONE: str = _get("REGISTRATION_DONE")
REGISTRATION_DONE_ADMIN: str = _get("REGISTRATION_DONE_ADMIN")
NEED_REGISTRATION: str = _get("NEED_REGISTRATION")

FAQ_ITEMS: list[list[str]] = _get("FAQ_ITEMS")
ADMIN_CONTACTS: list[list[str]] = _get("ADMIN_CONTACTS")
INSTITUTES: list[str] = _get("INSTITUTES")
DEPARTMENTS: list[str] = _get("DEPARTMENTS")
COURSES: list[str] = _get("COURSES")
STUDY_PROGRAMS: list[str] = _get("STUDY_PROGRAMS")

TEMPLATE_PRESENTATION: str = _get("TEMPLATE_PRESENTATION")
TEMPLATE_VISITKA: str = _get("TEMPLATE_VISITKA")
APPLICATION_SOURCES: list[str] = _get("APPLICATION_SOURCES")
ROLE_LABELS: dict[str, str] = _get("ROLE_LABELS")
DEFAULT_MEME: list[str | None] = _get("DEFAULT_MEME")
