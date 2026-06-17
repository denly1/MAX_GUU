"""FSM-состояния для всех пошаговых сценариев бота."""

from __future__ import annotations

from maxapi.context.state_machine import State, StatesGroup


class AskQuestion(StatesGroup):
    """«Задать свой вопрос» из раздела ЧаВо."""

    text = State()
    fio = State()
    phone = State()


class Reg(StatesGroup):
    """Регистрация (все роли)."""

    role = State()
    # общие ФИО
    last_name = State()
    first_name = State()
    patronymic = State()
    # студент
    institute = State()
    course = State()
    group = State()
    # преподаватель
    department = State()
    # соц. заказчик
    organization = State()
    # общий телефон
    phone = State()


class TaskFlow(StatesGroup):
    """Выбор социальной задачи студентом."""

    role_in_team = State()
    # лидер
    team_name = State()
    team_password = State()
    choose_task = State()
    confirm_task = State()
    # участник
    join_team = State()
    join_password = State()


class Feedback(StatesGroup):
    """Форма обратной связи."""

    text = State()


class AnswerDialog(StatesGroup):
    """Ответ администратора на вопрос/обратную связь."""

    text = State()


class TaskAdmin(StatesGroup):
    """Создание/редактирование задачи администратором."""

    title = State()
    partner = State()
    description = State()
    max_teams = State()
    program = State()
    edit_value = State()


class Mailing(StatesGroup):
    """Создание рассылки-приглашения на мероприятие."""

    text = State()


class CallReminder(StatesGroup):
    """Напоминание о созвоне для выбранной группы."""

    pick_recipients = State()
    text = State()
    link = State()


class MemeAdmin(StatesGroup):
    """Добавление/изменение мема по кодовому слову."""

    code_word = State()
    text = State()
    image = State()


class Application(StatesGroup):
    """Подача заявки на реализацию проекта (2.12)."""

    project_name = State()
    org_name = State()
    source = State()
    department = State()
    description = State()
    dobro_link = State()
    target_audience = State()
    beneficiaries_count = State()
    mechanism = State()
    desired_product = State()
    skills = State()
    study_directions = State()
    period_start = State()
    period_end = State()
    contact_fio = State()
    contact_phone = State()
    contact_telegram = State()
