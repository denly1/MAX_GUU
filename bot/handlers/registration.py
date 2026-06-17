"""Регистрация пользователей (студент / преподаватель / соц. заказчик)."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, repo, texts, validators
from ..common_ui import notify_admins, send_main_menu
from ..filters import CbPrefix
from ..states import Reg

router = Router(router_id="registration")


@router.message_callback(CbPrefix("reg"))
async def reg_cb(event: MessageCallback, context: BaseContext) -> None:
    parts = keyboards.parse_cb(event.callback.payload)
    user_id = event.callback.user.user_id

    # reg:start — приветствие + выбор роли
    if len(parts) == 2 and parts[1] == "start":
        await context.clear()
        await context.set_state(Reg.role)
        await event.edit(
            text=texts.WELCOME_TEXT + "\n\nПожалуйста, выберите свою роль:",
            attachments=[keyboards.role_select().as_markup()],
        )
        return

    # reg:role:<role>
    if len(parts) == 3 and parts[1] == "role":
        role = parts[2]
        await context.update_data(role=role)
        await context.set_state(Reg.last_name)
        await event.edit(
            text=f"Роль: {texts.ROLE_LABELS.get(role, role)}\n\nУкажите вашу фамилию:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    # reg:inst:<institute>
    if len(parts) == 3 and parts[1] == "inst":
        await context.update_data(institute=parts[2])
        await context.set_state(Reg.course)
        await event.edit(
            text=f"Институт: {parts[2]}\n\nУкажите ваш курс:",
            attachments=[keyboards.course_select().as_markup()],
        )
        return

    # reg:course:<course>
    if len(parts) == 3 and parts[1] == "course":
        await context.update_data(course=parts[2])
        await context.set_state(Reg.group)
        await event.edit(
            text=f"Курс: {parts[2]}\n\nУкажите группу в формате «РиССовБ 1-1»:",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return


# ── ФИО (общие шаги) ───────────────────────────────────────────────────────
@router.message_created(Reg.last_name, F.message.body.text)
async def reg_last_name(event: MessageCreated, context: BaseContext) -> None:
    ok, value = validators.validate_name(event.message.body.text or "")
    if not ok:
        await event.message.answer(validators.name_error("фамилию"))
        return
    await context.update_data(last_name=value)
    await context.set_state(Reg.first_name)
    await event.message.answer("Укажите ваше имя:")


@router.message_created(Reg.first_name, F.message.body.text)
async def reg_first_name(event: MessageCreated, context: BaseContext) -> None:
    ok, value = validators.validate_name(event.message.body.text or "")
    if not ok:
        await event.message.answer(validators.name_error("имя"))
        return
    await context.update_data(first_name=value)
    await context.set_state(Reg.patronymic)
    await event.message.answer("Укажите ваше отчество:")


@router.message_created(Reg.patronymic, F.message.body.text)
async def reg_patronymic(event: MessageCreated, context: BaseContext) -> None:
    ok, value = validators.validate_name(event.message.body.text or "")
    if not ok:
        await event.message.answer(validators.name_error("отчество"))
        return
    await context.update_data(patronymic=value)
    data = await context.get_data()
    role = data.get("role")

    if role == "student":
        await context.set_state(Reg.institute)
        await event.message.answer(
            "Укажите ваш институт:",
            attachments=[keyboards.institute_select().as_markup()],
        )
    elif role == "teacher":
        await context.set_state(Reg.department)
        await event.message.answer("Укажите вашу кафедру:")
    elif role == "partner":
        await context.set_state(Reg.organization)
        await event.message.answer(
            "Укажите полное юридическое название организации, которую вы представляете:"
        )


# ── Студент: группа ────────────────────────────────────────────────────────
@router.message_created(Reg.group, F.message.body.text)
async def reg_group(event: MessageCreated, context: BaseContext) -> None:
    group = (event.message.body.text or "").strip()
    if not group:
        await event.message.answer("Группа не может быть пустой. Попробуйте ещё раз:")
        return
    await context.update_data(group_name=group)
    await context.set_state(Reg.phone)
    await event.message.answer("Укажите ваш номер телефона в формате 8 ххх-ххх хх хх:")


# ── Преподаватель: кафедра ─────────────────────────────────────────────────
@router.message_created(Reg.department, F.message.body.text)
async def reg_department(event: MessageCreated, context: BaseContext) -> None:
    dep = (event.message.body.text or "").strip()
    if not dep:
        await event.message.answer("Кафедра не может быть пустой. Попробуйте ещё раз:")
        return
    await context.update_data(department=dep)
    await context.set_state(Reg.phone)
    await event.message.answer("Укажите ваш номер телефона в формате 8 ххх-ххх хх хх:")


# ── Соц. заказчик: организация ─────────────────────────────────────────────
@router.message_created(Reg.organization, F.message.body.text)
async def reg_organization(event: MessageCreated, context: BaseContext) -> None:
    org = (event.message.body.text or "").strip()
    if not org:
        await event.message.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    await context.update_data(organization=org)
    await context.set_state(Reg.phone)
    await event.message.answer("Укажите ваш номер телефона в формате 8 ххх-ххх хх хх:")


# ── Телефон + сохранение ───────────────────────────────────────────────────
@router.message_created(Reg.phone, F.message.body.text)
async def reg_phone(event: MessageCreated, context: BaseContext) -> None:
    ok, phone = validators.validate_phone(event.message.body.text or "")
    if not ok:
        await event.message.answer(validators.PHONE_ERROR)
        return

    data = await context.get_data()
    role = data.get("role")
    _, user_id = event.get_ids()

    fields: dict = {
        "last_name": data.get("last_name"),
        "first_name": data.get("first_name"),
        "patronymic": data.get("patronymic"),
        "phone": phone,
    }
    if role == "student":
        fields.update(
            institute=data.get("institute"),
            course=data.get("course"),
            group_name=data.get("group_name"),
        )
    elif role == "teacher":
        fields.update(department=data.get("department"))
    elif role == "partner":
        fields.update(organization=data.get("organization"))

    repo.save_registration(user_id, role, fields, status="pending")
    await context.clear()

    await event.message.answer(texts.REGISTRATION_DONE)

    # Уведомление администраторам с кнопками верификации.
    fio = " ".join(filter(None, [fields["last_name"], fields["first_name"],
                                 fields["patronymic"]]))
    extra = ""
    if role == "student":
        extra = (f"Институт: {fields['institute']}, курс {fields['course']}, "
                 f"группа {fields['group_name']}")
    elif role == "teacher":
        extra = f"Кафедра: {fields['department']}"
    elif role == "partner":
        extra = f"Организация: {fields['organization']}"

    await notify_admins(
        text=(
            f"🆕 Новая регистрация на подтверждение\n\n"
            f"Роль: {texts.ROLE_LABELS.get(role, role)}\n"
            f"ФИО: {fio}\n{extra}\n"
            f"Телефон: {phone}"
        ),
        attachments=[keyboards.verify_actions(user_id).as_markup()],
    )
