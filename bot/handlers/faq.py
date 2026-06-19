"""Часто задаваемые вопросы, «задать свой вопрос», контакты, шаблоны."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from .. import keyboards, repo, texts, validators
from ..common_ui import notify_admins_with_markup, require_role
from ..filters import CbPrefix
from ..states import AskQuestion, FAQEdit

router = Router(router_id="faq")


@router.message_callback(CbPrefix("faq"))
async def faq_cb(event: MessageCallback, context: BaseContext) -> None:
    parts = keyboards.parse_cb(event.callback.payload)
    # parts = ['faq'] | ['faq','q','<id>'] | ['faq','ask']
    if len(parts) == 1:
        await event.edit(
            text="Часто задаваемые вопросы.\nВыберите вопрос:",
            attachments=[keyboards.faq_list(repo.list_faq()).as_markup()],
        )
        return

    if parts[1] == "q":
        faq = repo.get_faq(int(parts[2]))
        if faq:
            await event.edit(
                text=f"{faq['question']}\n\n{faq['answer']}",
                attachments=[keyboards.faq_back().as_markup()],
            )
        return

    if parts[1] == "ask":
        await context.clear()
        await context.set_state(AskQuestion.text)
        await event.edit(
            text="Укажите ваш вопрос:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    
    # Управление FAQ (только для админов)
    if parts[1] == "manage":
        user_id = event.callback.user.user_id
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        faqs = repo.list_faq()
        await event.edit(
            text="Управление FAQ:",
            attachments=[keyboards.faq_manage(faqs).as_markup()],
        )
        return
    
    # Добавить FAQ
    if parts[1] == "add":
        user_id = event.callback.user.user_id
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        await context.clear()
        await context.set_state(FAQEdit.question)
        await event.edit(
            text="Добавление FAQ\n\nВведите вопрос:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return
    
    # Удалить FAQ
    if parts[1] == "delete":
        user_id = event.callback.user.user_id
        if not require_role(user_id, "admin"):
            await event.ack(notification="Доступно только администраторам")
            return
        faq_id = int(parts[2])
        repo.delete_faq(faq_id)
        faqs = repo.list_faq()
        await event.edit(
            text="FAQ удален.\n\nУправление FAQ:",
            attachments=[keyboards.faq_manage(faqs).as_markup()],
        )
        return


@router.message_created(AskQuestion.text, F.message.body.text)
async def ask_text(event: MessageCreated, context: BaseContext) -> None:
    text = (event.message.body.text or "").strip()
    if not text:
        await event.message.answer("Вопрос не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(question_text=text)
    await context.set_state(AskQuestion.fio)
    await event.message.answer("Укажите ваше ФИО:")


@router.message_created(AskQuestion.fio, F.message.body.text)
async def ask_fio(event: MessageCreated, context: BaseContext) -> None:
    fio = (event.message.body.text or "").strip()
    if not fio:
        await event.message.answer("ФИО не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(fio=fio)
    await context.set_state(AskQuestion.phone)
    await event.message.answer("Укажите ваш номер телефона в формате 8 ххх-ххх хх хх:")


@router.message_created(AskQuestion.phone, F.message.body.text)
async def ask_phone(event: MessageCreated, context: BaseContext) -> None:
    ok, phone = validators.validate_phone(event.message.body.text or "")
    if not ok:
        await event.message.answer(validators.PHONE_ERROR)
        return
    data = await context.get_data()
    _, user_id = event.get_ids()
    qid = repo.add_user_question(
        user_id=user_id,
        question_text=data.get("question_text", ""),
        fio=data.get("fio", ""),
        phone=phone,
    )
    await context.clear()
    await event.message.answer(
        "Спасибо! Ваш вопрос отправлен администраторам. Мы свяжемся с вами."
    )
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Ответить", payload=f"fb:answer:{qid}"))
    await notify_admins_with_markup(
        text=(
            f"Новый вопрос (#{qid})\n\n"
            f"От: {data.get('fio', '')}\n"
            f"Телефон: {phone}\n\n"
            f"Вопрос: {data.get('question_text', '')}"
        ),
        markup=kb,
    )


# ── FSM: Добавление FAQ (админ) ────────────────────────────────────────────
@router.message_created(FAQEdit.question, F.message.body.text)
async def faq_question(event: MessageCreated, context: BaseContext) -> None:
    question = (event.message.body.text or "").strip()
    if not question:
        await event.message.answer("Вопрос не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(question=question)
    await context.set_state(FAQEdit.answer)
    await event.message.answer("Введите ответ на вопрос:")


@router.message_created(FAQEdit.answer, F.message.body.text)
async def faq_answer(event: MessageCreated, context: BaseContext) -> None:
    answer = (event.message.body.text or "").strip()
    if not answer:
        await event.message.answer("Ответ не может быть пустым. Попробуйте ещё раз:")
        return
    
    data = await context.get_data()
    repo.add_faq(question=data['question'], answer=answer)
    await context.clear()
    
    await event.message.answer(
        f"FAQ добавлен!\n\n{data['question']}\n\n{answer}",
        attachments=[keyboards.main_menu_kb().as_markup()],
    )


# ── Примеры отчётности ─────────────────────────────────────────────────────
@router.message_callback(CbPrefix("templates"))
async def templates_cb(event: MessageCallback) -> None:
    kb = keyboards.InlineKeyboardBuilder()
    kb.row(keyboards.back_button())
    await event.edit(
        text=(
            "Примеры отчётности:\n\n"
            f"• Шаблон презентации на защиту:\n{texts.TEMPLATE_PRESENTATION}\n\n"
            f"• Шаблон визитки / стендовой презентации:\n{texts.TEMPLATE_VISITKA}"
        ),
        attachments=[kb.as_markup()],
    )
