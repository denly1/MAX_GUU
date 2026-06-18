"""Управление контактами администраторов (только для админов)."""

from __future__ import annotations

from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi import F

from .. import keyboards, repo
from ..common_ui import require_role
from ..filters import CbPrefix
from ..instance import bot
from ..states import AdminContactEdit

router = Router(router_id="admin_contacts")


# ── Просмотр контактов администраторов ─────────────────────────────────────
@router.message_callback(CbPrefix("admins"))
async def admins_cb(event: MessageCallback) -> None:
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
            text="⚙️ Управление контактами администраторов:",
            attachments=[keyboards.admin_contacts_manage(contacts).as_markup()],
        )
        return
    
    # Добавить новый контакт
    if sub == "add":
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        await event.edit(
            text="➕ Добавление контакта администратора.\n\nВведите ФИО:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        await event.callback.context.clear()
        await event.callback.context.set_state(AdminContactEdit.fio)
        return
    
    # Редактировать контакт
    if sub == "edit":
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        contact_id = int(parts[2])
        contact = repo.get_admin_contact(contact_id)
        if contact:
            await event.edit(
                text=(f"✏️ Редактирование контакта:\n\n"
                      f"ФИО: {contact['fio']}\n"
                      f"Телефон: {contact['phone']}\n"
                      f"Telegram: {contact['telegram'] or '—'}\n\n"
                      f"Что хотите изменить?"),
                attachments=[keyboards.admin_contact_edit_menu(contact_id).as_markup()],
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
            text="🗑 Контакт удалён.\n\n⚙️ Управление контактами администраторов:",
            attachments=[keyboards.admin_contacts_manage(contacts).as_markup()],
        )
        return
    
    # Показать список контактов (для всех пользователей)
    contacts = repo.list_admin_contacts()
    
    if not contacts:
        text = "📋 Контакты администраторов пока не добавлены."
        kb = keyboards.InlineKeyboardBuilder()
        if require_role(user_id, "admin"):
            kb.row(keyboards.CallbackButton(
                text="⚙️ Управление контактами",
                payload="admins:manage"
            ))
        kb.row(keyboards.back_button())
        await event.edit(text=text, attachments=[kb.as_markup()])
        return
    
    # Отправляем каждый контакт отдельным сообщением с фото
    await event.edit(
        text="📋 Контакты администраторов программы «Обучение служением»:",
        attachments=[],
    )
    
    for contact in contacts:
        text = (
            f"👤 **{contact['fio']}**\n\n"
            f"📞 Телефон: {contact['phone']}\n"
            f"💬 Telegram: {contact['telegram'] or '—'}"
        )
        
        # Если есть фото (токен), отправляем с фото
        if contact.get('photo_token'):
            from maxapi.types.attachments.image import Image
            await bot.send_message(
                user_id=user_id,
                text=text,
                attachments=[Image(file_token=contact['photo_token'])],
            )
        else:
            # Если нет фото, просто текст
            await bot.send_message(user_id=user_id, text=text)
    
    # Кнопки управления (для админов)
    kb = keyboards.InlineKeyboardBuilder()
    if require_role(user_id, "admin"):
        kb.row(keyboards.CallbackButton(
            text="⚙️ Управление контактами",
            payload="admins:manage"
        ))
    kb.row(keyboards.back_button())
    
    await bot.send_message(
        user_id=user_id,
        text="—",
        attachments=[kb.as_markup()],
    )


# ── FSM: Добавление контакта ───────────────────────────────────────────────
@router.message_created(AdminContactEdit.fio, F.message.body.text)
async def contact_fio(event: MessageCreated, context: BaseContext) -> None:
    fio = (event.message.body.text or "").strip()
    if not fio:
        await event.message.answer("ФИО не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(fio=fio)
    await context.set_state(AdminContactEdit.phone)
    await event.message.answer("Введите номер телефона:")


@router.message_created(AdminContactEdit.phone, F.message.body.text)
async def contact_phone(event: MessageCreated, context: BaseContext) -> None:
    phone = (event.message.body.text or "").strip()
    if not phone:
        await event.message.answer("Телефон не может быть пустым. Попробуйте ещё раз:")
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
    await context.update_data(telegram=telegram)
    await context.set_state(AdminContactEdit.photo)
    await event.message.answer(
        "Отправьте фото администратора или напишите «-» чтобы пропустить:"
    )


@router.message_created(AdminContactEdit.photo, F.message.body.text)
async def contact_photo_skip(event: MessageCreated, context: BaseContext) -> None:
    """Пропуск фото."""
    text = (event.message.body.text or "").strip()
    if text == "-":
        data = await context.get_data()
        contact_id = repo.add_admin_contact(
            fio=data['fio'],
            phone=data['phone'],
            telegram=data.get('telegram'),
            photo_token=None
        )
        await context.clear()
        await event.message.answer(
            f"✅ Контакт «{data['fio']}» добавлен!",
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
    contact_id = repo.add_admin_contact(
        fio=data['fio'],
        phone=data['phone'],
        telegram=data.get('telegram'),
        photo_token=photo_token
    )
    await context.clear()
    await event.message.answer(
        f"✅ Контакт «{data['fio']}» добавлен с фото!",
        attachments=[keyboards.main_menu_kb().as_markup()],
    )
