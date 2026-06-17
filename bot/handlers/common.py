"""Базовые обработчики: запуск, главное меню, навигация, отмена."""

from __future__ import annotations

import logging

from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.filters.command import Command, CommandStart
from maxapi.types.updates.bot_started import BotStarted
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import config, repo, texts
from ..common_ui import send_main_menu
from ..filters import CbPrefix

log = logging.getLogger(__name__)
router = Router(router_id="common")


def _display_name(user_obj) -> str | None:
    for attr in ("name", "first_name", "username"):
        val = getattr(user_obj, attr, None)
        if val:
            return val
    return None


async def _bootstrap(user_id: int, chat_id: int | None, name: str | None) -> None:
    """Регистрирует контакт и при необходимости назначает bootstrap-админа."""
    repo.upsert_user_contact(user_id, chat_id, name)
    if user_id in config.ADMIN_IDS:
        user = repo.get_user(user_id)
        if not user or user["role"] != "admin" or user["status"] != "verified":
            repo.set_user_role(user_id, "admin", status="verified")


@router.bot_started()
async def on_bot_started(event: BotStarted) -> None:
    chat_id, user_id = event.get_ids()
    await _bootstrap(user_id, chat_id, _display_name(event.user))
    await send_main_menu(user_id)


@router.message_created(CommandStart())
async def on_start(event: MessageCreated, context: BaseContext) -> None:
    await context.clear()
    chat_id, user_id = event.get_ids()
    if user_id is None:
        return
    name = _display_name(event.message.sender) if event.message.sender else None
    await _bootstrap(user_id, chat_id, name)
    await send_main_menu(user_id)


@router.message_created(Command("id"))
async def on_id(event: MessageCreated) -> None:
    _, user_id = event.get_ids()
    await event.message.answer(
        f"Ваш MAX user_id: {user_id}\n\n"
        "Передайте его, чтобы вас добавили в список администраторов (ADMIN_IDS)."
    )


@router.message_created(Command("menu"))
async def on_menu_cmd(event: MessageCreated, context: BaseContext) -> None:
    await context.clear()
    _, user_id = event.get_ids()
    if user_id is not None:
        await send_main_menu(user_id)


@router.message_callback(CbPrefix("menu"))
async def on_menu_cb(event: MessageCallback, context: BaseContext) -> None:
    await context.clear()
    await send_main_menu(event.callback.user.user_id)
    await event.ack(notification="Главное меню")


@router.message_callback(CbPrefix("cancel"))
async def on_cancel_cb(event: MessageCallback, context: BaseContext) -> None:
    await context.clear()
    await event.ack(notification="Отменено")
    await send_main_menu(event.callback.user.user_id)
