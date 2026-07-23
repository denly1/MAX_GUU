"""Подача заявки на реализацию проекта (2.12) — преподаватель/соц. партнёр.

Также просмотр поступивших заявок администратором.
"""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from .. import keyboards, repo, reports, texts, validators
from ..common_ui import notify_admins, require_role
from ..filters import CbPrefix
from ..instance import bot
from ..states import Application, AdminSearch

router = Router(router_id="applications")

SKIP_HINT = " (или «-», чтобы пропустить)"

# Последний поисковый запрос по заявкам (для постраничной навигации).
_last_app_query: dict[int, str] = {}


def _apps_list_kb(apps: list, search_mode: bool = False, query: str = "") -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    if not search_mode:
        kb.row(CallbackButton(text="📊 Выгрузить в Excel", payload="apps:export"))
    kb.row(CallbackButton(text="🔍 Поиск", payload="apps:search"))
    for a in apps[:30]:
        kb.row(CallbackButton(
            text=f"#{a['id']} {a['project_name']} — {a['org_name']}",
            payload=f"apps:view:{a['id']}"
        ))
    kb.row(keyboards.back_button())
    return kb


def _source_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for i, label in enumerate(texts.APPLICATION_SOURCES):
        kb.row(CallbackButton(text=label, payload=f"app:source:{i}"))
    kb.row(keyboards.back_button())
    return kb


# ── Старт и выбор источника ────────────────────────────────────────────────
@router.message_callback(CbPrefix("app"))
async def app_cb(event: MessageCallback, context: BaseContext) -> None:
    user_id = event.callback.user.user_id
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if sub == "start":
        if not require_role(user_id, "teacher", "partner"):
            await event.ack(notification="Доступно преподавателям и партнёрам")
            return
        await context.clear()
        await context.set_state(Application.project_name)
        await event.edit(
            text=("📝 Заявка на проекта.\n\n"
                  "Название проекта (короткое, яркое — например: Зазеркалье):"),
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    if sub == "source":
        idx = int(parts[2])
        await context.update_data(source=texts.APPLICATION_SOURCES[idx])
        if idx in (1, 2):  # кафедральные заказы — спрашиваем кафедру
            await context.set_state(Application.department)
            await event.edit(text="Укажите полное наименование кафедры:",
                             attachments=[keyboards.cancel_kb().as_markup()])
        else:
            await context.set_state(Application.description)
            await event.edit(
                text="Опишите проект в целом и роль студенческой команды в нём:",
                attachments=[keyboards.cancel_kb().as_markup()])
        return


@router.message_created(AdminSearch.applications, F.message.body.text)
async def app_search_query(event: MessageCreated, context: BaseContext) -> None:
    query = (event.message.body.text or "").strip()
    if not query:
        await event.message.answer("Введите непустой запрос для поиска:")
        return
    _, admin_id = event.get_ids()
    _last_app_query[admin_id] = query
    await context.clear()
    apps = repo.search_applications(query)
    await event.message.answer(
        text=f"🔍 Результаты поиска «{query}»: {len(apps)}",
        attachments=[_apps_list_kb(apps, search_mode=True).as_markup()],
    )


async def _next(event: MessageCreated, context: BaseContext, state, prompt: str):
    await context.set_state(state)
    await event.message.answer(prompt)


@router.message_created(Application.project_name, F.message.body.text)
async def a_project_name(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(project_name=(event.message.body.text or "").strip())
    await _next(event, context, Application.org_name,
                "Полное юридическое название организации-партнёра:")


@router.message_created(Application.org_name, F.message.body.text)
async def a_org_name(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(org_name=(event.message.body.text or "").strip())
    await context.set_state(Application.source)
    await event.message.answer("Источник задачи:",
                               attachments=[_source_kb().as_markup()])


@router.message_created(Application.department, F.message.body.text)
async def a_department(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(department=(event.message.body.text or "").strip())
    await _next(event, context, Application.description,
                "Опишите проект в целом и роль студенческой команды в нём:")


@router.message_created(Application.description, F.message.body.text)
async def a_description(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(description=(event.message.body.text or "").strip())
    await _next(event, context, Application.dobro_link,
                "Ссылка на проект на Добро.РФ" + SKIP_HINT + ":")


@router.message_created(Application.dobro_link, F.message.body.text)
async def a_dobro(event: MessageCreated, context: BaseContext) -> None:
    raw = (event.message.body.text or "").strip()
    if raw != "-":
        ok, url = validators.validate_url(raw)
        if not ok:
            await event.message.answer(validators.URL_ERROR + " Либо «-», чтобы пропустить:")
            return
        await context.update_data(dobro_link=url)
    await _next(event, context, Application.target_audience,
                "Опишите целевую аудиторию благополучателей:")


@router.message_created(Application.target_audience, F.message.body.text)
async def a_audience(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(target_audience=(event.message.body.text or "").strip())
    await _next(event, context, Application.beneficiaries_count,
                "Укажите ожидаемое количество благополучателей:")


@router.message_created(Application.beneficiaries_count, F.message.body.text)
async def a_benef(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(beneficiaries_count=(event.message.body.text or "").strip())
    await _next(event, context, Application.mechanism,
                "Опишите предполагаемый механизм действий при выполнении задачи:")


@router.message_created(Application.mechanism, F.message.body.text)
async def a_mechanism(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(mechanism=(event.message.body.text or "").strip())
    await _next(event, context, Application.desired_product,
                "Желаемый продукт по итогам выполнения задачи:")


@router.message_created(Application.desired_product, F.message.body.text)
async def a_product(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(desired_product=(event.message.body.text or "").strip())
    await _next(event, context, Application.skills,
                "Какие навыки приобретут студенты (жёсткие и гибкие)?")


@router.message_created(Application.skills, F.message.body.text)
async def a_skills(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(skills=(event.message.body.text or "").strip())
    await _next(event, context, Application.study_directions,
                "Предполагаемые направления обучения студентов" + SKIP_HINT + ":")


@router.message_created(Application.study_directions, F.message.body.text)
async def a_directions(event: MessageCreated, context: BaseContext) -> None:
    raw = (event.message.body.text or "").strip()
    if raw != "-":
        await context.update_data(study_directions=raw)
    await _next(event, context, Application.period_start,
                "Дата начала проекта (осень: не раньше 25.09; весна: не раньше 09.02):")


@router.message_created(Application.period_start, F.message.body.text)
async def a_period_start(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(period_start=(event.message.body.text or "").strip())
    await _next(event, context, Application.period_end,
                "Дата окончания проекта (осень: не позднее 05.12; весна: не позднее 25.05):")


@router.message_created(Application.period_end, F.message.body.text)
async def a_period_end(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(period_end=(event.message.body.text or "").strip())
    await _next(event, context, Application.contact_fio,
                "ФИО контактного лица:")


@router.message_created(Application.contact_fio, F.message.body.text)
async def a_contact_fio(event: MessageCreated, context: BaseContext) -> None:
    await context.update_data(contact_fio=(event.message.body.text or "").strip())
    await _next(event, context, Application.contact_phone,
                "Телефон контактного лица в формате 8 ххх-ххх хх хх:")


@router.message_created(Application.contact_phone, F.message.body.text)
async def a_contact_phone(event: MessageCreated, context: BaseContext) -> None:
    ok, phone = validators.validate_phone(event.message.body.text or "")
    if not ok:
        await event.message.answer(validators.PHONE_ERROR)
        return
    await context.update_data(contact_phone=phone)
    await _next(event, context, Application.contact_telegram,
                "Ник в телеграм в формате @ххххх" + SKIP_HINT + ":")


@router.message_created(Application.contact_telegram, F.message.body.text)
async def a_contact_telegram(event: MessageCreated, context: BaseContext) -> None:
    raw = (event.message.body.text or "").strip()
    if raw != "-":
        ok, tg = validators.validate_telegram(raw)
        if not ok:
            await event.message.answer(validators.TELEGRAM_ERROR + " Либо «-», чтобы пропустить:")
            return
        await context.update_data(contact_telegram=tg)

    data = await context.get_data()
    _, user_id = event.get_ids()
    app_id = repo.add_application(user_id, data)
    await context.clear()
    await event.message.answer(
        "✅ Спасибо! Ваша заявка на проект отправлена администраторам.")
    await notify_admins(
        text=(f"📥 Новая заявка на проект (#{app_id})\n\n"
              f"Проект: {data.get('project_name')}\n"
              f"Организация: {data.get('org_name')}\n"
              f"Источник: {data.get('source')}\n"
              f"Контакт: {data.get('contact_fio')} ({data.get('contact_phone')})\n\n"
              f"Полный список заявок: /apps")
    )


def _format_application(a: dict) -> str:
    """Форматирует заявку для полного просмотра."""
    lines = [
        f"📥 Заявка на проект #{a['id']}",
        "",
        f"Название проекта: {a['project_name']}",
        f"Организация: {a['org_name']}",
        f"Источник задачи: {a['source']}",
    ]
    if a.get('department'):
        lines.append(f"Кафедра: {a['department']}")
    lines.extend([
        "",
        f"Описание: {a['description']}",
        "",
        f"Целевая аудитория: {a['target_audience']}",
        f"Количество благополучателей: {a['beneficiaries_count']}",
        f"Механизм действий: {a['mechanism']}",
        f"Желаемый продукт: {a['desired_product']}",
        f"Навыки студентов: {a['skills']}",
    ])
    if a.get('study_directions'):
        lines.append(f"Направления обучения: {a['study_directions']}")
    if a.get('dobro_link'):
        lines.append(f"Ссылка на Добро.РФ: {a['dobro_link']}")
    lines.extend([
        "",
        f"Период: {a['period_start']} — {a['period_end']}",
        "",
        f"Контактное лицо: {a['contact_fio']}",
        f"Телефон: {a['contact_phone']}",
    ])
    if a.get('contact_telegram'):
        lines.append(f"Telegram: {a['contact_telegram']}")
    lines.append(f"Статус: {a['status']}")
    lines.append(f"Дата подачи: {a['created_at'][:10] if a['created_at'] else '—'}")
    return "\n".join(lines)


# ── Просмотр заявок администратором ────────────────────────────────────────
@router.message_callback(CbPrefix("apps"))
async def apps_list_cb(event: MessageCallback, context: BaseContext) -> None:
    if not repo.is_admin(event.callback.user.user_id):
        await event.ack(notification="Недостаточно прав")
        return
    parts = keyboards.parse_cb(event.callback.payload)
    sub = parts[1] if len(parts) > 1 else ""

    if sub == "export":
        await event.ack(notification="Готовлю файл…")
        from maxapi.types.input_media import InputMedia
        path = reports.export_applications()
        await bot.send_message(
            user_id=event.callback.user.user_id,
            text="📊 Выгрузка заявок:",
            attachments=[InputMedia(path=str(path))],
        )
        return

    if sub == "view" and len(parts) > 2:
        app_id = int(parts[2])
        a = repo.get_application(app_id)
        if not a:
            await event.ack(notification="Заявка не найдена")
            return
        text = _format_application(dict(a))
        await event.edit(text=text, attachments=[keyboards.application_admin_actions(app_id).as_markup()])
        return

    if sub == "approve" and len(parts) > 2:
        app_id = int(parts[2])
        repo.set_application_status(app_id, "approved")
        await event.ack(notification="Заявка одобрена")
        a = repo.get_application(app_id)
        text = _format_application(dict(a))
        await event.edit(text=text, attachments=[keyboards.application_admin_actions(app_id).as_markup()])
        return

    if sub == "reject" and len(parts) > 2:
        app_id = int(parts[2])
        repo.set_application_status(app_id, "rejected")
        await event.ack(notification="Заявка отклонена")
        a = repo.get_application(app_id)
        text = _format_application(dict(a))
        await event.edit(text=text, attachments=[keyboards.application_admin_actions(app_id).as_markup()])
        return

    if sub == "convert" and len(parts) > 2:
        app_id = int(parts[2])
        app = repo.get_application(app_id)
        if not app:
            await event.ack(notification="Заявка не найдена")
            return
        repo.add_task(
            number=None,
            title=app["project_name"],
            partner_name=app["org_name"] or "",
            description=app["description"] or "",
            max_teams=1,
            education_program=None,
        )
        repo.set_application_status(app_id, "converted")
        await event.ack(notification="Проект создан")
        a = repo.get_application(app_id)
        text = _format_application(dict(a))
        await event.edit(text=text, attachments=[keyboards.application_admin_actions(app_id).as_markup()])
        return

    # Запрос поисковой строки по заявкам
    if sub == "search":
        await context.clear()
        await context.set_state(AdminSearch.applications)
        await event.edit(
            text="🔍 Введите название проекта, организацию или ФИО контакта для поиска:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    # Результаты поиска заявок
    if sub == "sresults":
        query = _last_app_query.get(event.callback.user.user_id, "")
        apps = repo.search_applications(query) if query else repo.list_applications()
        text = f"🔍 Результаты поиска «{query}»: {len(apps)}"
        await event.edit(text=text, attachments=[_apps_list_kb(apps, search_mode=True).as_markup()])
        return

    apps = repo.list_applications()
    if not apps:
        text = "Заявок пока нет."
        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="🔍 Поиск", payload="apps:search"))
        kb.row(keyboards.back_button())
        await event.edit(text=text, attachments=[kb.as_markup()])
        return

    text = "📥 Заявки на проекты:\n\nНажмите на заявку, чтобы посмотреть подробности."
    await event.edit(text=text, attachments=[_apps_list_kb(apps).as_markup()])


