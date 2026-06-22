"""Построители inline-клавиатур.

Используется простая текстовая схема payload вида ``action:arg1:arg2``.
Разбор выполняется хелпером :func:`parse_cb`.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from . import texts


def parse_cb(payload: str | None) -> list[str]:
    """Разбивает payload на части по ':'. Пустой payload -> []"""
    if not payload:
        return []
    return payload.split(":")


# ── Меню до регистрации ────────────────────────────────────────────────────
def pre_registration_menu() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Часто задаваемые вопросы", payload="faq"))
    kb.row(CallbackButton(text="Справочная информация об администраторах",
                          payload="admins"))
    kb.row(CallbackButton(text="Регистрация", payload="reg:start"))
    return kb


# ── Главное меню по ролям ──────────────────────────────────────────────────
def main_menu(role: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    
    if role == "student":
        # Основные функции студента
        kb.row(CallbackButton(text="Выбор проекта", payload="task:menu"))
        kb.row(CallbackButton(text="Примеры отчётности", payload="templates"))
        # Информация и помощь
        kb.row(CallbackButton(text="Мой профиль", payload="profile"))
        kb.row(CallbackButton(text="FAQ", payload="faq"))
        kb.row(CallbackButton(text="Контакты", payload="admins"))
        kb.row(CallbackButton(text="Обратная связь", payload="fb:start"))
        
    elif role == "teacher":
        # Основные функции преподавателя
        kb.row(CallbackButton(text="Подать заявку на проект", payload="app:start"))
        kb.row(CallbackButton(text="Список проектов", payload="task:list"))
        # Информация и помощь
        kb.row(CallbackButton(text="Мой профиль", payload="profile"))
        kb.row(CallbackButton(text="FAQ", payload="faq"))
        kb.row(CallbackButton(text="Контакты", payload="admins"))
        kb.row(CallbackButton(text="Обратная связь", payload="fb:start"))
        
    elif role == "partner":
        # Основные функции партнёра
        kb.row(CallbackButton(text="Подать заявку на проект", payload="app:start"))
        # Информация и помощь
        kb.row(CallbackButton(text="FAQ", payload="faq"))
        kb.row(CallbackButton(text="Контакты", payload="admins"))
        kb.row(CallbackButton(text="Обратная связь", payload="fb:start"))
        
    elif role == "admin":
        # Функционал администратора согласно ТЗ (раздел 3.3)
        kb.row(CallbackButton(text="📋 Админ-панель", payload="apanel:main"))
        kb.row(CallbackButton(text="❓ FAQ", payload="faq"))
        kb.row(CallbackButton(text="📞 Контакты", payload="admins"))
        kb.row(CallbackButton(text="💬 Обратная связь", payload="fb:start"))
    else:
        # Меню для незарегистрированных
        kb.row(CallbackButton(text="FAQ", payload="faq"))
        kb.row(CallbackButton(text="Контакты", payload="admins"))
        
    return kb


def back_button(payload: str = "menu") -> CallbackButton:
    return CallbackButton(text="Назад", payload=payload)


# ── ЧаВо ───────────────────────────────────────────────────────────────────
def faq_list(items: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for row in items:
        kb.row(CallbackButton(text=row["question"], payload=f"faq:q:{row['id']}"))
    kb.row(CallbackButton(text="Задать свой вопрос", payload="faq:ask"))
    kb.row(back_button())
    return kb


def faq_manage(items: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    """Меню управления FAQ для администраторов."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Добавить FAQ", payload="faq:add"))
    for row in items:
        kb.row(CallbackButton(
            text=f"Удалить {row['question'][:40]}...",
            payload=f"faq:delete:{row['id']}"
        ))
    kb.row(back_button())
    return kb


def faq_back(is_admin: bool = False) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="К списку вопросов", payload="faq"))
    if is_admin:
        kb.row(CallbackButton(text="Управление FAQ", payload="faq:manage"))
    kb.row(back_button())
    return kb


# ── Регистрация ────────────────────────────────────────────────────────────
def role_select() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Студент", payload="reg:role:student"))
    kb.row(CallbackButton(text="Преподаватель", payload="reg:role:teacher"))
    kb.row(CallbackButton(text="Социальный заказчик", payload="reg:role:partner"))
    return kb


def institute_select() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for inst in texts.INSTITUTES:
        kb.row(CallbackButton(text=inst, payload=f"reg:inst:{inst}"))
    return kb


def course_select() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    row_btns = [CallbackButton(text=c, payload=f"reg:course:{c}")
                for c in texts.COURSES]
    kb.row(*row_btns)
    return kb


# ── Выбор задачи (студент) ─────────────────────────────────────────────────
def team_role_select() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Лидер команды", payload="task:role:leader"))
    kb.row(CallbackButton(text="Участник команды", payload="task:role:member"))
    kb.row(back_button())
    return kb


def task_choose_list(tasks: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for t in tasks:
        kb.row(CallbackButton(text=t["title"], payload=f"task:open:{t['id']}"))
    kb.row(back_button())
    return kb


def task_card_actions(task_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Выбрать задачу",
                          payload=f"task:pick:{task_id}"))
    kb.row(CallbackButton(text="Назад", payload="task:back_list"))
    return kb


def task_confirm(task_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Подтвердить выбор",
                          payload=f"task:confirm:{task_id}"))
    kb.row(CallbackButton(text="Назад", payload="task:back_list"))
    return kb


def teams_join_list(teams: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for t in teams:
        kb.row(CallbackButton(text=t["name"], payload=f"task:join:{t['id']}"))
    kb.row(back_button())
    return kb


# ── Подтверждение участия в событии/созвоне ────────────────────────────────
def event_response(event_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(
        CallbackButton(text="Буду присутствовать",
                       payload=f"evt:yes:{event_id}"),
        CallbackButton(text="Не буду присутствовать",
                       payload=f"evt:no:{event_id}"),
    )
    return kb


# ── Верификация (админ) ────────────────────────────────────────────────────
def verify_actions(user_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(
        CallbackButton(text="Подтвердить", payload=f"ver:approve:{user_id}"),
        CallbackButton(text="Отклонить", payload=f"ver:reject:{user_id}"),
    )
    return kb


# ── Управление задачами (админ) ────────────────────────────────────────────
def task_admin_menu() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Добавить задачу", payload="tadm:add"))
    kb.row(CallbackButton(text="Список задач", payload="tadm:list"))
    kb.row(CallbackButton(text="Выгрузить задачи в Excel",
                          payload="tadm:export"))
    kb.row(back_button())
    return kb


def task_admin_list(tasks: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for t in tasks:
        flag = "•" if t["active"] else "•"
        kb.row(CallbackButton(text=f"{flag} {t['title']}",
                              payload=f"tadm:view:{t['id']}"))
    kb.row(back_button("tadm:menu"))
    return kb


def task_admin_actions(task_id: int, active: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    toggle = "Деактивировать" if active else "Активировать"
    kb.row(CallbackButton(text=f"{toggle}",
                          payload=f"tadm:toggle:{task_id}"))
    kb.row(CallbackButton(text="❌ Удалить", payload=f"tadm:del:{task_id}"))
    kb.row(back_button("tadm:list"))
    return kb


# ── Мемы (админ) ───────────────────────────────────────────────────────────
def memes_admin_menu(memes: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Добавить/изменить мем", payload="meme:add"))
    for m in memes:
        kb.row(CallbackButton(text=f"Удалить {m['code_word']}",
                              payload=f"meme:del:{m['code_word']}"))
    kb.row(back_button())
    return kb


# ── Созвоны: выбор аудитории ───────────────────────────────────────────────
def call_recipients_menu() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Конкретная команда", payload="call:team"))
    kb.row(CallbackButton(text="Все студенты", payload="call:allst"))
    kb.row(CallbackButton(text="Все пользователи", payload="call:all"))
    kb.row(back_button())
    return kb


def teams_pick_list(teams: Iterable[sqlite3.Row], action: str
                    ) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for t in teams:
        kb.row(CallbackButton(text=t["name"], payload=f"{action}:{t['id']}"))
    kb.row(back_button())
    return kb


def cancel_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Отмена", payload="cancel"))
    return kb


def skip_cancel_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(
        CallbackButton(text="Пропустить", payload="skip"),
        CallbackButton(text="Отмена", payload="cancel"),
    )
    return kb


# ── Управление контактами администраторов ──────────────────────────────────
def admin_contacts_manage(contacts: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    """Меню управления контактами администраторов."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Добавить контакт", payload="admins:add"))
    for contact in contacts:
        kb.row(CallbackButton(
            text=f"Редактировать {contact['fio']}",
            payload=f"admins:edit:{contact['id']}"
        ))
    kb.row(back_button())
    return kb


def admin_contact_edit_menu(contact_id: int) -> InlineKeyboardBuilder:
    """Меню редактирования контакта."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="❌ Удалить контакт", 
                          payload=f"admins:delete:{contact_id}"))
    kb.row(back_button("admins:manage"))
    return kb


def main_menu_kb() -> InlineKeyboardBuilder:
    """Кнопка возврата в главное меню."""
    kb = InlineKeyboardBuilder()
    kb.row(back_button())
    return kb
