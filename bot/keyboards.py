"""Построители inline-клавиатур.

Используется простая текстовая схема payload вида ``action:arg1:arg2``.
Разбор выполняется хелпером :func:`parse_cb`.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from . import repo, texts


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
        kb.row(
            CallbackButton(
                text=f"✏️ {row['question'][:35]}...",
                payload=f"faq:edit:{row['id']}"
            ),
            CallbackButton(
                text="❌",
                payload=f"faq:delete:{row['id']}"
            )
        )
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


def study_program_select(page: int = 1) -> InlineKeyboardBuilder:
    """Пагинированный список направлений подготовки."""
    items_per_page = 8
    programs = repo.list_study_programs()
    total = len(programs)
    total_pages = max(1, (total + items_per_page - 1) // items_per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page

    kb = InlineKeyboardBuilder()
    for idx, prog in enumerate(programs[start:end], start=start):
        kb.row(CallbackButton(text=prog, payload=f"reg:prog:{idx}"))

    nav = []
    if page > 1:
        nav.append(CallbackButton(text="◀️", payload=f"reg:sp:{page - 1}"))
    nav.append(CallbackButton(text=f"{page}/{total_pages}", payload=f"reg:sp:{page}"))
    if page < total_pages:
        nav.append(CallbackButton(text="▶️", payload=f"reg:sp:{page + 1}"))
    kb.row(*nav)
    kb.row(CallbackButton(text="Отмена", payload="cancel"))
    return kb


def department_select(page: int = 1) -> InlineKeyboardBuilder:
    """Пагинированный список кафедр для регистрации преподавателя."""
    items_per_page = 8
    deps = repo.list_departments()
    total_pages = max(1, (len(deps) + items_per_page - 1) // items_per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    kb = InlineKeyboardBuilder()
    for idx, dep in enumerate(deps[start:start + items_per_page], start=start):
        kb.row(CallbackButton(text=dep[:60], payload=f"reg:dep:{idx}"))
    nav = []
    if page > 1:
        nav.append(CallbackButton(text="◀️", payload=f"reg:dp:{page - 1}"))
    nav.append(CallbackButton(text=f"{page}/{total_pages}", payload=f"reg:dp:{page}"))
    if page < total_pages:
        nav.append(CallbackButton(text="▶️", payload=f"reg:dp:{page + 1}"))
    kb.row(*nav)
    kb.row(CallbackButton(text="Отмена", payload="cancel"))
    return kb


def teacher_programs_select(page: int = 1, selected: list[int] | None = None) -> InlineKeyboardBuilder:
    """Пагинированный список программ для преподавателя (мультивыбор)."""
    selected = selected or []
    items_per_page = 6
    progs = repo.list_study_programs()
    total_pages = max(1, (len(progs) + items_per_page - 1) // items_per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    kb = InlineKeyboardBuilder()
    for idx, prog in enumerate(progs[start:start + items_per_page], start=start):
        mark = "✅ " if idx in selected else ""
        kb.row(CallbackButton(text=f"{mark}{prog[:55]}", payload=f"reg:tprog:{idx}"))
    nav = []
    if page > 1:
        nav.append(CallbackButton(text="◀️", payload=f"reg:tpp:{page - 1}"))
    nav.append(CallbackButton(text=f"{page}/{total_pages}", payload=f"reg:tpp:{page}"))
    if page < total_pages:
        nav.append(CallbackButton(text="▶️", payload=f"reg:tpp:{page + 1}"))
    kb.row(*nav)
    if selected:
        kb.row(CallbackButton(text=f"Готово ({len(selected)} выбрано)", payload="reg:tpdone"))
    kb.row(CallbackButton(text="Отмена", payload="cancel"))
    return kb


def task_program_select(page: int = 1) -> InlineKeyboardBuilder:
    """Пагинированный список программ для добавления задачи администратором."""
    items_per_page = 8
    progs = repo.list_study_programs()
    total_pages = max(1, (len(progs) + items_per_page - 1) // items_per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="— Без привязки к программе —", payload="tadm:prog:none"))
    for idx, prog in enumerate(progs[start:start + items_per_page], start=start):
        kb.row(CallbackButton(text=prog[:60], payload=f"tadm:prog:{idx}"))
    nav = []
    if page > 1:
        nav.append(CallbackButton(text="◀️", payload=f"tadm:progp:{page - 1}"))
    nav.append(CallbackButton(text=f"{page}/{total_pages}", payload=f"tadm:progp:{page}"))
    if page < total_pages:
        nav.append(CallbackButton(text="▶️", payload=f"tadm:progp:{page + 1}"))
    kb.row(*nav)
    kb.row(CallbackButton(text="Отмена", payload="cancel"))
    return kb


def task_edit_program_select(task_id: int, page: int = 1) -> InlineKeyboardBuilder:
    """Пагинированный список программ для РЕДАКТИРОВАНИЯ задачи (payload tadm:edit_prog)."""
    items_per_page = 8
    progs = repo.list_study_programs()
    total_pages = max(1, (len(progs) + items_per_page - 1) // items_per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="— Без привязки к программе —",
                          payload=f"tadm:edit_prog:{task_id}:none"))
    for idx, prog in enumerate(progs[start:start + items_per_page], start=start):
        kb.row(CallbackButton(text=prog[:60], payload=f"tadm:edit_prog:{task_id}:{idx}"))
    nav = []
    if page > 1:
        nav.append(CallbackButton(text="◀️", payload=f"tadm:edit_progp:{task_id}:{page - 1}"))
    nav.append(CallbackButton(text=f"{page}/{total_pages}",
                              payload=f"tadm:edit_progp:{task_id}:{page}"))
    if page < total_pages:
        nav.append(CallbackButton(text="▶️", payload=f"tadm:edit_progp:{task_id}:{page + 1}"))
    kb.row(*nav)
    kb.row(CallbackButton(text="Отмена", payload="cancel"))
    return kb


def institute_select() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for inst in repo.list_institutes():
        kb.row(CallbackButton(text=inst, payload=f"reg:inst:{inst}"))
    return kb


def course_select() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    row_btns = [CallbackButton(text=c, payload=f"reg:course:{c}")
                for c in texts.COURSES]
    kb.row(*row_btns)
    return kb


def profile_institute_select() -> InlineKeyboardBuilder:
    """Выбор института при редактировании профиля (prefix prof:)."""
    kb = InlineKeyboardBuilder()
    for inst in repo.list_institutes():
        kb.row(CallbackButton(text=inst, payload=f"prof:inst:{inst}"))
    return kb


def profile_course_select() -> InlineKeyboardBuilder:
    """Выбор курса при редактировании профиля (prefix prof:)."""
    kb = InlineKeyboardBuilder()
    row_btns = [CallbackButton(text=c, payload=f"prof:course:{c}")
                for c in texts.COURSES]
    kb.row(*row_btns)
    return kb


def profile_study_program_select(page: int = 1) -> InlineKeyboardBuilder:
    """Пагинированный список направлений для редактирования профиля (prefix prof:)."""
    items_per_page = 8
    programs = repo.list_study_programs()
    total = len(programs)
    start = (page - 1) * items_per_page
    end = start + items_per_page
    kb = InlineKeyboardBuilder()
    for i, prog in enumerate(programs[start:end], start=start):
        kb.row(CallbackButton(text=prog, payload=f"prof:prog:{i}"))
    nav = []
    if page > 1:
        nav.append(CallbackButton(text="◀ Назад", payload=f"prof:sp:{page - 1}"))
    if end < total:
        nav.append(CallbackButton(text="Далее ▶", payload=f"prof:sp:{page + 1}"))
    if nav:
        kb.row(*nav)
    return kb


def profile_department_select(page: int = 1) -> InlineKeyboardBuilder:
    """Пагинированный список кафедр для редактирования профиля (prefix prof:)."""
    items_per_page = 8
    deps = repo.list_departments()
    total = len(deps)
    start = (page - 1) * items_per_page
    end = start + items_per_page
    kb = InlineKeyboardBuilder()
    for i, dep in enumerate(deps[start:end], start=start):
        kb.row(CallbackButton(text=dep, payload=f"prof:dep:{i}"))
    nav = []
    if page > 1:
        nav.append(CallbackButton(text="◀ Назад", payload=f"prof:dp:{page - 1}"))
    if end < total:
        nav.append(CallbackButton(text="Далее ▶", payload=f"prof:dp:{page + 1}"))
    if nav:
        kb.row(*nav)
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


# ── Просмотр подтверждений участия (админ) ─────────────────────────────────
def event_view_button(event_id: int) -> InlineKeyboardBuilder:
    """Кнопка быстрого перехода к подтверждениям сразу после рассылки."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="📋 Посмотреть подтверждения",
                          payload=f"evtresp:view:{event_id}"))
    return kb


def events_list_menu(events: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    """Список рассылок/созвонов администратора с переходом к подтверждениям."""
    kb = InlineKeyboardBuilder()
    for e in events:
        preview = (e["text"] or "").strip().replace("\n", " ")
        if len(preview) > 40:
            preview = preview[:40] + "…"
        icon = "📞" if e["kind"] == "call" else "📨"
        kb.row(CallbackButton(text=f"{icon} #{e['id']} {preview}",
                              payload=f"evtresp:view:{e['id']}"))
    kb.row(back_button())
    return kb


def event_responses_menu(event_id: int, yes: int, no: int, pending: int) -> InlineKeyboardBuilder:
    """Меню с количеством ответов; каждая кнопка открывает список ФИО."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text=f"✅ Будут ({yes})",
                          payload=f"evtresp:list:{event_id}:yes"))
    kb.row(CallbackButton(text=f"❌ Не будут ({no})",
                          payload=f"evtresp:list:{event_id}:no"))
    kb.row(CallbackButton(text=f"⏳ Без ответа ({pending})",
                          payload=f"evtresp:list:{event_id}:pending"))
    kb.row(CallbackButton(text="⬅️ К списку рассылок", payload="evtresp:menu"))
    return kb


def event_responses_back(event_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="⬅️ Назад", payload=f"evtresp:view:{event_id}"))
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
    kb.row(CallbackButton(text="🔍 Поиск задачи", payload="tadm:tsearch"))
    kb.row(CallbackButton(text="Выгрузить задачи в Excel",
                          payload="tadm:export"))
    kb.row(back_button())
    return kb


def task_admin_list(tasks: Iterable[sqlite3.Row], page: int = 1,
                     search_mode: bool = False) -> InlineKeyboardBuilder:
    items = []
    for t in tasks:
        flag = "🟢" if t["active"] else "🔴"
        items.append((f"{flag} {t['title']}", f"tadm:view:{t['id']}"))
    action_prefix = "tadm:tresults" if search_mode else "tadm:list"
    kb = paginated_list(items, page, action_prefix, items_per_page=10)
    kb.row(CallbackButton(text="🔍 Поиск", payload="tadm:tsearch"))
    kb.row(back_button("tadm:menu"))
    return kb


def task_admin_actions(task_id: int, active: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="✏️ Редактировать", payload=f"tadm:edit:{task_id}"))
    toggle = "Деактивировать" if active else "Активировать"
    kb.row(CallbackButton(text=f"{toggle}",
                          payload=f"tadm:toggle:{task_id}"))
    kb.row(CallbackButton(text="❌ Удалить", payload=f"tadm:del:{task_id}"))
    kb.row(back_button("tadm:list"))
    return kb


def task_edit_fields(task_id: int) -> InlineKeyboardBuilder:
    """Меню выбора поля для редактирования задачи."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Название", payload=f"tadm:edit_field:{task_id}:title"))
    kb.row(CallbackButton(text="Партнёр", payload=f"tadm:edit_field:{task_id}:partner_name"))
    kb.row(CallbackButton(text="Описание", payload=f"tadm:edit_field:{task_id}:description"))
    kb.row(CallbackButton(text="Количество команд", payload=f"tadm:edit_field:{task_id}:max_teams"))
    kb.row(CallbackButton(text="Образовательная программа", payload=f"tadm:edit_field:{task_id}:education_program"))
    kb.row(back_button(f"tadm:view:{task_id}"))
    return kb


def application_view(app_id: int) -> InlineKeyboardBuilder:
    """Кнопка возврата к списку заявок."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="К списку заявок", payload="apps:list"))
    kb.row(back_button())
    return kb


def paginated_list(items: list, page: int, action_prefix: str, items_per_page: int = 10) -> InlineKeyboardBuilder:
    """Строит paginated клавиатуру с кнопками элементов и навигацией.

    items — список кортежей (text, payload) для кнопок.
    action_prefix — префикс payload для навигации, например 'tadm:list'.
    """
    kb = InlineKeyboardBuilder()
    total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page

    for text, payload in items[start:end]:
        kb.row(CallbackButton(text=text, payload=payload))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(CallbackButton(text="◀️ Назад", payload=f"{action_prefix}:page:{page - 1}"))
    nav_buttons.append(CallbackButton(text=f"{page}/{total_pages}", payload=f"{action_prefix}:page:{page}"))
    if page < total_pages:
        nav_buttons.append(CallbackButton(text="Вперёд ▶️", payload=f"{action_prefix}:page:{page + 1}"))
    kb.row(*nav_buttons)
    return kb


def users_paginated_list(users: Iterable[sqlite3.Row], page: int = 1,
                          search_mode: bool = False) -> InlineKeyboardBuilder:
    """Пагинированный список пользователей для админ-панели."""
    items = []
    for u in users:
        fio = f"{u['last_name'] or ''} {u['first_name'] or ''}".strip() or u['display_name'] or f"ID {u['user_id']}"
        role_icon = {"student": "🎓", "teacher": "👨‍🏫", "partner": "🤝", "admin": "👤"}.get(u['role'], "❓")
        status_icon = {"verified": "✅", "pending": "⏳", "rejected": "❌"}.get(u['status'], "")
        items.append((f"{role_icon} {status_icon} {fio[:40]}", f"apanel:user:{u['user_id']}"))
    action_prefix = "apanel:usearch" if search_mode else "apanel:users"
    kb = paginated_list(items, page, action_prefix, items_per_page=10)
    kb.row(CallbackButton(text="🔍 Поиск", payload="apanel:usersearch"))
    kb.row(back_button("apanel:main"))
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
    kb.row(CallbackButton(text="Все преподаватели", payload="call:allteach"))
    kb.row(CallbackButton(text="Все пользователи", payload="call:all"))
    kb.row(back_button())
    return kb


def mailing_recipients_menu() -> InlineKeyboardBuilder:
    """Меню выбора аудитории для рассылки."""
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Конкретная команда", payload="mail:team"))
    kb.row(CallbackButton(text="Все пользователи", payload="mail:all"))
    kb.row(CallbackButton(text="Все студенты", payload="mail:students"))
    kb.row(CallbackButton(text="Все преподаватели", payload="mail:teachers"))
    kb.row(CallbackButton(text="Все партнёры", payload="mail:partners"))
    kb.row(back_button())
    return kb


def teams_pick_list(teams: Iterable[sqlite3.Row], action: str
                    ) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for t in teams:
        kb.row(CallbackButton(text=t["name"], payload=f"{action}:{t['id']}"))
    kb.row(back_button())
    return kb


def team_pick_mail(teams: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    return teams_pick_list(teams, "mail:teampick")


def team_pick_call(teams: Iterable[sqlite3.Row]) -> InlineKeyboardBuilder:
    return teams_pick_list(teams, "call:teampick")


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
