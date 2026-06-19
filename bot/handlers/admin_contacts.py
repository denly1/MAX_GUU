"""Управление контактами администраторов (только для админов)."""

from __future__ import annotations

from pathlib import Path

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types import InputMedia
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from .. import keyboards, repo, validators
from ..common_ui import require_role
from ..filters import CbPrefix
from ..instance import bot
from ..states import AdminContactEdit

router = Router(router_id="admin_contacts")


# ── Просмотр контактов администраторов ─────────────────────────────────────
@router.message_callback(CbPrefix("admins"))
async def admins_cb(event: MessageCallback, context: BaseContext) -> None:
    """Показывает список контактов администраторов с фото."""
    user_id = event.callback.user.user_id
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""
    
    # Управление контактами (только для админов)
    if sub == "manage":
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        contacts = repo.list_admin_contacts()
        await event.edit(
            text="Управление контактами администраторов:",
            attachments=[keyboards.admin_contacts_manage(contacts).as_markup()],
        )
        return
    
    # Добавить новый контакт
    if sub == "add":
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        await event.edit(
            text="Добавление контакта администратора.\n\nВведите ФИО:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        await context.clear()
        await context.set_state(AdminContactEdit.fio)
        return
    
    # Редактировать контакт
    if sub == "edit":
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        contact_id = int(parts[2])
        contact = repo.get_admin_contact(contact_id)
        if contact:
            kb = InlineKeyboardBuilder()
            kb.row(CallbackButton(text="Изменить ФИО", payload=f"admins:edit_fio:{contact_id}"))
            kb.row(CallbackButton(text="Изменить телефон", payload=f"admins:edit_phone:{contact_id}"))
            kb.row(CallbackButton(text="Изменить Telegram", payload=f"admins:edit_tg:{contact_id}"))
            kb.row(CallbackButton(text="Изменить фото", payload=f"admins:edit_photo:{contact_id}"))
            kb.row(CallbackButton(text="Удалить контакт", payload=f"admins:delete:{contact_id}"))
            kb.row(CallbackButton(text="Назад", payload="admins:manage"))
            
            await event.edit(
                text=(f"**Редактирование контакта**\n\n"
                      f"**ФИО:** {contact['fio']}\n"
                      f"**Телефон:** {contact['phone']}\n"
                      f"**Telegram:** {contact['telegram'] or '—'}\n"
                      f"**Фото:** {'Есть' if (contact['photo_token'] or contact['photo_url']) else 'Нет'}\n\n"
                      f"Выберите, что хотите изменить:"),
                attachments=[kb.as_markup()],
            )
        return
    
    # Редактировать ФИО
    if sub == "edit_fio":
        contact_id = int(parts[2])
        await context.clear()
        await context.update_data(edit_contact_id=contact_id, edit_field="fio")
        await context.set_state(AdminContactEdit.fio)
        await event.edit(
            text="Введите новое ФИО:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    
    # Редактировать телефон
    if sub == "edit_phone":
        contact_id = int(parts[2])
        await context.clear()
        await context.update_data(edit_contact_id=contact_id, edit_field="phone")
        await context.set_state(AdminContactEdit.phone)
        await event.edit(
            text="Введите новый телефон:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    
    # Редактировать Telegram
    if sub == "edit_tg":
        contact_id = int(parts[2])
        await context.clear()
        await context.update_data(edit_contact_id=contact_id, edit_field="telegram")
        await context.set_state(AdminContactEdit.telegram)
        await event.edit(
            text="Введите новый Telegram (или - для удаления):",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    
    # Редактировать фото
    if sub == "edit_photo":
        contact_id = int(parts[2])
        await context.clear()
        await context.update_data(edit_contact_id=contact_id, edit_field="photo")
        await context.set_state(AdminContactEdit.photo)
        await event.edit(
            text="Отправьте новое фото (или - для удаления):",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    
    # Удалить контакт
    if sub == "delete":
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        contact_id = int(parts[2])
        repo.delete_admin_contact(contact_id)
        contacts = repo.list_admin_contacts()
        await event.edit(
            text="Контакт удален.\n\nУправление контактами администраторов:",
            attachments=[keyboards.admin_contacts_manage(contacts).as_markup()],
        )
        return
    
    # Показать конкретный контакт
    if sub == "view":
        contact_id = int(parts[2])
        contact = repo.get_admin_contact(contact_id)
        if not contact:
            await event.ack(notification="Контакт не найден")
            return
        
        text = (
            f"**{contact['fio']}**\n\n"
            f"Телефон: {contact['phone']}\n"
            f"Telegram: {contact['telegram'] or '—'}"
        )
        
        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="К списку контактов", payload="admins"))
        kb.row(keyboards.back_button())
        
        # Если есть фото (токен), отправляем с фото
        if contact['photo_token']:
            from maxapi.types.attachments.image import Image
            await event.edit(
                text=text,
                attachments=[Image(file_token=contact['photo_token']), kb.as_markup()],
            )
        elif contact['photo_url'] and Path(contact['photo_url']).exists():
            # Фото из файла (загружено через миграцию или админку)
            try:
                media = InputMedia(path=contact['photo_url'])
                await event.edit(
                    text=text,
                    attachments=[media, kb.as_markup()],
                )
            except Exception as e:
                await event.edit(text=f"{text}\n\nВнимание: не удалось загрузить фото: {e}", attachments=[kb.as_markup()])
        else:
            await event.edit(text=text, attachments=[kb.as_markup()])
        return
    
    # Показать список контактов (для всех пользователей)
    contacts = repo.list_admin_contacts()
    
    if not contacts:
        text = "Контакты администраторов пока не добавлены."
        kb = InlineKeyboardBuilder()
        if require_role(user_id, "admin"):
            kb.row(CallbackButton(
                text="Управление контактами",
                payload="admins:manage"
            ))
        kb.row(keyboards.back_button())
        await event.edit(text=text, attachments=[kb.as_markup()])
        return
    
    # Показываем список контактов с кнопками
    text = "**Контакты администраторов программы «Обучение служением»**\n\n"
    text += "Выберите контакт для просмотра:\n"
    
    kb = InlineKeyboardBuilder()
    for contact in contacts:
        kb.row(CallbackButton(
            text=f"{contact['fio']}",
            payload=f"admins:view:{contact['id']}"
        ))
    
    if require_role(user_id, "admin"):
        kb.row(CallbackButton(
            text="Управление контактами",
            payload="admins:manage"
        ))
    kb.row(keyboards.back_button())
    
    await event.edit(text=text, attachments=[kb.as_markup()])


# ── FSM: Добавление/редактирование контакта ───────────────────────────────
@router.message_created(AdminContactEdit.fio, F.message.body.text)
async def contact_fio(event: MessageCreated, context: BaseContext) -> None:
    fio = (event.message.body.text or "").strip()
    if not fio:
        await event.message.answer("ФИО не может быть пустым. Попробуйте ещё раз:")
        return
    
    data = await context.get_data()
    edit_contact_id = data.get('edit_contact_id')
    
    # Если редактируем существующий контакт
    if edit_contact_id:
        repo.update_admin_contact(edit_contact_id, fio=fio)
        await context.clear()
        await event.message.answer(
            f"ФИО обновлено!",
            attachments=[keyboards.main_menu_kb().as_markup()],
        )
        return
    
    # Иначе добавляем новый
    await context.update_data(fio=fio)
    await context.set_state(AdminContactEdit.phone)
    await event.message.answer("Введите номер телефона:")


@router.message_created(AdminContactEdit.phone, F.message.body.text)
async def contact_phone(event: MessageCreated, context: BaseContext) -> None:
    raw_phone = (event.message.body.text or "").strip()
    if not raw_phone:
        await event.message.answer("Телефон не может быть пустым. Попробуйте ещё раз:")
        return
    
    ok, phone = validators.validate_phone(raw_phone)
    if not ok:
        await event.message.answer(validators.PHONE_ERROR)
        return
    
    data = await context.get_data()
    edit_contact_id = data.get('edit_contact_id')
    
    # Если редактируем существующий контакт
    if edit_contact_id:
        repo.update_admin_contact(edit_contact_id, phone=phone)
        await context.clear()
        await event.message.answer(
            f"Телефон обновлен!",
            attachments=[keyboards.main_menu_kb().as_markup()],
        )
        return
    
    await context.update_data(phone=phone)
    await context.set_state(AdminContactEdit.telegram)
    await event.message.answer(
        "Введите Telegram (например: @username) или «-» если нет:"
    )


@router.message_created(AdminContactEdit.telegram, F.message.body.text)
async def contact_telegram(event: MessageCreated, context: BaseContext) -> None:
    telegram = (event.message.body.text or "").strip()
    if telegram == "-":
        telegram = None
    
    data = await context.get_data()
    edit_contact_id = data.get('edit_contact_id')
    
    # Если редактируем существующий контакт
    if edit_contact_id:
        repo.update_admin_contact(edit_contact_id, telegram=telegram)
        await context.clear()
        await event.message.answer(
            f"Telegram обновлен!",
            attachments=[keyboards.main_menu_kb().as_markup()],
        )
        return
    
    await context.update_data(telegram=telegram)
    await context.set_state(AdminContactEdit.photo)
    await event.message.answer(
        "Отправьте фото администратора или напишите «-» чтобы пропустить:"
    )


@router.message_created(AdminContactEdit.photo, F.message.body.text)
async def contact_photo_skip(event: MessageCreated, context: BaseContext) -> None:
    """Пропуск или удаление фото."""
    text = (event.message.body.text or "").strip()
    if text == "-":
        data = await context.get_data()
        edit_contact_id = data.get('edit_contact_id')
        
        # Если редактируем существующий контакт
        if edit_contact_id:
            repo.update_admin_contact(edit_contact_id, photo_token=None)
            await context.clear()
            await event.message.answer(
                f"Фото удалено!",
                attachments=[keyboards.main_menu_kb().as_markup()],
            )
            return
        
        # Иначе добавляем новый контакт без фото
        contact_id = repo.add_admin_contact(
            fio=data['fio'],
            phone=data['phone'],
            telegram=data.get('telegram'),
            photo_token=None
        )
        await context.clear()
        await event.message.answer(
            f"Контакт «{data['fio']}» добавлен!",
            attachments=[keyboards.main_menu_kb().as_markup()],
        )
    else:
        await event.message.answer(
            "Пожалуйста, отправьте фото или напишите «-» чтобы пропустить."
        )


@router.message_created(AdminContactEdit.photo, F.message.attachments)
async def contact_photo_upload(event: MessageCreated, context: BaseContext) -> None:
    """Загрузка фото."""
    # Ищем изображение в attachments
    photo_token = None
    for att in event.message.attachments or []:
        if hasattr(att, 'file_token'):
            photo_token = att.file_token
            break
    
    if not photo_token:
        await event.message.answer(
            "Не удалось получить фото. Попробуйте ещё раз или напишите «-» чтобы пропустить."
        )
        return
    
    data = await context.get_data()
    edit_contact_id = data.get('edit_contact_id')
    
    # Если редактируем существующий контакт
    if edit_contact_id:
        repo.update_admin_contact(edit_contact_id, photo_token=photo_token)
        await context.clear()
        await event.message.answer(
            f"Фото обновлено!",
            attachments=[keyboards.main_menu_kb().as_markup()],
        )
        return
    
    # Иначе добавляем новый контакт с фото
    contact_id = repo.add_admin_contact(
        fio=data['fio'],
        phone=data['phone'],
        telegram=data.get('telegram'),
        photo_token=photo_token
    )
    await context.clear()
    await event.message.answer(
        f"Контакт «{data['fio']}» добавлен с фото!",
        attachments=[keyboards.main_menu_kb().as_markup()],
    )
