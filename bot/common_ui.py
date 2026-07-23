"""Общие UI-помощники: главное меню, уведомления администраторам и т.п."""

from __future__ import annotations

import sqlite3
from typing import Optional

from . import keyboards, repo, texts
from .instance import bot


def full_name(user: sqlite3.Row) -> str:
    parts = [user["last_name"], user["first_name"], user["patronymic"]]
    return " ".join(p for p in parts if p) or (user["display_name"] or "—")


async def send_main_menu(user_id: int, greeting: Optional[str] = None) -> None:
    """Отправляет пользователю меню, соответствующее его статусу и роли."""
    user = repo.get_user(user_id)

    # Не зарегистрирован (нет роли) — меню до регистрации.
    if user is None or not user["role"]:
        await bot.send_message(
            user_id=user_id,
            text=greeting or (
                f"{texts.BOT_NAME}\n\nВыберите действие. Полный функционал "
                "доступен после регистрации."
            ),
            attachments=[keyboards.pre_registration_menu().as_markup()],
        )
        return

    # Полное меню по роли.
    role_label = texts.ROLE_LABELS.get(user["role"], "")
    name = user["first_name"] or user["display_name"] or "Пользователь"
    
    # Персонализированное приветствие
    if greeting:
        menu_text = greeting
    else:
        menu_text = f"👋 Привет, {name}!\n\n📚 {texts.BOT_NAME}\n\n"
        
        if user["role"] == "student":
            menu_text += "🎓 Выбери проект и начни работу над ним в команде!"
        elif user["role"] == "teacher":
            menu_text += "👨‍🏫 Предложи свой проект или посмотри существующие."
        elif user["role"] == "partner":
            menu_text += "🤝 Предложи проект для студентов."
        elif user["role"] == "admin":
            menu_text += "Панель управления программой «Обучение служением»"
        
    await bot.send_message(
        user_id=user_id,
        text=menu_text,
        attachments=[keyboards.main_menu(user["role"]).as_markup()],
    )


async def notify_admins(text: str, attachments=None) -> None:
    """Рассылает сообщение всем подтверждённым администраторам."""
    for admin_id in repo.list_admin_user_ids():
        try:
            await bot.send_message(
                user_id=admin_id, text=text, attachments=attachments
            )
        except Exception:  # noqa: BLE001 — не падаем из-за одного получателя
            continue


async def notify_admins_with_markup(text: str, markup) -> None:
    """Рассылает сообщение с inline-клавиатурой всем админам."""
    attachments = [markup.as_markup()] if markup else None
    await notify_admins(text, attachments=attachments)


async def notify_students(text: str, attachments=None) -> None:
    """Рассылает сообщение всем подтверждённым студентам."""
    for student_id in repo.list_student_user_ids():
        try:
            await bot.send_message(
                user_id=student_id, text=text, attachments=attachments
            )
        except Exception:  # noqa: BLE001 — не падаем из-за одного получателя
            continue


def require_verified(user_id: int) -> bool:
    return repo.is_verified(user_id)


def require_role(user_id: int, *roles: str) -> bool:
    user = repo.get_user(user_id)
    return bool(user and user["role"] in roles)
