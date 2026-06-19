"""Профиль пользователя."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from .. import keyboards, repo, validators
from ..common_ui import send_main_menu
from ..filters import CbPrefix
from ..states import ProfileEdit

router = Router(router_id="profile")


@router.message_callback(CbPrefix("profile"))
async def profile_cb(event: MessageCallback) -> None:
    """Показывает профиль пользователя."""
    user_id = event.callback.user.user_id
    user = repo.get_user(user_id)
    
    if not user or not user["role"]:
        await event.edit(
            text="❌ Вы не зарегистрированы в системе.",
            attachments=[keyboards.back_button().as_markup()],
        )
        return
    
    # Формируем текст профиля
    role_labels = {
        'student': '🎓 Студент',
        'teacher': '👨‍🏫 Преподаватель',
        'partner': '🤝 Социальный партнёр',
        'admin': '⚙️ Администратор'
    }
    
    status_labels = {
        'pending': '⏳ На верификации',
        'verified': '✅ Подтверждён',
        'rejected': '❌ Отклонён'
    }
    
    text = f"👤 **Мой профиль**\n\n"
    text += f"**ID:** {user_id}\n"
    text += f"**Роль:** {role_labels.get(user['role'], user['role'])}\n"
    text += f"**Статус:** {status_labels.get(user['status'], user['status'])}\n\n"
    
    # ФИО
    fio_parts = [user['last_name'], user['first_name'], user['patronymic']]
    fio = " ".join(p for p in fio_parts if p)
    if fio:
        text += f"**ФИО:** {fio}\n"
    
    # Телефон
    if user['phone']:
        text += f"**Телефон:** {user['phone']}\n"
    
    # Специфичные поля для студента
    if user['role'] == 'student':
        text += f"\n📚 **Учёба:**\n"
        if user['institute']:
            text += f"Институт: {user['institute']}\n"
        if user['course']:
            text += f"Курс: {user['course']}\n"
        if user['group_name']:
            text += f"Группа: {user['group_name']}\n"
        
        # Статистика студента
        teams = repo.get_user_teams(user_id)
        if teams:
            text += f"\n👥 **Мои команды:** {len(teams)}\n"
            for team in teams:
                task = repo.get_task(team['task_id']) if team['task_id'] else None
                role_icon = "👑" if team['leader_id'] == user_id else "👤"
                text += f"{role_icon} {team['name']}"
                if task:
                    text += f" — {task['title']}"
                text += "\n"
    
    # Специфичные поля для преподавателя
    elif user['role'] == 'teacher':
        if user['department']:
            text += f"\n🏛 **Кафедра:** {user['department']}\n"
    
    # Специфичные поля для партнёра
    elif user['role'] == 'partner':
        if user['organization']:
            text += f"\n🏢 **Организация:** {user['organization']}\n"
    
    # Дата регистрации
    if user['created_at']:
        text += f"\n📅 **Регистрация:** {user['created_at'][:10]}\n"
    
    kb = keyboards.InlineKeyboardBuilder()
    kb.row(CallbackButton(text="✏️ Редактировать профиль", payload="profile:edit"))
    kb.row(keyboards.back_button())
    
    await event.edit(text=text, attachments=[kb.as_markup()])


@router.message_callback(CbPrefix("profile:edit"))
async def profile_edit_cb(event: MessageCallback, context: BaseContext) -> None:
    """Меню редактирования профиля или начало редактирования поля."""
    parts = keyboards.parse_cb(event.callback.payload)
    
    # Если 2 части — показываем меню выбора поля
    if len(parts) == 2:
        user_id = event.callback.user.user_id
        user = repo.get_user(user_id)
        if not user:
            await event.ack(notification="Пользователь не найден")
            return
        
        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="📝 Фамилия", payload="profile:edit:last_name"))
        kb.row(CallbackButton(text="📝 Имя", payload="profile:edit:first_name"))
        kb.row(CallbackButton(text="📝 Отчество", payload="profile:edit:patronymic"))
        kb.row(CallbackButton(text="📞 Телефон", payload="profile:edit:phone"))
        
        if user["role"] == "student":
            kb.row(CallbackButton(text="🏫 Институт", payload="profile:edit:institute"))
            kb.row(CallbackButton(text="📚 Курс", payload="profile:edit:course"))
            kb.row(CallbackButton(text="👥 Группа", payload="profile:edit:group_name"))
        elif user["role"] == "teacher":
            kb.row(CallbackButton(text="🏛 Кафедра", payload="profile:edit:department"))
        elif user["role"] == "partner":
            kb.row(CallbackButton(text="🏢 Организация", payload="profile:edit:organization"))
        
        kb.row(CallbackButton(text="🔙 Назад", payload="profile"))
        
        await event.edit(
            text="✏️ Выберите, что хотите изменить:",
            attachments=[kb.as_markup()],
        )
        return
    
    # Если 3 части — начинаем редактировать конкретное поле
    if len(parts) == 3:
        field = parts[2]
        allowed_fields = {
            "last_name", "first_name", "patronymic", "phone",
            "institute", "course", "group_name", "department", "organization"
        }
        if field not in allowed_fields:
            await event.ack(notification="Недопустимое поле")
            return
        
        field_names = {
            "last_name": "фамилию",
            "first_name": "имя",
            "patronymic": "отчество",
            "phone": "телефон",
            "institute": "институт",
            "course": "курс",
            "group_name": "группу",
            "department": "кафедру",
            "organization": "организацию",
        }
        
        await context.clear()
        await context.update_data(edit_field=field)
        await context.set_state(ProfileEdit.value)
        
        hints = {
            "phone": "В формате 8 ххх-ххх хх хх",
            "course": "1, 2, 3 или 4",
            "institute": "ИОМ, ИМ, ИГУиП, ИЭФ или ИУПСиБК",
        }
        hint = hints.get(field, "")
        
        await event.edit(
            text=f"Введите новое значение для {field_names[field]}{':' if hint else ''}\n{hint}",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return


@router.message_created(ProfileEdit.value, F.message.body.text)
async def profile_edit_value(event: MessageCreated, context: BaseContext) -> None:
    """Сохраняет новое значение поля профиля."""
    data = await context.get_data()
    field = data.get("edit_field")
    if not field:
        await context.clear()
        return
    
    _, user_id = event.get_ids()
    raw_value = (event.message.body.text or "").strip()
    
    if field == "phone":
        ok, value = validators.validate_phone(raw_value)
        if not ok:
            await event.message.answer(validators.PHONE_ERROR)
            return
    elif field == "course":
        if raw_value not in ["1", "2", "3", "4"]:
            await event.message.answer("Курс должен быть от 1 до 4. Попробуйте ещё раз:")
            return
        value = raw_value
    elif field == "institute":
        if raw_value not in ["ИОМ", "ИМ", "ИГУиП", "ИЭФ", "ИУПСиБК"]:
            await event.message.answer("Выберите институт из списка: ИОМ, ИМ, ИГУиП, ИЭФ, ИУПСиБК")
            return
        value = raw_value
    else:
        value = raw_value
    
    if not value:
        await event.message.answer("Значение не может быть пустым. Попробуйте ещё раз:")
        return
    
    repo.update_user_field(user_id, field, value)
    await context.clear()
    
    field_labels = {
        "last_name": "Фамилия",
        "first_name": "Имя",
        "patronymic": "Отчество",
        "phone": "Телефон",
        "institute": "Институт",
        "course": "Курс",
        "group_name": "Группа",
        "department": "Кафедра",
        "organization": "Организация",
    }
    
    await event.message.answer(
        f"✅ {field_labels[field]} обновлено!\n\nНовое значение: {value}",
        attachments=[InlineKeyboardBuilder().row(CallbackButton(text="👤 Профиль", payload="profile")).as_markup()],
    )
