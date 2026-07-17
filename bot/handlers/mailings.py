"""Рассылка приглашений на мероприятия (2.7), напоминания о созвонах (2.8)."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.filters.command import Command
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, repo
from ..common_ui import full_name
from ..filters import CbPrefix
from ..instance import bot
from ..states import CallReminder, Mailing

router = Router(router_id="mailings")


def _guard(user_id: int) -> bool:
    return repo.is_admin(user_id)


async def _broadcast(event_id: int, recipients: list[int], text: str) -> int:
    sent = 0
    kb = keyboards.event_response(event_id).as_markup()
    for uid in recipients:
        repo.add_event_recipient(event_id, uid)
        try:
            await bot.send_message(user_id=uid, text=text, attachments=[kb])
            sent += 1
        except Exception:  # noqa: BLE001
            continue
    return sent


# ── Приглашение на мероприятие ──────────────────────────────────────────────
@router.message_callback(CbPrefix("mail"))
async def mail_cb(event: MessageCallback, context: BaseContext) -> None:
    if not _guard(event.callback.user.user_id):
        await event.ack(notification="Недостаточно прав")
        return
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if sub == "start":
        await context.clear()
        await event.edit(
            text="📨 Выберите аудиторию рассылки:",
            attachments=[keyboards.mailing_recipients_menu().as_markup()],
        )
        return

    if sub == "team":
        await context.clear()
        await context.set_state(Mailing.team_search)
        await event.edit(
            text="Введите название команды (или часть названия) для поиска:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "teampick" and len(parts) > 2:
        team_id = int(parts[2])
        members = [m["user_id"] for m in repo.list_team_members(team_id)]
        team = repo.get_team(team_id)
        team_name = team["name"] if team else f"#{team_id}"
        await context.clear()
        await context.update_data(
            recipients_fn="_team",
            audience=f"команда «{team_name}»",
            team_members=members,
        )
        await context.set_state(Mailing.text)
        await event.edit(
            text=(f"📨 Рассылка приглашения на мероприятие.\n\n"
                  f"Получатели: команда «{team_name}».\n\n"
                  f"Отправьте текст приглашения:"),
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub in ("all", "students", "teachers", "partners"):
        audience = {
            "all": (repo.list_all_active_users, "все пользователи"),
            "students": (repo.list_students, "все студенты"),
            "teachers": (repo.list_teachers, "все преподаватели"),
            "partners": (repo.list_partners, "все партнёры"),
        }[sub]
        await context.clear()
        await context.update_data(recipients_fn=audience[0].__name__, audience=audience[1])
        await context.set_state(Mailing.text)
        await event.edit(
            text=(f"📨 Рассылка приглашения на мероприятие.\n\n"
                  f"Получатели: {audience[1]}.\n\n"
                  f"Отправьте текст приглашения:"),
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return


@router.message_created(Mailing.team_search, F.message.body.text)
async def mail_team_search(event: MessageCreated, context: BaseContext) -> None:
    query = (event.message.body.text or "").strip()
    teams = repo.search_teams(query)
    if not teams:
        await event.message.answer(
            f"Команды по запросу «{query}» не найдены. Попробуйте другое название:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    await event.message.answer(
        "Выберите команду:",
        attachments=[keyboards.team_pick_mail(teams).as_markup()],
    )


@router.message_created(CallReminder.team_search, F.message.body.text)
async def call_team_search(event: MessageCreated, context: BaseContext) -> None:
    query = (event.message.body.text or "").strip()
    teams = repo.search_teams(query)
    if not teams:
        await event.message.answer(
            f"Команды по запросу «{query}» не найдены. Попробуйте другое название:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    await event.message.answer(
        "Выберите команду:",
        attachments=[keyboards.team_pick_call(teams).as_markup()],
    )


@router.message_created(Mailing.text, F.message.body.text)
async def mail_text(event: MessageCreated, context: BaseContext) -> None:
    text = (event.message.body.text or "").strip()
    _, admin_id = event.get_ids()
    data = await context.get_data()
    await context.clear()
    event_id = repo.create_event("event", text, None, admin_id)

    recipients_fn_name = data.get("recipients_fn", "list_all_active_users")
    if recipients_fn_name == "_team":
        recipients = data.get("team_members", [])
    else:
        recipients_fn = getattr(repo, recipients_fn_name, repo.list_all_active_users)
        recipients = [u["user_id"] for u in recipients_fn()]

    audience = data.get("audience", "все пользователи")
    sent = await _broadcast(event_id, recipients, f"📣 Приглашение на мероприятие\n\n{text}")
    await event.message.answer(
        f"✅ Рассылка отправлена ({sent} получателей).\n"
        f"Аудитория: {audience}.\n"
        f"Посмотреть подтверждения: /responses {event_id}"
    )


# ── Напоминание о созвоне (выбранной группе) ───────────────────────────────
@router.message_callback(CbPrefix("call"))
async def call_cb(event: MessageCallback, context: BaseContext) -> None:
    if not _guard(event.callback.user.user_id):
        await event.ack(notification="Недостаточно прав")
        return
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if sub == "start":
        await context.clear()
        await event.edit(
            text="📞 Напоминание о созвоне.\nВыберите получателей:",
            attachments=[keyboards.call_recipients_menu().as_markup()],
        )
        return

    if sub == "team":
        await context.clear()
        await context.set_state(CallReminder.team_search)
        await event.edit(
            text="Введите название команды (или часть названия) для поиска:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "teampick":
        team_id = int(parts[2])
        members = [m["user_id"] for m in repo.list_team_members(team_id)]
        team = repo.get_team(team_id)
        await context.update_data(recipients=members,
                                  audience=f"команда «{team['name']}»")
        await _ask_call_text(event, context)
        return

    if sub == "allst":
        recipients = [u["user_id"] for u in repo.list_students()]
        await context.update_data(recipients=recipients, audience="все студенты")
        await _ask_call_text(event, context)
        return

    if sub == "allteach":
        recipients = [u["user_id"] for u in repo.list_teachers()]
        await context.update_data(recipients=recipients, audience="все преподаватели")
        await _ask_call_text(event, context)
        return

    if sub == "all":
        recipients = [u["user_id"] for u in repo.list_all_active_users()]
        await context.update_data(recipients=recipients, audience="все пользователи")
        await _ask_call_text(event, context)
        return


async def _ask_call_text(event: MessageCallback, context: BaseContext) -> None:
    await context.set_state(CallReminder.text)
    data = await context.get_data()
    await event.edit(
        text=(f"Получатели: {data.get('audience', '')}.\n\n"
              "Отправьте текст напоминания о созвоне:"),
        attachments=[keyboards.cancel_kb().as_markup()],
    )


@router.message_created(CallReminder.text, F.message.body.text)
async def call_text(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(call_text=(event.message.body.text or "").strip())
    await context.set_state(CallReminder.link)
    await event.message.answer(
        "Отправьте ссылку на созвон (или «-», если без ссылки):")


@router.message_created(CallReminder.link, F.message.body.text)
async def call_link(event: MessageCreated, context: BaseContext) -> None:
    link_raw = (event.message.body.text or "").strip()
    link = None if link_raw == "-" else link_raw
    data = await context.get_data()
    _, admin_id = event.get_ids()
    recipients = data.get("recipients", [])
    await context.clear()

    event_id = repo.create_event("call", data.get("call_text", ""), link, admin_id)
    body = f"📞 Напоминание о созвоне\n\n{data.get('call_text', '')}"
    if link:
        body += f"\n\nСсылка: {link}"
    sent = await _broadcast(event_id, recipients, body)
    await event.message.answer(
        f"✅ Напоминание отправлено ({sent} получателей).\n"
        f"Посмотреть подтверждения: /responses {event_id}"
    )


# ── Ответ участника на приглашение/созвон ──────────────────────────────────
@router.message_callback(CbPrefix("evt"))
async def evt_cb(event: MessageCallback) -> None:
    parts = keyboards.parse_cb(event.callback.payload)
    if len(parts) != 3:
        return
    response = "yes" if parts[1] == "yes" else "no"
    event_id = int(parts[2])
    user_id = event.callback.user.user_id
    repo.set_event_response(event_id, user_id, response)
    label = "Вы подтвердили участие ✅" if response == "yes" else "Вы отказались ❌"
    await event.edit(text=event.message.body.text + f"\n\n{label}", attachments=[])
    await event.ack(notification=label)


# ── Просмотр подтверждений (админ) ─────────────────────────────────────────
@router.message_created(Command("responses"))
async def responses_cmd(event: MessageCreated) -> None:
    _, admin_id = event.get_ids()
    if not _guard(admin_id):
        return
    text = (event.message.body.text or "").strip()
    parts = text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await event.message.answer("Использование: /responses <id_рассылки>")
        return
    event_id = int(parts[1])
    rows = repo.list_event_responses(event_id)
    if not rows:
        await event.message.answer("По этой рассылке нет получателей.")
        return
    yes = [r for r in rows if r["response"] == "yes"]
    no = [r for r in rows if r["response"] == "no"]
    pending = [r for r in rows if not r["response"]]
    lines = [f"Подтверждения по рассылке #{event_id}:\n"]
    lines.append(f"✅ Будут ({len(yes)}):")
    lines += [f"  • {full_name(r)}" for r in yes] or ["  —"]
    lines.append(f"\n❌ Не будут ({len(no)}):")
    lines += [f"  • {full_name(r)}" for r in no] or ["  —"]
    lines.append(f"\n⏳ Без ответа ({len(pending)}):")
    lines += [f"  • {full_name(r)}" for r in pending] or ["  —"]
    await event.message.answer("\n".join(lines))
