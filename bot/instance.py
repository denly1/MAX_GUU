"""Единый экземпляр бота и диспетчера, используемый всеми роутерами."""

from __future__ import annotations

from maxapi import Bot, Dispatcher

from . import config

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
