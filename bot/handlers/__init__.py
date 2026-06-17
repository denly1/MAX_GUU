"""Пакет обработчиков. Экспортирует список роутеров для подключения."""

from __future__ import annotations

from .applications import router as applications_router
from .common import router as common_router
from .faq import router as faq_router
from .feedback import router as feedback_router
from .mailings import router as mailings_router
from .memes import router as memes_router
from .registration import router as registration_router
from .task_admin import router as task_admin_router
from .tasks import router as tasks_router
from .verification import router as verification_router

# Порядок важен: специфичные роутеры раньше общего fallback.
# memes_router содержит «ловушку» на любой текст (кодовые слова), поэтому
# обязан быть ПОСЛЕДНИМ — иначе перехватит команды и ввод FSM других модулей.
all_routers = [
    common_router,
    registration_router,
    faq_router,
    verification_router,
    tasks_router,
    task_admin_router,
    mailings_router,
    feedback_router,
    applications_router,
    memes_router,
]
