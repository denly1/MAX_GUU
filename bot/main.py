"""Точка входа: инициализация БД, подключение роутеров, запуск polling."""

from __future__ import annotations

import asyncio
import logging

from maxapi.types import BotCommand

from . import config
from .database import init_db
from .handlers import all_routers
from .instance import bot, dp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("osl_bot")


async def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit(
            "Не задан токен бота. Укажите MAX_BOT_TOKEN в .env (см. .env.example)."
        )

    init_db()
    dp.include_routers(*all_routers)

    if config.ADMIN_IDS:
        log.info("Bootstrap-администраторы: %s", sorted(config.ADMIN_IDS))
    else:
        log.warning(
            "ADMIN_IDS пуст — некому верифицировать пользователей. "
            "Узнайте свой id командой /id и добавьте его в .env."
        )

    # На случай ранее активных webhook-подписок — события polling иначе не придут.
    try:
        await bot.delete_webhook()
    except Exception as e:  # noqa: BLE001
        log.debug("delete_webhook: %s", e)

    # Регистрируем список команд бота, чтобы меню команд (значок "/") было
    # доступно и в десктоп-версии MAX, и на Android (не только на iOS).
    try:
        await bot.set_my_commands(
            BotCommand(name="/start", description="Запустить бота / главное меню"),
            BotCommand(name="/menu", description="Открыть главное меню"),
            BotCommand(name="/admin", description="Панель администратора"),
            BotCommand(name="/id", description="Показать свой user_id"),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("Не удалось установить список команд бота: %s", e)

    log.info("Бот запущен (polling).")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
