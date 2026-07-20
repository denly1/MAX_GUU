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
            text="Вы не зарегистрированы в системе.",
            attachments=[keyboards.back_button().as_markup()],
        )
        await event.ack()
        return

    role_labels = {
        'student': 'Студент',
        'teacher': 'Преподаватель',
        'partner': 'Социальный партнёр',
        'admin': 'Администратор',
    }

    status_labels = {
        'pending': 'На верификации',
        'verified': 'Подтверждён',
        'rejected': 'Отклонён',
    }

    text = "Мой профиль\n\n"
    text += f"ID: {user_id}\n"
    text += f"Роль: {role_labels.get(user['role'], user['role'])}\n"
    text += f"Статус: {status_labels.get(user['status'], user['status'])}\n\n"

    fio_parts = [user['last_name'], user['first_name'], user['patronymic']]
    fio = " ".join(p for p in fio_parts if p)
    if fio:
        text += f"ФИО: {fio}\n"
    if user['phone']:
        text += f"Телефон: {user['phone']}\n"

    if user['role'] == 'student':
        text += "\nУчёба:\n"
        if user['institute']:
            text += f"Институт: {user['institute']}\n"
        if user['course']:
            text += f"Курс: {user['course']}\n"
        ud = dict(user)
        if ud.get('education_program'):
            text += f"Направление: {ud['education_program']}\n"
        if user['group_name']:
            text += f"Группа: {user['group_name']}\n"
        teams = repo.get_user_teams(user_id)
        if teams:
            text += f"\nМои команды: {len(teams)}\n"
            for team in teams:
                task = repo.get_task(team['task_id']) if team['task_id'] else None
                role_icon = "Лидер" if team['leader_id'] == user_id else "Участник"
                text += f"{role_icon}: {team['name']}"
                if task:
                    text += f" — {task['title']}"
                text += "\n"
    elif user['role'] == 'teacher':
        if user['department']:
            text += f"\nКафедра: {user['department']}\n"
        ud = dict(user)
        if ud.get('teacher_programs'):
            from .. import texts as _t
            ids = [int(x) for x in ud['teacher_programs'].split(',') if x.strip().isdigit()]
            names = [_t.STUDY_PROGRAMS[i] for i in ids if i < len(_t.STUDY_PROGRAMS)]
            text += f"Программы: {', '.join(names)}\n"
    elif user['role'] == 'partner':
        if user['organization']:
            text += f"\nОрганизация: {user['organization']}\n"
    if user['created_at']:
        text += f"\nРегистрация: {user['created_at'][:10]}\n"

    kb = keyboards.InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Редактировать профиль", payload="profile:edit"))
    kb.row(keyboards.back_button())

    await event.edit(text=text, attachments=[kb.as_markup()])
    await event.ack()


@router.message_callback(CbPrefix("profile:edit"))
async def profile_edit_cb(event: MessageCallback, context: BaseContext) -> None:
    """Меню редактирования профиля или начало редактирования поля."""
    parts = keyboards.parse_cb(event.callback.payload)

    if len(parts) == 2:
        user_id = event.callback.user.user_id
        user = repo.get_user(user_id)
        if not user:
            await event.ack(notification="Пользователь не найден")
            return

        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="Фамилия", payload="profile:edit:last_name"))
        kb.row(CallbackButton(text="Имя", payload="profile:edit:first_name"))
        kb.row(CallbackButton(text="Отчество", payload="profile:edit:patronymic"))
        kb.row(CallbackButton(text="Телефон", payload="profile:edit:phone"))

        if user["role"] == "student":
            kb.row(CallbackButton(text="Институт", payload="profile:edit:institute"))
            kb.row(CallbackButton(text="Курс", payload="profile:edit:course"))
            kb.row(CallbackButton(text="Направление", payload="profile:edit:education_program"))
            kb.row(CallbackButton(text="Группа", payload="profile:edit:group_name"))
        elif user["role"] == "teacher":
            kb.row(CallbackButton(text="Кафедра", payload="profile:edit:department"))
        elif user["role"] == "partner":
            kb.row(CallbackButton(text="Организация", payload="profile:edit:organization"))

        kb.row(CallbackButton(text="Назад", payload="profile"))

        await event.edit(
            text="Выберите, что хотите изменить:",
            attachments=[kb.as_markup()],
        )
        await event.ack()
        return

    if len(parts) == 3:
        field = parts[2]
        allowed_fields = {
            "last_name", "first_name", "patronymic", "phone",
            "institute", "course", "group_name", "department",
            "organization", "education_program",
        }
        if field not in allowed_fields:
            await event.ack(notification="Недопустимое поле")
            return

        await context.clear()
        await context.update_data(edit_field=field)

        if field == "institute":
            await event.edit(
                text="Выберите институт:",
                attachments=[keyboards.profile_institute_select().as_markup()],
            )
            await context.set_state(ProfileEdit.value)
            await event.ack()
            return
        if field == "course":
            await event.edit(
                text="Выберите курс:",
                attachments=[keyboards.profile_course_select().as_markup()],
            )
            await context.set_state(ProfileEdit.value)
            await event.ack()
            return
        if field == "education_program":
            await event.edit(
                text="Выберите направление подготовки:",
                attachments=[keyboards.profile_study_program_select(1).as_markup()],
            )
            await context.set_state(ProfileEdit.value)
            await event.ack()
            return
        if field == "department":
            await event.edit(
                text="Выберите кафедру:",
                attachments=[keyboards.profile_department_select(1).as_markup()],
            )
            await context.set_state(ProfileEdit.value)
            await event.ack()
            return

        field_names = {
            "last_name": "фамилию",
            "first_name": "имя",
            "patronymic": "отчество",
            "phone": "телефон",
            "group_name": "группу",
            "organization": "организацию",
        }
        hints = {
            "phone": "В формате 8 ххх-ххх хх хх",
            "group_name": "Цифра от 1 до 10",
        }
        hint = hints.get(field, "")
        fname = field_names.get(field, field)
        await context.set_state(ProfileEdit.value)
        await event.edit(
            text=(f"Введите новое значение для {fname}:\n{hint}"
                  if hint else f"Введите новое значение для {fname}:"),
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        await event.ack()
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

    if field == "phone":
        ok, value = validators.validate_phone(raw_value)
        if not ok:
            await event.message.answer(validators.PHONE_ERROR)
            return
    elif field == "group_name":
        if not raw_value.isdigit() or not (1 <= int(raw_value) <= 10):
            await event.message.answer("Номер группы — цифра от 1 до 10. Попробуйте ещё раз:")
            return
        value = raw_value
    elif field in ("last_name", "first_name", "patronymic"):
        ok, value = validators.validate_name(raw_value)
        if not ok:
            await event.message.answer(validators.name_error(field_names.get(field, field)))
            return
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
        "education_program": "Направление подготовки",
    }
    label = field_labels.get(field, field)
    await event.message.answer(
        f"{label} обновлено!\n\nНовое значение: {value}",
        attachments=[InlineKeyboardBuilder().row(
            CallbackButton(text="Профиль", payload="profile")).as_markup()],
    )


@router.message_callback(ProfileEdit.value, CbPrefix("prof"))
async def profile_edit_button_cb(event: MessageCallback, context: BaseContext) -> None:
    """Обрабатывает кнопочный выбор для полей institute/course/education_program/department."""
    data = await context.get_data()
    field = data.get("edit_field")
    if not field:
        await event.ack(notification="Сессия устарела")
        return

    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""
    user_id = event.callback.user.user_id

    if sub == "inst" and len(parts) > 2 and field == "institute":
        value = parts[2]
        repo.update_user_field(user_id, "institute", value)
        await context.clear()
        await event.edit(
            text=f"Институт обновлён: {value}",
            attachments=[InlineKeyboardBuilder().row(
                CallbackButton(text="Профиль", payload="profile")).as_markup()],
        )
        return

    if sub == "course" and len(parts) > 2 and field == "course":
        value = parts[2]
        repo.update_user_field(user_id, "course", value)
        await context.clear()
        await event.edit(
            text=f"Курс обновлён: {value}",
            attachments=[InlineKeyboardBuilder().row(
                CallbackButton(text="Профиль", payload="profile")).as_markup()],
        )
        return

    if sub == "prog" and len(parts) > 2 and field == "education_program":
        from .. import texts as _t
        idx = int(parts[2])
        value = _t.STUDY_PROGRAMS[idx]
        repo.update_user_field(user_id, "education_program", value)
        await context.clear()
        await event.edit(
            text=f"Направление обновлено: {value}",
            attachments=[InlineKeyboardBuilder().row(
                CallbackButton(text="Профиль", payload="profile")).as_markup()],
        )
        return

    if sub == "sp" and len(parts) > 2 and parts[2].isdigit() and field == "education_program":
        await event.edit(
            text="Выберите направление подготовки:",
            attachments=[keyboards.profile_study_program_select(int(parts[2])).as_markup()],
        )
        return

    if sub == "dep" and len(parts) > 2 and field == "department":
        from .. import texts as _t
        idx = int(parts[2])
        value = _t.DEPARTMENTS[idx]
        repo.update_user_field(user_id, "department", value)
        await context.clear()
        await event.edit(
            text=f"Кафедра обновлена: {value}",
            attachments=[InlineKeyboardBuilder().row(
                CallbackButton(text="Профиль", payload="profile")).as_markup()],
        )
        return

    if sub == "dp" and len(parts) > 2 and parts[2].isdigit() and field == "department":
        await event.edit(
            text="Выберите кафедру:",
            attachments=[keyboards.profile_department_select(int(parts[2])).as_markup()],
        )
        return

    await event.ack()
