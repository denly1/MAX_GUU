"""Управление задачами администратором (раздел 2.11)."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, repo, reports, texts
from ..common_ui import require_role
from ..filters import CbPrefix
from ..instance import bot
from ..states import TaskAdmin

router = Router(router_id="task_admin")


def _task_text(task) -> str:
    prog = f"\nОбразовательная программа: {task['education_program']}" if task["education_program"] else ""
    status = "активна" if task["active"] else "неактивна"
    taken = repo.task_taken_count(task["id"])
    return (
        f"Задача #{task['number'] or task['id']}: {task['title']}\n\n"
        f"Партнёр: {task['partner_name']}\n"
        f"Описание: {task['description']}\n"
        f"Макс. команд: {task['max_teams']} (занято: {taken}){prog}\n"
        f"Статус: {status}"
    )


@router.message_callback(CbPrefix("tadm"))
async def tadm_cb(event: MessageCallback, context: BaseContext) -> None:
    user_id = event.callback.user.user_id
    if not require_role(user_id, "admin"):
        await event.ack(notification="Недостаточно прав")
        return

    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if sub == "menu":
        await event.edit(
            text="Управление задачами\n\nВыберите действие:",
            attachments=[keyboards.task_admin_menu().as_markup()],
        )
        return

    if sub == "list":
        page = 1
        if len(parts) >= 4 and parts[2] == "page" and parts[3].isdigit():
            page = int(parts[3])
        tasks = repo.list_tasks()
        await event.edit(
            text=f"Список задач ({len(tasks)} всего):",
            attachments=[keyboards.task_admin_list(tasks, page).as_markup()],
        )
        return

    if sub == "add":
        await context.clear()
        await context.set_state(TaskAdmin.title)
        await event.edit(
            text="Добавление задачи.\n\nВведите краткое название проекта:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "prog":
        arg = parts[2] if len(parts) > 2 else ""
        if arg == "none":
            await context.update_data(education_program=None)
        elif arg.isdigit():
            idx = int(arg)
            if idx < len(texts.STUDY_PROGRAMS):
                await context.update_data(education_program=texts.STUDY_PROGRAMS[idx])
        data = await context.get_data()
        task_id = repo.add_task(
            number=None,
            title=data.get("title", ""),
            partner_name=data.get("partner", ""),
            description=data.get("description", ""),
            max_teams=data.get("max_teams", 1),
            education_program=data.get("education_program"),
        )
        await context.clear()
        task = repo.get_task(task_id)
        await event.edit(
            text=f"Задача добавлена!\n\n{_task_text(task)}",
            attachments=[keyboards.task_admin_menu().as_markup()],
        )
        return

    if sub == "progp":
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        await event.edit(
            text="Выберите образовательную программу:",
            attachments=[keyboards.task_program_select(page).as_markup()],
        )
        return

    if sub == "view":
        task_id = int(parts[2])
        task = repo.get_task(task_id)
        if not task:
            await event.ack(notification="Задача не найдена")
            return
        await event.edit(
            text=_task_text(task),
            attachments=[keyboards.task_admin_actions(task_id, task["active"]).as_markup()],
        )
        return

    if sub == "toggle":
        task_id = int(parts[2])
        task = repo.get_task(task_id)
        if not task:
            await event.ack(notification="Задача не найдена")
            return
        new_active = 0 if task["active"] else 1
        repo.update_task(task_id, active=new_active)
        task = repo.get_task(task_id)
        await event.edit(
            text=_task_text(task),
            attachments=[keyboards.task_admin_actions(task_id, task["active"]).as_markup()],
        )
        return

    if sub == "del":
        task_id = int(parts[2])
        repo.delete_task(task_id)
        tasks = repo.list_tasks()
        await event.edit(
            text=f"Задача удалена.\n\nСписок задач ({len(tasks)} всего):",
            attachments=[keyboards.task_admin_list(tasks, 1).as_markup()],
        )
        return

    if sub == "edit":
        task_id = int(parts[2])
        task = repo.get_task(task_id)
        if not task:
            await event.ack(notification="Задача не найдена")
            return
        await event.edit(
            text=f"Редактирование задачи:\n{task['title']}\n\nВыберите поле:",
            attachments=[keyboards.task_edit_fields(task_id).as_markup()],
        )
        return

    if sub == "edit_field":
        if len(parts) < 4:
            return
        task_id = int(parts[2])
        field = parts[3]
        await context.clear()
        await context.update_data(edit_task_id=task_id, edit_field=field)
        if field == "education_program":
            await context.set_state(TaskAdmin.edit_value)
            await event.edit(
                text="Выберите новую образовательную программу:",
                attachments=[keyboards.task_program_select(1).as_markup()],
            )
            return
        field_labels = {
            "title": "краткое название",
            "partner_name": "название партнёра",
            "description": "описание",
            "max_teams": "максимальное количество команд",
        }
        await context.set_state(TaskAdmin.edit_value)
        await event.edit(
            text=f"Введите новое значение для поля \u00ab{field_labels.get(field, field)}\u00bb:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "edit_prog":
        if len(parts) < 4:
            return
        task_id = int(parts[2])
        arg = parts[3]
        value = None if arg == "none" else (
            texts.STUDY_PROGRAMS[int(arg)] if arg.isdigit() and int(arg) < len(texts.STUDY_PROGRAMS) else None
        )
        repo.update_task(task_id, education_program=value)
        task = repo.get_task(task_id)
        await context.clear()
        await event.edit(
            text=f"Программа обновлена.\n\n{_task_text(task)}",
            attachments=[keyboards.task_admin_actions(task_id, task["active"]).as_markup()],
        )
        return

    if sub == "export":
        await event.ack(notification="Готовлю файл\u2026")
        try:
            from maxapi.types.input_media import InputMedia
            path = reports.export_tasks()
            await bot.send_message(
                user_id=user_id,
                text="Выгрузка задач:",
                attachments=[InputMedia(path=str(path))],
            )
        except Exception as e:
            await bot.send_message(user_id=user_id, text=f"Ошибка при экспорте: {e}")
        return

    if sub == "expch" or sub == "export_choices":
        await event.ack(notification="Готовлю файл\u2026")
        try:
            from maxapi.types.input_media import InputMedia
            path = reports.export_task_choices()
            await bot.send_message(
                user_id=user_id,
                text="Выгрузка выбора проектов:",
                attachments=[InputMedia(path=str(path))],
            )
        except Exception as e:
            await bot.send_message(user_id=user_id, text=f"Ошибка при экспорте: {e}")
        return


@router.message_created(TaskAdmin.title, F.message.body.text)
async def ta_title(event: MessageCreated, context: BaseContext) -> None:
    title = (event.message.body.text or "").strip()
    if not title:
        await event.message.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(title=title)
    await context.set_state(TaskAdmin.partner)
    await event.message.answer("Введите название социального партнёра:")


@router.message_created(TaskAdmin.partner, F.message.body.text)
async def ta_partner(event: MessageCreated, context: BaseContext) -> None:
    partner = (event.message.body.text or "").strip()
    if not partner:
        await event.message.answer("Название партнёра не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(partner=partner)
    await context.set_state(TaskAdmin.description)
    await event.message.answer("Введите описание задачи:")


@router.message_created(TaskAdmin.description, F.message.body.text)
async def ta_description(event: MessageCreated, context: BaseContext) -> None:
    desc = (event.message.body.text or "").strip()
    if not desc:
        await event.message.answer("Описание не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(description=desc)
    await context.set_state(TaskAdmin.max_teams)
    await event.message.answer("Введите максимальное количество команд (число):")


@router.message_created(TaskAdmin.max_teams, F.message.body.text)
async def ta_max_teams(event: MessageCreated, context: BaseContext) -> None:
    raw = (event.message.body.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await event.message.answer("Введите целое число больше 0:")
        return
    await context.update_data(max_teams=int(raw))
    await context.set_state(TaskAdmin.education_program)
    await event.message.answer(
        "Выберите образовательную программу (или пропустите):",
        attachments=[keyboards.task_program_select(1).as_markup()],
    )


@router.message_created(TaskAdmin.edit_value, F.message.body.text)
async def ta_edit_value(event: MessageCreated, context: BaseContext) -> None:
    raw = (event.message.body.text or "").strip()
    data = await context.get_data()
    task_id = data.get("edit_task_id")
    field = data.get("edit_field")
    if not task_id or not field:
        await context.clear()
        return
    if field == "max_teams":
        if not raw.isdigit() or int(raw) < 1:
            await event.message.answer("Введите целое число больше 0:")
            return
        value = int(raw)
    else:
        if not raw:
            await event.message.answer("Значение не может быть пустым. Попробуйте ещё раз:")
            return
        value = raw
    repo.update_task(task_id, **{field: value})
    task = repo.get_task(task_id)
    await context.clear()
    await event.message.answer(
        f"Поле обновлено.\n\n{_task_text(task)}",
        attachments=[keyboards.task_admin_actions(task_id, task["active"]).as_markup()],
    )
