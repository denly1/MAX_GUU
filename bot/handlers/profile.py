"""Профиль пользователя."""

from __future__ import annotations

from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback

from .. import keyboards, repo
from ..filters import CbPrefix

router = Router(router_id="profile")


@router.message_callback(CbPrefix("profile"))
async def profile_cb(event: MessageCallback) -> None:
    """Показывает профиль пользователя."""
    user_id = event.callback.user.user_id
    user = repo.get_user(user_id)
    
    if not user or not user["role"]:
        await event.edit(
            text="❌ Вы не зарегистрированы в системе.",
            attachments=[keyboards.back_button().as_markup()],
        )
        return
    
    # Формируем текст профиля
    role_labels = {
        'student': '🎓 Студент',
        'teacher': '👨‍🏫 Преподаватель',
        'partner': '🤝 Социальный партнёр',
        'admin': '⚙️ Администратор'
    }
    
    status_labels = {
        'pending': '⏳ На верификации',
        'verified': '✅ Подтверждён',
        'rejected': '❌ Отклонён'
    }
    
    text = f"👤 **Мой профиль**\n\n"
    text += f"**Роль:** {role_labels.get(user['role'], user['role'])}\n"
    text += f"**Статус:** {status_labels.get(user['status'], user['status'])}\n\n"
    
    # ФИО
    fio_parts = [user['last_name'], user['first_name'], user['patronymic']]
    fio = " ".join(p for p in fio_parts if p)
    if fio:
        text += f"**ФИО:** {fio}\n"
    
    # Телефон
    if user['phone']:
        text += f"**Телефон:** {user['phone']}\n"
    
    # Специфичные поля для студента
    if user['role'] == 'student':
        text += f"\n📚 **Учёба:**\n"
        if user['institute']:
            text += f"Институт: {user['institute']}\n"
        if user['course']:
            text += f"Курс: {user['course']}\n"
        if user['group_name']:
            text += f"Группа: {user['group_name']}\n"
        
        # Статистика студента
        teams = repo.get_user_teams(user_id)
        if teams:
            text += f"\n👥 **Мои команды:** {len(teams)}\n"
            for team in teams:
                task = repo.get_task(team['task_id']) if team['task_id'] else None
                role_icon = "👑" if team['leader_id'] == user_id else "👤"
                text += f"{role_icon} {team['name']}"
                if task:
                    text += f" — {task['title']}"
                text += "\n"
    
    # Специфичные поля для преподавателя
    elif user['role'] == 'teacher':
        if user['department']:
            text += f"\n🏛 **Кафедра:** {user['department']}\n"
    
    # Специфичные поля для партнёра
    elif user['role'] == 'partner':
        if user['organization']:
            text += f"\n🏢 **Организация:** {user['organization']}\n"
    
    # Дата регистрации
    if user['created_at']:
        text += f"\n📅 **Регистрация:** {user['created_at'][:10]}\n"
    
    kb = keyboards.InlineKeyboardBuilder()
    kb.row(keyboards.back_button())
    
    await event.edit(text=text, attachments=[kb.as_markup()])
