"""Обратная связь (2.10) и ответы администратора на вопросы/обращения."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.filters.command import Command
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, repo
from ..common_ui import notify_admins, require_verified
from ..filters import CbPrefix
from ..instance import bot
from ..states import AnswerDialog, Feedback

router = Router(router_id="feedback")


@router.message_callback(CbPrefix("fb"))
async def fb_start(event: MessageCallback, context: BaseContext) -> None:
    user_id = event.callback.user.user_id
    if not require_verified(user_id):
        await event.ack(notification="Доступно после регистрации")
        return
    await context.clear()
    await context.set_state(Feedback.text)
    await event.edit(
        text=("💬 Обратная связь.\nНапишите ваш вопрос или сообщение — "
              "оно будет направлено администратору, и он вам ответит:"),
        attachments=[keyboards.cancel_kb().as_markup()],
    )


@router.message_created(Feedback.text, F.message.body.text)
async def fb_text(event: MessageCreated, context: BaseContext) -> None:
    text = (event.message.body.text or "").strip()
    if not text:
        await event.message.answer("Сообщение не может быть пустым:")
        return
    _, user_id = event.get_ids()
    fid = repo.add_feedback(user_id, text)
    await context.clear()
    await event.message.answer("Спасибо! Ваше сообщение отправлено администратору.")
    user = repo.get_user(user_id)
    fio = " ".join(filter(None, [user["last_name"], user["first_name"],
                                 user["patronymic"]])) if user else str(user_id)
    await notify_admins(
        text=(f"💬 Новое сообщение обратной связи (#{fid})\n\n"
              f"От: {fio}\nТелефон: {user['phone'] if user else '—'}\n\n"
              f"Сообщение: {text}\n\nОтветить: /answerf {fid}")
    )


# ── Ответы администратора ──────────────────────────────────────────────────
@router.message_created(Command("answerq"))
async def answerq(event: MessageCreated, context: BaseContext) -> None:
    _, admin_id = event.get_ids()
    if not repo.is_admin(admin_id):
        return
    parts = (event.message.body.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await event.message.answer("Использование: /answerq <id_вопроса>")
        return
    q = repo.get_question(int(parts[1]))
    if not q:
        await event.message.answer("Вопрос не найден.")
        return
    await context.set_state(AnswerDialog.text)
    await context.update_data(kind="q", target_id=q["id"], recipient=q["user_id"])
    await event.message.answer(
        f"Вопрос от {q['fio']}:\n«{q['question_text']}»\n\nВведите ваш ответ:")


@router.message_created(Command("answerf"))
async def answerf(event: MessageCreated, context: BaseContext) -> None:
    _, admin_id = event.get_ids()
    if not repo.is_admin(admin_id):
        return
    parts = (event.message.body.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await event.message.answer("Использование: /answerf <id_обращения>")
        return
    f = repo.get_feedback(int(parts[1]))
    if not f:
        await event.message.answer("Обращение не найдено.")
        return
    await context.set_state(AnswerDialog.text)
    await context.update_data(kind="f", target_id=f["id"], recipient=f["user_id"])
    await event.message.answer(
        f"Обращение:\n«{f['text']}»\n\nВведите ваш ответ:")


@router.message_created(AnswerDialog.text, F.message.body.text)
async def answer_send(event: MessageCreated, context: BaseContext) -> None:
    answer = (event.message.body.text or "").strip()
    if not answer:
        await event.message.answer("Ответ не может быть пустым:")
        return
    data = await context.get_data()
    await context.clear()
    recipient = data.get("recipient")
    if data.get("kind") == "q":
        repo.answer_question(data["target_id"], answer)
        prefix = "Ответ на ваш вопрос"
    else:
        repo.answer_feedback(data["target_id"], answer)
        prefix = "Ответ на ваше обращение"
    try:
        await bot.send_message(user_id=recipient, text=f"📩 {prefix}:\n\n{answer}")
    except Exception:  # noqa: BLE001
        await event.message.answer("Не удалось доставить ответ пользователю.")
        return
    await event.message.answer("✅ Ответ отправлен пользователю.")
