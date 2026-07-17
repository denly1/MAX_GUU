"""Статистика программы для администраторов."""

from __future__ import annotations

from maxapi.dispatcher import Router
from maxapi.types.updates.message_callback import MessageCallback

from .. import keyboards, repo
from ..common_ui import require_role
from ..filters import CbPrefix

router = Router(router_id="statistics")


@router.message_callback(CbPrefix("stats"))
async def stats_cb(event: MessageCallback) -> None:
    """Показывает статистику программы."""
    user_id = event.callback.user.user_id
    
    if not require_role(user_id, "admin"):
        await event.ack(notification="Доступно только администраторам")
        return
    
    # Получаем статистику
    stats = repo.get_statistics()
    
    text = (
        "📊 Статистика программы «Обучение служением»\n\n"
        
        "👥 Пользователи:\n"
        f"├─ Всего: {stats['total_users']}\n"
        f"├─ 🎓 Студентов: {stats['students']}\n"
        f"├─ 👨‍🏫 Преподавателей: {stats['teachers']}\n"
        f"├─ 🤝 Партнёров: {stats['partners']}\n"
        f"├─ ⚙️ Администраторов: {stats['admins']}\n"
        f"└─ ⏳ На верификации: {stats['pending']}\n\n"
        
        "🗂 Проекты:\n"
        f"├─ Всего задач: {stats['total_tasks']}\n"
        f"├─ ✅ Активных: {stats['active_tasks']}\n"
        f"└─ 🔴 Скрытых: {stats['inactive_tasks']}\n\n"
        
        "👥 Команды:\n"
        f"├─ Всего команд: {stats['total_teams']}\n"
        f"├─ Участников: {stats['team_members']}\n"
        f"└─ Средний размер: {stats['avg_team_size']}\n\n"
        
        "💬 Активность:\n"
        f"├─ Вопросов от пользователей: {stats['questions']}\n"
        f"├─ Обратной связи: {stats['feedback']}\n"
        f"├─ Заявок на проекты: {stats['applications']}\n"
        f"└─ Мемов: {stats['memes']}\n\n"
        
        f"📅 Последнее обновление: сейчас"
    )
    
    kb = keyboards.InlineKeyboardBuilder()
    kb.row(keyboards.CallbackButton(text="🔄 Обновить", payload="stats"))
    kb.row(keyboards.back_button())
    
    await event.edit(text=text, attachments=[kb.as_markup()])
