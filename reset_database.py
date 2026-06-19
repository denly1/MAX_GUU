"""Полная очистка базы данных бота (остаются только таблицы и админ-контакты)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def main() -> None:
    project_dir = Path(__file__).parent
    db_path = project_dir / "data" / "bot.db"

    if not db_path.exists():
        print(f"База данных не найдена: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Очищаем таблицы с пользовательскими данными
    tables_to_clear = [
        "users",
        "teams",
        "team_members",
        "applications",
        "feedback",
        "questions",
        "events",
        "memes",
    ]

    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Очищена таблица: {table}")
        except sqlite3.OperationalError as e:
            print(f"Таблица {table} не найдена или ошибка: {e}")

    # Сбрасываем автоинкремент
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ({})".format(
        ",".join("?" for _ in tables_to_clear)
    ), tables_to_clear)

    conn.commit()
    conn.close()

    print("\nБаза данных очищена. Пользователи и их данные удалены.")
    print("Контакты администраторов и FAQ остаются в таблицах admin_contacts и faq.")


if __name__ == "__main__":
    main()
