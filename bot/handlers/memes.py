"""Мемы по кодовому слову (2.9) и управление ими администратором."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.enums.upload_type import UploadType
from maxapi.types.attachments.image import Image
from maxapi.types.attachments.upload import AttachmentPayload, AttachmentUpload
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, repo
from ..filters import CbPrefix
from ..states import MemeAdmin

router = Router(router_id="memes")


def _meme_attachment(token: str | None):
    if not token:
        return None
    return AttachmentUpload(
        type=UploadType.IMAGE, payload=AttachmentPayload(token=token)
    )


async def _send_meme(event: MessageCreated, meme) -> None:
    attachment = _meme_attachment(meme["image_path"])
    await event.message.answer(
        text=meme["text"] or "",
        attachments=[attachment] if attachment else None,
    )


# ── Управление мемами (админ) ──────────────────────────────────────────────
@router.message_callback(CbPrefix("meme"))
async def meme_cb(event: MessageCallback, context: BaseContext) -> None:
    if not repo.is_admin(event.callback.user.user_id):
        await event.ack(notification="Недостаточно прав")
        return
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if sub == "menu":
        memes = repo.list_memes()
        listing = "\n".join(f"• {m['code_word']}" for m in memes) or "—"
        await event.edit(
            text=f"😎 Управление мемами.\nТекущие кодовые слова:\n{listing}",
            attachments=[keyboards.memes_admin_menu(memes).as_markup()],
        )
        return

    if sub == "add":
        await context.clear()
        await context.set_state(MemeAdmin.code_word)
        await event.edit(
            text="Введите кодовое слово для мема:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "del":
        code = parts[2]
        repo.delete_meme(code)
        memes = repo.list_memes()
        await event.edit(
            text=f"Мем «{code}» удалён.",
            attachments=[keyboards.memes_admin_menu(memes).as_markup()],
        )
        return


@router.message_created(MemeAdmin.code_word, F.message.body.text)
async def meme_code(event: MessageCreated, context: BaseContext) -> None:
    code = (event.message.body.text or "").strip()
    if not code:
        await event.message.answer("Кодовое слово не может быть пустым:")
        return
    await context.update_data(code_word=code)
    await context.set_state(MemeAdmin.text)
    await event.message.answer("Введите текст, который будет отправлен с мемом:")


@router.message_created(MemeAdmin.text, F.message.body.text)
async def meme_text(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(meme_text=(event.message.body.text or "").strip())
    await context.set_state(MemeAdmin.image)
    await event.message.answer(
        "Отправьте картинку для мема (или «-», чтобы оставить без картинки):")


@router.message_created(MemeAdmin.image, F.message.body.attachments)
async def meme_image(event: MessageCreated, context: BaseContext) -> None:
    body = event.message.body
    attachments = body.attachments if body else None
    token = None
    if attachments and isinstance(attachments[0], Image):
        payload = attachments[0].payload
        token = getattr(payload, "token", None)
    if not token:
        await event.message.answer("Не удалось распознать картинку. Отправьте фото ещё раз или «-»:")
        return
    data = await context.get_data()
    repo.upsert_meme(data["code_word"], data.get("meme_text", ""), token)
    await context.clear()
    await event.message.answer(
        f"✅ Мем по кодовому слову «{data['code_word']}» сохранён.",
        attachments=[keyboards.memes_admin_menu(repo.list_memes()).as_markup()],
    )


@router.message_created(MemeAdmin.image, F.message.body.text)
async def meme_image_skip(event: MessageCreated, context: BaseContext) -> None:
    if (event.message.body.text or "").strip() != "-":
        await event.message.answer("Отправьте картинку или «-», чтобы пропустить:")
        return
    data = await context.get_data()
    repo.upsert_meme(data["code_word"], data.get("meme_text", ""), None)
    await context.clear()
    await event.message.answer(
        f"✅ Мем по кодовому слову «{data['code_word']}» сохранён (без картинки).",
        attachments=[keyboards.memes_admin_menu(repo.list_memes()).as_markup()],
    )


# ── Глобальный fallback: реакция на кодовое слово ──────────────────────────
@router.message_created(F.message.body.text)
async def code_word_listener(event: MessageCreated) -> None:
    text = (event.message.body.text or "").strip()
    meme = repo.get_meme(text)
    if meme:
        await _send_meme(event, meme)
        return
    # Не кодовое слово и не активный сценарий — подсказываем меню.
    await event.message.answer("Не понимаю команду. Откройте меню: /menu")
