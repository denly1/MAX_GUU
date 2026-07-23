"""Управление командами администратором."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from .. import keyboards, repo
from ..common_ui import full_name, require_role
from ..filters import CbPrefix
from ..states import TeamAdmin

router = Router(router_id="team_admin")


def _team_text(team, members, task) -> str:
    lines = [f"👥 Команда «{team['name']}» (#{team['id']})"]
    if task:
        lines.append(f"🗂 Проект: {task['title']}")
    else:
        lines.append("🗂 Проект: —")
    lines.append(f"Участников: {len(members)}")
    leader = next((m for m in members if m["role_in_team"] == "leader"), None)
    if leader:
        lines.append(f"⭐ Лидер: {full_name(leader)}")
    lines.append("")
    lines.append("Участники:")
    for m in members:
        role = "лидер" if m["role_in_team"] == "leader" else "участник"
        lines.append(f"• {full_name(m)} ({role})")
    return "\n".join(lines)


@router.message_callback(CbPrefix("teamadm"))
async def teamadm_cb(event: MessageCallback, context: BaseContext) -> None:
    admin_id = event.callback.user.user_id
    if not require_role(admin_id, "admin"):
        await event.ack(notification="Недостаточно прав")
        return

    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if not sub or sub == "menu":
        teams = repo.list_teams()
        items = [(t["name"], f"teamadm:view:{t['id']}") for t in teams]
        text = f"👥 Команды ({len(teams)})\n\nВыберите команду:"
        kb = keyboards.paginated_list(
            items, page=1, action_prefix="teamadm:page", items_per_page=10
        )
        kb.row(keyboards.back_button("apanel:main"))
        await event.edit(text=text, attachments=[kb.as_markup()])
        return

    if sub == "page" and len(parts) > 2 and parts[2].isdigit():
        page = int(parts[2])
        teams = repo.list_teams()
        items = [(t["name"], f"teamadm:view:{t['id']}") for t in teams]
        kb = keyboards.paginated_list(
            items, page=page, action_prefix="teamadm:page", items_per_page=10
        )
        kb.row(keyboards.back_button("apanel:main"))
        await event.edit(
            text=f"👥 Команды ({len(teams)})",
            attachments=[kb.as_markup()],
        )
        return

    if sub == "view" and len(parts) > 2:
        team_id = int(parts[2])
        team = repo.get_team(team_id)
        if not team:
            await event.ack(notification="Команда не найдена")
            return
        members = repo.list_team_members(team_id)
        task = repo.get_task(team["task_id"]) if team.get("task_id") else None
        text = _team_text(team, members, task)
        await event.edit(
            text=text,
            attachments=[keyboards.team_admin_actions(team_id).as_markup()],
        )
        return

    if sub == "rename" and len(parts) > 2:
        team_id = int(parts[2])
        await context.clear()
        await context.update_data(team_id=team_id)
        await context.set_state(TeamAdmin.name)
        await event.edit(
            text="Введите новое название команды:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "members" and len(parts) > 2:
        team_id = int(parts[2])
        members = repo.list_team_members(team_id)
        if not members:
            await event.edit(text="В команде пока нет участников.")
            return
        kb = InlineKeyboardBuilder()
        for m in members:
            fio = full_name(m)
            kb.row(CallbackButton(
                text=fio,
                payload=f"teamadm:member:{team_id}:{m['user_id']}",
            ))
        kb.row(keyboards.back_button(f"teamadm:view:{team_id}"))
        await event.edit(text="Выберите участника:", attachments=[kb.as_markup()])
        return

    if sub == "member" and len(parts) > 3:
        team_id = int(parts[2])
        user_id = int(parts[3])
        members = repo.list_team_members(team_id)
        member = next((m for m in members if m["user_id"] == user_id), None)
        if not member:
            await event.ack(notification="Участник не найден")
            return
        fio = full_name(member)
        text = f"Участник: {fio}\nРоль: {member['role_in_team']}"
        await event.edit(
            text=text,
            attachments=[keyboards.team_member_actions(team_id, user_id).as_markup()],
        )
        return

    if sub == "leader" and len(parts) > 3:
        team_id = int(parts[2])
        user_id = int(parts[3])
        repo.set_team_leader(team_id, user_id)
        await event.ack(notification="Лидер изменён")
        team = repo.get_team(team_id)
        members = repo.list_team_members(team_id)
        task = repo.get_task(team["task_id"]) if team and team.get("task_id") else None
        await event.edit(
            text=_team_text(team, members, task),
            attachments=[keyboards.team_admin_actions(team_id).as_markup()],
        )
        return

    if sub == "remove" and len(parts) > 3:
        team_id = int(parts[2])
        user_id = int(parts[3])
        members = repo.list_team_members(team_id)
        member = next((m for m in members if m["user_id"] == user_id), None)
        if member and member["role_in_team"] == "leader":
            await event.ack(notification="Сначала назначьте другого лидера")
            return
        repo.remove_team_member(team_id, user_id)
        await event.ack(notification="Участник исключён")
        members = repo.list_team_members(team_id)
        if not members:
            await event.edit(text="В команде пока нет участников.")
            return
        kb = InlineKeyboardBuilder()
        for m in members:
            kb.row(CallbackButton(
                text=full_name(m),
                payload=f"teamadm:member:{team_id}:{m['user_id']}",
            ))
        kb.row(keyboards.back_button(f"teamadm:view:{team_id}"))
        await event.edit(text="Выберите участника:", attachments=[kb.as_markup()])
        return

    if sub == "delete" and len(parts) > 2:
        team_id = int(parts[2])
        team = repo.get_team(team_id)
        team_name = team["name"] if team else f"#{team_id}"
        await event.edit(
            text=f"Удалить команду «{team_name}»? Все участники будут исключены.",
            attachments=[keyboards.confirm_kb(
                f"teamadm:delete_confirm:{team_id}", f"teamadm:view:{team_id}"
            ).as_markup()],
        )
        return

    if sub == "delete_confirm" and len(parts) > 2:
        team_id = int(parts[2])
        repo.delete_team(team_id)
        teams = repo.list_teams()
        items = [(t["name"], f"teamadm:view:{t['id']}") for t in teams]
        kb = keyboards.paginated_list(
            items, page=1, action_prefix="teamadm:page", items_per_page=10
        )
        kb.row(keyboards.back_button("apanel:main"))
        await event.edit(
            text=f"Команда удалена. Всего команд: {len(teams)}",
            attachments=[kb.as_markup()],
        )
        return


@router.message_created(TeamAdmin.name, F.message.body.text)
async def team_rename(event: MessageCreated, context: BaseContext) -> None:
    name = (event.message.body.text or "").strip()
    if not name:
        await event.message.answer("Название не может быть пустым:")
        return

    data = await context.get_data()
    team_id = data.get("team_id")
    if not team_id:
        await context.clear()
        return

    existing = repo.get_team_by_name(name)
    if existing and existing["id"] != team_id:
        await event.message.answer("Команда с таким названием уже существует. Введите другое:")
        return

    repo.update_team(team_id, name=name)
    await context.clear()
    await event.message.answer(
        f"Название команды обновлено на «{name}».",
        attachments=[keyboards.main_menu_kb().as_markup()],
    )
