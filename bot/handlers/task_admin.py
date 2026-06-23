"""Администрирование задач: формирование/редактирование списка и выгрузки."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.input_media import InputMedia
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, reports, repo, validators
from ..common_ui import notify_students
from ..filters import CbPrefix
from ..instance import bot
from ..states import TaskAdmin

router = Router(router_id="task_admin")


def _guard(user_id: int) -> bool:
    return repo.is_admin(user_id)


async def _send_file(user_id: int, path, caption: str) -> None:
    await bot.send_message(
        user_id=user_id, text=caption,
        attachments=[InputMedia(path=str(path))],
    )


@router.message_callback(CbPrefix("tadm"))
async def tadm_cb(event: MessageCallback, context: BaseContext) -> None:
    user_id = event.callback.user.user_id
    if not _guard(user_id):
        await event.ack(notification="Недостаточно прав")
        return
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if sub == "menu":
        await event.edit(
            text="🗂 Управление задачами:",
            attachments=[keyboards.task_admin_menu().as_markup()],
        )
        return

    if sub == "add":
        await context.clear()
        await context.set_state(TaskAdmin.title)
        await event.edit(
            text="Добавление задачи.\nВведите краткое название проекта:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "list":
        tasks = repo.list_tasks()
        if not tasks:
            await event.edit(
                text="Список задач пуст.",
                attachments=[keyboards.task_admin_menu().as_markup()],
            )
        else:
            await event.edit(
                text="Список задач (🟢 активна / 🔴 скрыта):",
                attachments=[keyboards.task_admin_list(tasks).as_markup()],
            )
        return

    if sub == "view":
        task = repo.get_task(int(parts[2]))
        if task:
            taken = repo.task_taken_count(task["id"])
            await event.edit(
                text=(f"📌 {task['title']}\nПартнёр: {task['partner_name']}\n\n"
                      f"{task['description']}\n\nКоманд макс.: {task['max_teams']} "
                      f"(занято: {taken})\nСтатус: "
                      f"{'🟢 активна' if task['active'] else '🔴 скрыта'}"),
                attachments=[keyboards.task_admin_actions(
                    task["id"], task["active"]).as_markup()],
            )
        return

    if sub == "toggle":
        task = repo.get_task(int(parts[2]))
        if task:
            repo.update_task(task["id"], active=0 if task["active"] else 1)
        await event.edit(
            text="Статус задачи изменён.",
            attachments=[keyboards.task_admin_list(repo.list_tasks()).as_markup()],
        )
        return

    if sub == "del":
        repo.delete_task(int(parts[2]))
        await event.edit(
            text="Задача удалена.",
            attachments=[keyboards.task_admin_list(repo.list_tasks()).as_markup()],
        )
        return

    if sub == "export":
        await event.ack(notification="Готовлю файл…")
        path = reports.export_tasks()
        await _send_file(user_id, path, "📊 Выгрузка списка задач:")
        return

    if sub == "edit":
        task_id = int(parts[2])
        task = repo.get_task(task_id)
        if not task:
            await event.ack(notification="Задача не найдена")
            return
        await event.edit(
            text=f"Редактирование задачи «{task['title']}».\nВыберите поле:",
            attachments=[keyboards.task_edit_fields(task_id).as_markup()],
        )
        return

    if sub == "edit_field":
        task_id = int(parts[2])
        field = parts[3]
        allowed = {"title", "partner_name", "description", "max_teams", "education_program"}
        if field not in allowed:
            await event.ack(notification="Недопустимое поле")
            return
        await context.clear()
        await context.update_data(edit_task_id=task_id, edit_field=field)
        await context.set_state(TaskAdmin.edit_value)

        field_prompts = {
            "title": "Введите новое название проекта:",
            "partner_name": "Введите новое наименование партнёра:",
            "description": "Введите новое описание:",
            "max_teams": "Введите новое максимальное количество команд (число):",
            "education_program": "Введите новую образовательную программу (или «-» чтобы удалить):",
        }
        await event.edit(
            text=field_prompts[field],
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return


# ── Выгрузка выбора проектов (раздел 2.5) ──────────────────────────────────
@router.message_callback(CbPrefix("expch"))
async def export_choices_cb(event: MessageCallback) -> None:
    user_id = event.callback.user.user_id
    if not _guard(user_id):
        await event.ack(notification="Недостаточно прав")
        return
    await event.ack(notification="Готовлю файл…")
    path = reports.export_task_choices()
    await _send_file(user_id, path, "📊 Выгрузка данных по выбору проектов:")


# ── FSM добавления задачи ──────────────────────────────────────────────────
@router.message_created(TaskAdmin.title, F.message.body.text)
async def ta_title(event: MessageCreated, context: BaseContext) -> None:
    title = (event.message.body.text or "").strip()
    if not title:
        await event.message.answer("Название не может быть пустым:")
        return
    await context.update_data(title=title)
    await context.set_state(TaskAdmin.partner)
    await event.message.answer("Введите наименование социального партнёра:")


@router.message_created(TaskAdmin.partner, F.message.body.text)
async def ta_partner(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(partner=(event.message.body.text or "").strip())
    await context.set_state(TaskAdmin.description)
    await event.message.answer("Введите краткое описание (1-2 предложения):")


@router.message_created(TaskAdmin.description, F.message.body.text)
async def ta_description(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(description=(event.message.body.text or "").strip())
    await context.set_state(TaskAdmin.max_teams)
    await event.message.answer(
        "Сколько команд могут взять эту задачу? Введите число:")


@router.message_created(TaskAdmin.max_teams, F.message.body.text)
async def ta_max_teams(event: MessageCreated, context: BaseContext) -> None:
    ok, value = validators.validate_int(event.message.body.text or "")
    if not ok or value < 1:
        await event.message.answer("Введите целое число больше 0:")
        return
    await context.update_data(max_teams=value)
    await context.set_state(TaskAdmin.program)
    await event.message.answer(
        "Укажите образовательную программу для задачи "
        "(или отправьте «-», чтобы пропустить):")


@router.message_created(TaskAdmin.edit_value, F.message.body.text)
async def ta_edit_value(event: MessageCreated, context: BaseContext) -> None:
    """Сохраняет отредактированное поле задачи."""
    data = await context.get_data()
    task_id = data.get("edit_task_id")
    field = data.get("edit_field")
    if not task_id or not field:
        await context.clear()
        return

    raw = (event.message.body.text or "").strip()
    if field == "max_teams":
        ok, value = validators.validate_int(raw)
        if not ok or value < 1:
            await event.message.answer("Введите целое число больше 0:")
            return
    elif field == "education_program":
        value = None if raw == "-" else raw
    else:
        value = raw

    if not value and field != "education_program":
        await event.message.answer("Значение не может быть пустым. Попробуйте ещё раз:")
        return

    repo.update_task(task_id, **{field: value})
    await context.clear()

    task = repo.get_task(task_id)
    await event.message.answer(
        f"✅ Задача «{task['title']}» обновлена.",
        attachments=[keyboards.task_admin_actions(task["id"], task["active"]).as_markup()],
    )


@router.message_created(TaskAdmin.program, F.message.body.text)
async def ta_program(event: MessageCreated, context: BaseContext) -> None:
    program = (event.message.body.text or "").strip()
    program = None if program == "-" else program
    data = await context.get_data()
    number = len(repo.list_tasks()) + 1
    repo.add_task(
        number=number,
        title=data["title"],
        partner_name=data.get("partner", ""),
        description=data.get("description", ""),
        max_teams=data.get("max_teams", 1),
        education_program=program,
    )
    await context.clear()
    await event.message.answer(
        f"✅ Задача «{data['title']}» добавлена (№{number}).",
        attachments=[keyboards.task_admin_menu().as_markup()],
    )

    # Уведомляем всех студентов о новом проекте
    await notify_students(
        text=(
            f"🆕 **Новый проект доступен!**\n\n"
            f"📌 {data['title']}\n"
            f"🤝 Партнёр: {data.get('partner', '—')}\n\n"
            f"📝 {data.get('description', '')}\n\n"
            f"Выбери этот проект в разделе «Выбор проекта»!"
        )
    )
