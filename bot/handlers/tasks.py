"""Выбор социальной задачи студентами: команды, выбор и подтверждение (2.4).

Также просмотр списка задач преподавателями.
"""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, repo, validators
from ..common_ui import require_role
from ..filters import CbPrefix
from ..instance import bot
from ..states import TaskFlow

router = Router(router_id="tasks")


def _task_card_text(task) -> str:
    taken = repo.task_taken_count(task["id"])
    remaining = max(task["max_teams"] - taken, 0)
    return (
        f"📌 {task['title']}\n\n"
        f"Социальный партнёр: {task['partner_name']}\n\n"
        f"{task['description']}\n\n"
        f"Команд может взять задачу: {task['max_teams']} "
        f"(свободно мест: {remaining})"
    )


async def _show_available_tasks(event: MessageCallback, header: str,
                               program: str | None = None) -> None:
    tasks = repo.list_available_tasks_for_program(program)
    if not tasks:
        await event.edit(
            text=f"{header}\n\nСейчас нет доступных задач. Попробуйте позже.",
            attachments=[keyboards.InlineKeyboardBuilder().row(
                keyboards.back_button()).as_markup()],
        )
        return
    await event.edit(
        text=header,
        attachments=[keyboards.task_choose_list(tasks).as_markup()],
    )


@router.message_callback(CbPrefix("task"))
async def task_cb(event: MessageCallback, context: BaseContext) -> None:
    user_id = event.callback.user.user_id
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    # Просмотр списка задач (преподаватель)
    if sub == "list":
        if not require_role(user_id, "teacher", "admin", "student"):
            await event.ack(notification="Недоступно")
            return
        user = repo.get_user(user_id)
        user_role = user["role"] if user else None
        if user_role == "teacher":
            tp_raw = dict(user).get("teacher_programs") or ""
            prog_ids = [int(x) for x in tp_raw.split(",") if x.strip().isdigit()]
            from .. import texts as _t
            programs = [_t.STUDY_PROGRAMS[i] for i in prog_ids if i < len(_t.STUDY_PROGRAMS)]
            tasks = repo.list_tasks_for_programs(programs)
        else:
            tasks = repo.list_tasks()
        if not tasks:
            text = "Список задач пуст."
        else:
            lines = ["📑 Список задач:\n"]
            for t in tasks:
                prog = f" [{t['education_program']}]" if t["education_program"] else ""
                lines.append(
                    f"• {t['title']} — {t['partner_name']}{prog}\n  {t['description']}\n"
                    f"  Команд: {t['max_teams']}"
                )
            text = "\n\n".join(lines)
        await event.edit(
            text=text,
            attachments=[keyboards.InlineKeyboardBuilder().row(
                keyboards.back_button()).as_markup()],
        )
        return

    # Меню выбора задачи (студент)
    if sub == "menu":
        if not require_role(user_id, "student"):
            await event.ack(notification="Доступно только студентам")
            return
        existing = repo.get_user_team(user_id)
        if existing:
            task = repo.get_task(existing["task_id"]) if existing["task_id"] else None
            info = (f"\nВыбранная задача: {task['title']}" if task
                    else "\nЗадача ещё не выбрана.")
            await event.edit(
                text=(f"Вы уже состоите в команде «{existing['name']}» "
                      f"({'лидер' if existing['member_role'] == 'leader' else 'участник'})."
                      f"{info}"),
                attachments=[keyboards.InlineKeyboardBuilder().row(
                    keyboards.back_button()).as_markup()],
            )
            return
        await context.clear()
        await context.set_state(TaskFlow.role_in_team)
        await event.edit(
            text="Укажите вашу роль в команде:",
            attachments=[keyboards.team_role_select().as_markup()],
        )
        return

    # Задачи по программе студента
    if sub == "myprogram":
        user = repo.get_user(user_id)
        program = dict(user).get("education_program") if user else None
        tasks = repo.list_available_tasks_for_program(program)
        if not tasks:
            await event.edit(
                text="Сейчас нет доступных задач для вашей программы.",
                attachments=[keyboards.InlineKeyboardBuilder().row(
                    keyboards.back_button()).as_markup()],
            )
            return
        await event.edit(
            text="Задачи для вашей образовательной программы:",
            attachments=[keyboards.task_choose_list(tasks).as_markup()],
        )
        return

    # Выбор роли в команде
    if sub == "role":
        role = parts[2]
        if role == "leader":
            await context.set_state(TaskFlow.team_name)
            await event.edit(
                text="Создание команды.\nВведите название команды:",
                attachments=[keyboards.cancel_kb().as_markup()],
            )
        else:
            teams = repo.list_teams()
            if not teams:
                await event.edit(
                    text="Пока нет ни одной команды. Дождитесь, пока лидер создаст команду.",
                    attachments=[keyboards.InlineKeyboardBuilder().row(
                        keyboards.back_button()).as_markup()],
                )
            else:
                await context.set_state(TaskFlow.join_team)
                await event.edit(
                    text="Выберите команду из списка:",
                    attachments=[keyboards.teams_join_list(teams).as_markup()],
                )
        return

    # Открыть карточку задачи
    if sub == "open":
        task = repo.get_task(int(parts[2]))
        if task:
            await event.edit(
                text=_task_card_text(task),
                attachments=[keyboards.task_card_actions(task["id"]).as_markup()],
            )
        return

    # Назад к списку задач
    if sub == "back_list":
        user = repo.get_user(user_id)
        program = dict(user).get("education_program") if user else None
        await _show_available_tasks(event, "Выберите задачу для команды:", program=program)
        return

    # Нажатие «Выбрать задачу» -> подтверждение
    if sub == "pick":
        task = repo.get_task(int(parts[2]))
        if task:
            await event.edit(
                text=(_task_card_text(task) +
                      "\n\n⚠️ Обязательно обсудите решение заранее с командой. "
                      "После выбора задачи участники команды не смогут изменить решение."),
                attachments=[keyboards.task_confirm(task["id"]).as_markup()],
            )
        return

    # Подтверждение выбора задачи
    if sub == "confirm":
        task_id = int(parts[2])
        team = repo.get_user_team(user_id)
        if not team or team["member_role"] != "leader":
            await event.ack(notification="Только лидер может выбрать задачу")
            return
        # Повторная проверка свободных мест
        task = repo.get_task(task_id)
        if not task or task["active"] != 1 or \
                repo.task_taken_count(task_id) >= task["max_teams"]:
            await event.edit(
                text="К сожалению, эта задача уже недоступна. Выберите другую.",
                attachments=[keyboards.InlineKeyboardBuilder().row(
                    keyboards.back_button()).as_markup()],
            )
            return

        repo.set_team_task(team["id"], task_id)
        await event.edit(text="Задача выбрана успешно", attachments=[])

        # Уведомление всем участникам команды
        for m in repo.list_team_members(team["id"]):
            try:
                await bot.send_message(
                    user_id=m["user_id"],
                    text=f"Выбрана задача «{task['title']}».",
                )
            except Exception:  # noqa: BLE001
                continue
        return

    # Выбор команды для входа (участник)
    if sub == "join":
        team_id = int(parts[2])
        await context.update_data(join_team_id=team_id)
        await context.set_state(TaskFlow.join_password)
        team = repo.get_team(team_id)
        await event.edit(
            text=f"Команда «{team['name']}».\nВведите пароль:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return


# ── Текстовые шаги лидера ──────────────────────────────────────────────────
@router.message_created(TaskFlow.team_name, F.message.body.text)
async def leader_team_name(event: MessageCreated, context: BaseContext) -> None:
    name = (event.message.body.text or "").strip()
    if not name:
        await event.message.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    if repo.get_team_by_name(name):
        await event.message.answer("Команда с таким названием уже существует. Введите другое:")
        return
    await context.update_data(team_name=name)
    await context.set_state(TaskFlow.team_password)
    await event.message.answer("Задайте пароль (числовое значение):")


@router.message_created(TaskFlow.team_password, F.message.body.text)
async def leader_team_password(event: MessageCreated, context: BaseContext) -> None:
    ok, pwd = validators.validate_password(event.message.body.text or "")
    if not ok:
        await event.message.answer(validators.PASSWORD_ERROR)
        return
    data = await context.get_data()
    _, user_id = event.get_ids()
    repo.create_team(name=data["team_name"], password=pwd, leader_id=user_id)
    await context.set_state(TaskFlow.choose_task)
    user = repo.get_user(user_id)
    program = dict(user).get("education_program") if user else None
    tasks = repo.list_available_tasks_for_program(program)
    if not tasks:
        await context.clear()
        await event.message.answer(
            f"Команда «{data['team_name']}» создана! Сейчас нет доступных задач — "
            "загляните позже через меню «Выбор социальной задачи»."
        )
        return
    await event.message.answer(
        text=(f"Команда «{data['team_name']}» создана!\n\n"
              "Выберите задачу для команды.\n"
              "Обязательно обсудите решение заранее с командой. После выбора "
              "задачи участники команды не смогут изменить решение."),
        attachments=[keyboards.task_choose_list(tasks).as_markup()],
    )


# ── Текстовый шаг участника: пароль ────────────────────────────────────────
@router.message_created(TaskFlow.join_password, F.message.body.text)
async def member_join_password(event: MessageCreated, context: BaseContext) -> None:
    data = await context.get_data()
    team = repo.get_team(data.get("join_team_id"))
    _, user_id = event.get_ids()
    entered = (event.message.body.text or "").strip()
    if not team:
        await context.clear()
        await event.message.answer("Команда не найдена. Начните заново через меню.")
        return
    if entered != team["password"]:
        await event.message.answer("Неверный пароль")
        return
    repo.add_team_member(team["id"], user_id)
    await context.clear()
    await event.message.answer("Вы успешно вошли в команду проекта")
    # Если команда уже выбрала задачу — сообщим её
    if team["task_id"]:
        task = repo.get_task(team["task_id"])
        if task:
            await event.message.answer(f"Команда уже выбрала задачу «{task['title']}».")
