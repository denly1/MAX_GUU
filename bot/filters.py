"""Кастомные фильтры для маршрутизации callback-нажатий по префиксу payload."""

from __future__ import annotations

from maxapi.filters.filter import BaseFilter


class CbPrefix(BaseFilter):
    """Пропускает callback, payload которого начинается с одного из префиксов.

    Префикс сравнивается по сегментам, разделённым ':'. Например, префикс
    ``"task"`` совпадёт с ``task``, ``task:menu``, ``task:open:5``.
    """

    def __init__(self, *prefixes: str) -> None:
        self.prefixes = prefixes

    async def __call__(self, event) -> bool:  # noqa: ANN001
        callback = getattr(event, "callback", None)
        if callback is None:
            return False
        payload = callback.payload or ""
        first = payload.split(":", 1)[0]
        return first in self.prefixes
