"""Верификация пользователей администратором (раздел 2.3)."""

from __future__ import annotations

from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback

from .. import keyboards, repo, texts
from ..common_ui import full_name, send_main_menu
from ..filters import CbPrefix
from ..instance import bot

router = Router(router_id="verification")


@router.message_callback(CbPrefix("ver"))
async def ver_cb(event: MessageCallback) -> None:
    admin_id = event.callback.user.user_id
    if not repo.is_admin(admin_id):
        await event.ack(notification="Недостаточно прав")
        return

    parts = keyboards.parse_cb(event.callback.payload)

    # ver:menu — список ожидающих
    if len(parts) == 2 and parts[1] == "menu":
        pending = repo.list_users_by_status("pending")
        await event.edit(
            text=(f"✅ Верификация пользователей\nОжидают подтверждения: "
                  f"{len(pending)}"),
            attachments=[keyboards.InlineKeyboardBuilder().row(
                keyboards.back_button()).as_markup()],
        )
        for u in pending:
            role = texts.ROLE_LABELS.get(u["role"], u["role"] or "—")
            extra = ""
            if u["role"] == "student":
                extra = (f"\nИнститут: {u['institute']}, курс {u['course']}, "
                         f"группа {u['group_name']}")
            elif u["role"] == "teacher":
                extra = f"\nКафедра: {u['department']}"
            elif u["role"] == "partner":
                extra = f"\nОрганизация: {u['organization']}"
            await bot.send_message(
                user_id=admin_id,
                text=(f"👤 {full_name(u)}\nРоль: {role}{extra}\n"
                      f"Телефон: {u['phone']}"),
                attachments=[keyboards.verify_actions(u["user_id"]).as_markup()],
            )
        return

    # ver:approve:<uid> / ver:reject:<uid>
    if len(parts) == 3 and parts[1] in ("approve", "reject"):
        target = int(parts[2])
        if parts[1] == "approve":
            repo.set_user_status(target, "verified")
            await event.edit(text="✅ Пользователь подтверждён.", attachments=[])
            try:
                await bot.send_message(user_id=target, text=texts.VERIFIED_NOTICE)
                await send_main_menu(target)
            except Exception:  # noqa: BLE001
                pass
        else:
            repo.set_user_status(target, "rejected")
            await event.edit(text="❌ Пользователь отклонён.", attachments=[])
            try:
                await bot.send_message(user_id=target, text=texts.REJECTED_NOTICE)
            except Exception:  # noqa: BLE001
                pass
        return
