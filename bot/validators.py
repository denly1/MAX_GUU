"""Валидация пользовательского ввода согласно разделу 4 ТЗ."""

from __future__ import annotations

import re

# Имя/фамилия/отчество: только буквы (латиница/кириллица), дефис и пробел.
_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\- ]*$")

# Телефон в формате 8 ххх-ххх хх хх (допускаем любые разделители/их отсутствие,
# но требуем ровно 11 цифр, начинающихся с 8 или 7).
_PHONE_DIGITS_RE = re.compile(r"\D+")

# Ник в телеграм: @ + латиница/цифры/подчёркивание
_TELEGRAM_RE = re.compile(r"^@[A-Za-z0-9_]{3,}$")

# Ссылка
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def validate_name(value: str, kind: str = "имя") -> tuple[bool, str]:
    """Проверяет имя/фамилию/отчество. Возвращает (ok, очищенное_значение).

    kind используется только для текста ошибки в вызывающем коде.
    """
    value = value.strip()
    if value and _NAME_RE.match(value):
        return True, value
    return False, value


def name_error(kind: str) -> str:
    return f"Не похоже на {kind}. Попробуйте еще раз"


def validate_phone(value: str) -> tuple[bool, str]:
    """Проверяет телефон, возвращает (ok, нормализованный_формат)."""
    digits = _PHONE_DIGITS_RE.sub("", value)
    if len(digits) == 11 and digits[0] in ("8", "7"):
        d = "8" + digits[1:]
        formatted = f"{d[0]} {d[1:4]}-{d[4:7]} {d[7:9]} {d[9:11]}"
        return True, formatted
    return False, value


PHONE_ERROR = (
    "Не похоже на номер телефона. Введите в формате 8 ххх-ххх хх хх"
)


def validate_password(value: str) -> tuple[bool, str]:
    """Пароль — только числовое значение."""
    value = value.strip()
    if value.isdigit():
        return True, value
    return False, value


PASSWORD_ERROR = "Не похоже на пароль."


def validate_telegram(value: str) -> tuple[bool, str]:
    value = value.strip()
    if _TELEGRAM_RE.match(value):
        return True, value
    return False, value


TELEGRAM_ERROR = "Не похоже на ник в телеграм. Введите в формате @ххххх"


def validate_url(value: str) -> tuple[bool, str]:
    value = value.strip()
    if _URL_RE.match(value):
        return True, value
    return False, value


URL_ERROR = "Не похоже на ссылку. Введите ссылку в формате https://..."


def validate_int(value: str) -> tuple[bool, int | None]:
    value = value.strip()
    if value.isdigit():
        return True, int(value)
    return False, None
