"""Единый экземпляр бота и диспетчера, используемый всеми роутерами."""

from __future__ import annotations

from maxapi import Bot, Dispatcher
from maxapi.types.updates.message_callback import MessageCallback

from . import config

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Автоматически подтверждаем callback после event.edit(), чтобы кнопки не "зависали".
_original_edit = MessageCallback.edit


async def _edit_and_ack(self, *args, **kwargs):
    result = await _original_edit(self, *args, **kwargs)
    try:
        await self.ack()
    except Exception:
        pass
    return result


MessageCallback.edit = _edit_and_ack
