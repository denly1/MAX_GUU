"""Регистрация пользователей (студент / преподаватель / соц. заказчик)."""

from __future__ import annotations

from maxapi import F
from maxapi.context.base import BaseContext
from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from .. import keyboards, repo, texts, validators
from ..common_ui import send_main_menu
from ..filters import CbPrefix
from ..states import Reg

router = Router(router_id="registration")


@router.message_callback(CbPrefix("reg"))
async def reg_cb(event: MessageCallback, context: BaseContext) -> None:
    parts = keyboards.parse_cb(event.callback.payload)
    user_id = event.callback.user.user_id

    # reg:start — приветствие + выбор роли
    if len(parts) == 2 and parts[1] == "start":
        # Если пользователь уже зарегистрирован и подтверждён — показываем меню
        if repo.is_verified(user_id):
            await event.ack(notification="Вы уже зарегистрированы")
            await send_main_menu(user_id)
            return
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
        await context.set_state(Reg.study_program)
        await event.edit(
            text=f"Курс: {parts[2]}\n\nУкажите ваше направление подготовки:",
            attachments=[keyboards.study_program_select(1).as_markup()],
        )
        return

    # reg:sp:<page> — пагинация по направлениям
    if len(parts) == 3 and parts[1] == "sp" and parts[2].isdigit():
        page = int(parts[2])
        await event.edit(
            text="Укажите ваше направление подготовки:",
            attachments=[keyboards.study_program_select(page).as_markup()],
        )
        return

    # reg:prog:<idx> — выбор направления студента
    if len(parts) == 3 and parts[1] == "prog":
        idx = int(parts[2])
        program = texts.STUDY_PROGRAMS[idx]
        await context.update_data(education_program=program)
        await context.set_state(Reg.group)
        await event.edit(
            text=f"Направление: {program}\n\nУкажите номер вашей группы (цифра от 1 до 10):",
            attachments=[keyboards.cancel_kb().as_markup()],
        )
        return

    # reg:dep:<idx> — выбор кафедры преподавателя
    if len(parts) == 3 and parts[1] == "dep":
        idx = int(parts[2])
        dep = texts.DEPARTMENTS[idx]
        await context.update_data(department=dep)
        await context.set_state(Reg.teacher_programs)
        data = await context.get_data()
        selected = data.get("selected_prog_ids", [])
        await event.edit(
            text=f"Кафедра: {dep}\n\nУкажите образовательные программы, студентов которых вы будете курировать:\n(можно выбрать несколько)",
            attachments=[keyboards.teacher_programs_select(1, selected).as_markup()],
        )
        return

    # reg:dp:<page> — пагинация кафедр
    if len(parts) == 3 and parts[1] == "dp" and parts[2].isdigit():
        await event.edit(
            text="Укажите вашу кафедру:",
            attachments=[keyboards.department_select(int(parts[2])).as_markup()],
        )
        return

    # reg:tprog:<idx> — тоггл программы преподавателя
    if len(parts) == 3 and parts[1] == "tprog":
        idx = int(parts[2])
        data = await context.get_data()
        selected = list(data.get("selected_prog_ids", []))
        if idx in selected:
            selected.remove(idx)
        else:
            selected.append(idx)
        await context.update_data(selected_prog_ids=selected)
        dep = data.get("department", "")
        await event.edit(
            text=f"Кафедра: {dep}\n\nВыбрано: {len(selected)} программ\nПродолжайте выбирать или нажмите «Готово»:",
            attachments=[keyboards.teacher_programs_select(1, selected).as_markup()],
        )
        return

    # reg:tpp:<page> — пагинация программ преподавателя
    if len(parts) == 3 and parts[1] == "tpp" and parts[2].isdigit():
        data = await context.get_data()
        selected = data.get("selected_prog_ids", [])
        dep = data.get("department", "")
        await event.edit(
            text=f"Кафедра: {dep}\n\nВыбрано: {len(selected)} программ\nПродолжайте выбирать:",
            attachments=[keyboards.teacher_programs_select(int(parts[2]), selected).as_markup()],
        )
        return

    # reg:tpdone — подтверждение выбора программ
    if len(parts) == 2 and parts[1] == "tpdone":
        data = await context.get_data()
        selected = data.get("selected_prog_ids", [])
        programs_str = ",".join(str(i) for i in selected)
        await context.update_data(teacher_programs=programs_str)
        await context.set_state(Reg.phone)
        names = [texts.STUDY_PROGRAMS[i] for i in selected if i < len(texts.STUDY_PROGRAMS)]
        await event.edit(
            text=f"Выбрано программ: {len(names)}\n\nУкажите ваш номер телефона в формате 8 ххх-ххх хх хх:",
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
        await event.message.answer(
            "Укажите вашу кафедру:",
            attachments=[keyboards.department_select(1).as_markup()],
        )
    elif role == "partner":
        await context.set_state(Reg.organization)
        await event.message.answer(
            "Укажите полное юридическое название организации, которую вы представляете:"
        )


# ── Студент: группа ────────────────────────────────────────────────────────
@router.message_created(Reg.group, F.message.body.text)
async def reg_group(event: MessageCreated, context: BaseContext) -> None:
    raw = (event.message.body.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 10):
        await event.message.answer("Номер группы — цифра от 1 до 10. Попробуйте ещё раз:")
        return
    await context.update_data(group_name=raw)
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
            education_program=data.get("education_program"),
            group_name=data.get("group_name"),
        )
    elif role == "teacher":
        fields.update(
            department=data.get("department"),
            teacher_programs=data.get("teacher_programs"),
        )
    elif role == "partner":
        fields.update(organization=data.get("organization"))

    repo.save_registration(user_id, role, fields, status="verified")
    await context.clear()
    await event.message.answer(texts.REGISTRATION_DONE)
    await send_main_menu(user_id)

