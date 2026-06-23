"""Админ-панель: управление администраторами, переключение ролей, просмотр пользователей."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from .. import keyboards, repo
from ..common_ui import require_role, send_main_menu
from ..filters import CbPrefix
from ..instance import bot
from ..states import AdminManage

router = Router(router_id="admin_panel")


# ── Главная админ-панель ───────────────────────────────────────────────────
@router.message_callback(CbPrefix("apanel"))
async def admin_panel_cb(event: MessageCallback, context: BaseContext) -> None:
    """Главная админ-панель."""
    user_id = event.callback.user.user_id
    
    if not require_role(user_id, "admin"):
        await event.ack(notification="Доступно только администраторам")
        return
    
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""
    
    # Главное меню админ-панели
    if not sub or sub == "main":
        kb = InlineKeyboardBuilder()
        # Управление пользователями
        kb.row(CallbackButton(text="✓ Верификация", payload="ver:menu"))
        kb.row(CallbackButton(text="👤 Управление администраторами", payload="apanel:admins"))
        kb.row(CallbackButton(text="👥 Просмотр пользователей", payload="apanel:users"))
        kb.row(CallbackButton(text="🔄 Переключение роли", payload="apanel:switch"))
        # Управление контентом
        kb.row(CallbackButton(text="📋 Проекты", payload="tadm:menu"))
        kb.row(CallbackButton(text="📝 Заявки", payload="apps:list"))
        kb.row(CallbackButton(text="🎭 Мемы", payload="meme:menu"))
        kb.row(CallbackButton(text="📞 Управление контактами", payload="admins:manage"))
        # Коммуникация
        kb.row(CallbackButton(text="📢 Рассылка", payload="mail:start"))
        kb.row(CallbackButton(text="📞 Созвон", payload="call:start"))
        # Отчёты и статистика
        kb.row(CallbackButton(text="📊 Статистика", payload="stats"))
        kb.row(CallbackButton(text="📥 Экспорт", payload="expch:run"))
        kb.row(keyboards.back_button())
        
        await event.edit(
            text="**Админ-панель**\n\nВыберите действие:",
            attachments=[kb.as_markup()],
        )
        return
    
    # Управление администраторами
    if sub == "admins":
        admins = repo.list_admins()
        
        text = "**Управление администраторами**\n\n"
        text += f"Всего администраторов: {len(admins)}\n\n"
        
        for admin in admins:
            fio = f"{admin['last_name']} {admin['first_name']}" if admin['last_name'] else admin['display_name']
            text += f"• {fio} (ID: {admin['user_id']})\n"
        
        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="➕ Добавить администратора", payload="apanel:add_admin"))
        for admin in admins:
            fio = f"{admin['last_name']} {admin['first_name']}" if admin['last_name'] else admin['display_name']
            kb.row(CallbackButton(
                text=f"❌ Удалить {fio[:30]}",
                payload=f"apanel:remove_admin:{admin['user_id']}"
            ))
        kb.row(CallbackButton(text="◀️ Назад", payload="apanel:main"))
        
        await event.edit(text=text, attachments=[kb.as_markup()])
        return
    
    # Добавить администратора
    if sub == "add_admin":
        await context.clear()
        await context.set_state(AdminManage.user_id)
        await event.edit(
            text=(
                "➕ **Добавление администратора**\n\n"
                "Введите MAX user_id пользователя, которого хотите сделать администратором:"
            ),
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    
    # Удалить администратора
    if sub == "remove_admin":
        target_id = int(parts[2])
        
        # Нельзя удалить себя
        if target_id == user_id:
            await event.ack(notification="Нельзя удалить себя из администраторов")
            return
        
        # Понижаем до обычного пользователя
        target = repo.get_user(target_id)
        if target:
            repo.set_user_role(target_id, "student", status="verified")
            await event.ack(notification="Администратор удалён")
            
            # Уведомляем пользователя
            try:
                await bot.send_message(
                    user_id=target_id,
                    text="Вы больше не являетесь администратором системы."
                )
            except Exception:
                pass
        
        # Обновляем список
        admins = repo.list_admins()
        text = "**Управление администраторами**\n\n"
        text += f"Всего администраторов: {len(admins)}\n\n"
        
        for admin in admins:
            fio = f"{admin['last_name']} {admin['first_name']}" if admin['last_name'] else admin['display_name']
            text += f"• {fio} (ID: {admin['user_id']})\n"
        
        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="➕ Добавить администратора", payload="apanel:add_admin"))
        for admin in admins:
            fio = f"{admin['last_name']} {admin['first_name']}" if admin['last_name'] else admin['display_name']
            kb.row(CallbackButton(
                text=f"❌ Удалить {fio[:30]}",
                payload=f"apanel:remove_admin:{admin['user_id']}"
            ))
        kb.row(CallbackButton(text="◀️ Назад", payload="apanel:main"))
        
        await event.edit(text=text, attachments=[kb.as_markup()])
        return
    
    # Переключение роли
    if sub == "switch":
        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="🎓 Студент", payload="apanel:role:student"))
        kb.row(CallbackButton(text="👨‍🏫 Преподаватель", payload="apanel:role:teacher"))
        kb.row(CallbackButton(text="🤝 Партнер", payload="apanel:role:partner"))
        kb.row(CallbackButton(text="👤 Администратор", payload="apanel:role:admin"))
        kb.row(CallbackButton(text="◀️ Назад", payload="apanel:main"))
        
        current_user = repo.get_user(user_id)
        current_role = current_user['role'] if current_user else 'admin'
        
        role_labels = {
            'student': 'Студент',
            'teacher': 'Преподаватель',
            'partner': 'Партнер',
            'admin': 'Администратор'
        }
        
        await event.edit(
            text=(
                f"**Переключение роли**\n\n"
                f"Текущая роль: {role_labels.get(current_role, current_role)}\n\n"
                f"Выберите роль для просмотра интерфейса:"
            ),
            attachments=[kb.as_markup()],
        )
        return
    
    # Переключить роль
    if sub == "role":
        new_role = parts[2]
        
        # Сохраняем флаг в БД, что пользователь был админом
        repo.set_user_role(user_id, new_role, status="verified")
        repo.set_was_admin(user_id, 1)
        
        await event.ack(notification=f"Роль изменена на {new_role}")
        await send_main_menu(user_id, greeting=f"🔄 Вы переключились на роль: {new_role}\n\nИспользуйте /admin для возврата в админ-панель")
        return
    
    # Просмотр пользователей
    if sub == "users":
        page = 1
        if len(parts) > 3 and parts[2] == "page" and parts[3].isdigit():
            page = int(parts[3])
        users = repo.list_all_users()
        
        text = f"**Все пользователи**\n\nВсего: {len(users)}\n\nНажмите на пользователя, чтобы перейти к профилю."
        
        await event.edit(
            text=text,
            attachments=[keyboards.users_paginated_list(users, page=page).as_markup()],
        )
        return


# ── FSM: Добавление администратора ─────────────────────────────────────────
@router.message_created(AdminManage.user_id, F.message.body.text)
async def add_admin_id(event: MessageCreated, context: BaseContext) -> None:
    text = (event.message.body.text or "").strip()
    
    try:
        target_id = int(text)
    except ValueError:
        await event.message.answer("Неверный формат. Введите числовой user_id:")
        return
    
    target = repo.get_user(target_id)
    
    if not target:
        await event.message.answer(
            f"Пользователь с ID {target_id} не найден в системе.\n\n"
            "Пользователь должен сначала зарегистрироваться в боте."
        )
        return
    
    # Делаем администратором
    repo.set_user_role(target_id, "admin", status="verified")
    await context.clear()
    
    fio = f"{target['last_name']} {target['first_name']}" if target['last_name'] else target['display_name']
    
    await event.message.answer(
        f"Пользователь {fio} (ID: {target_id}) назначен администратором!",
        attachments=[keyboards.main_menu_kb().as_markup()],
    )
    
    # Уведомляем нового админа
    try:
        await bot.send_message(
            user_id=target_id,
            text=(
                "Поздравляем!\n\n"
                "Вы назначены администратором системы «Обучение служением».\n\n"
                "Теперь вам доступна полная админ-панель."
            )
        )
    except Exception:
        pass


# ── Команда для возврата в админ-режим ─────────────────────────────────────
@router.message_created(F.message.body.text == "/admin")
async def admin_command(event: MessageCreated, context: BaseContext) -> None:
    user_id = event.message.sender.user_id if event.message.sender else None
    if not user_id:
        return
    
    # Проверяем, может ли пользователь вернуться в админ-режим:
    # 1. Пользователь в ADMIN_IDS (bootstrap-админ)
    # 2. В БД стоит флаг was_admin (переключился через админ-панель)
    can_return_admin = user_id in config.ADMIN_IDS
    if not can_return_admin:
        user = repo.get_user(user_id)
        can_return_admin = bool(user and user.get("was_admin"))
    
    if can_return_admin:
        repo.set_user_role(user_id, "admin", status="verified")
        await context.clear()
        await event.message.answer("Вы вернулись в режим администратора")
        await send_main_menu(user_id)
    elif require_role(user_id, "admin"):
        # Уже админ
        await send_main_menu(user_id)
    else:
        await event.message.answer("У вас нет прав администратора")
