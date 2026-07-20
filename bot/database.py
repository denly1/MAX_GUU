"""Слой работы с SQLite: подключение, схема и первичное наполнение.

Используется синхронный sqlite3 — запросы локальные и быстрые, а нагрузка
бота невелика (лимит MAX — 30 rps), поэтому отдельный асинхронный драйвер
избыточен.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from . import config
from .texts import ADMIN_CONTACTS, FAQ_ITEMS

_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    """Возвращает singleton-подключение к БД."""
    global _conn
    if _conn is None:
        config.ensure_dirs()
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id      INTEGER PRIMARY KEY,
    chat_id      INTEGER,
    role         TEXT,
    status       TEXT DEFAULT 'pending',
    last_name    TEXT,
    first_name   TEXT,
    patronymic   TEXT,
    institute    TEXT,
    course       TEXT,
    education_program TEXT,
    group_name   TEXT,
    department   TEXT,
    organization TEXT,
    phone        TEXT,
    display_name TEXT,
    was_admin         INTEGER DEFAULT 0,
    teacher_programs  TEXT,
    created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS faq (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    position  INTEGER,
    question  TEXT,
    answer    TEXT
);

CREATE TABLE IF NOT EXISTS admin_contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fio         TEXT,
    phone       TEXT,
    telegram    TEXT,
    photo_url   TEXT,
    photo_token TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    number            INTEGER,
    title             TEXT,
    partner_name      TEXT,
    description       TEXT,
    max_teams         INTEGER DEFAULT 1,
    education_program TEXT,
    active            INTEGER DEFAULT 1,
    created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS teams (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT,
    password   TEXT,
    leader_id  INTEGER,
    task_id    INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS team_members (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id      INTEGER,
    user_id      INTEGER,
    role_in_team TEXT,
    UNIQUE(team_id, user_id)
);

CREATE TABLE IF NOT EXISTS user_questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER,
    question_text TEXT,
    fio           TEXT,
    phone         TEXT,
    status        TEXT DEFAULT 'new',
    answer        TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    text       TEXT,
    answer     TEXT,
    status     TEXT DEFAULT 'new',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT,
    text       TEXT,
    link       TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS event_recipients (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id  INTEGER,
    user_id   INTEGER,
    response  TEXT,
    UNIQUE(event_id, user_id)
);

CREATE TABLE IF NOT EXISTS memes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    code_word  TEXT UNIQUE,
    text       TEXT,
    image_path TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER,
    project_name       TEXT,
    org_name           TEXT,
    source             TEXT,
    department         TEXT,
    description        TEXT,
    dobro_link         TEXT,
    target_audience    TEXT,
    beneficiaries_count TEXT,
    mechanism          TEXT,
    desired_product    TEXT,
    skills             TEXT,
    study_directions   TEXT,
    period_start       TEXT,
    period_end         TEXT,
    contact_fio        TEXT,
    contact_phone      TEXT,
    contact_telegram   TEXT,
    status             TEXT DEFAULT 'new',
    created_at         TEXT DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    """Создаёт таблицы и наполняет справочники, если они пусты."""
    conn = get_conn()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    _seed(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Добавляет колонки в существующие таблицы (безопасно)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "teacher_programs" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN teacher_programs TEXT")
    if "was_admin" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN was_admin INTEGER DEFAULT 0")
    if "education_program" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN education_program TEXT")
    conn.commit()


def _seed(conn: sqlite3.Connection) -> None:
    # FAQ
    if conn.execute("SELECT COUNT(*) FROM faq").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO faq (position, question, answer) VALUES (?, ?, ?)",
            [(i, q, a) for i, (q, a) in enumerate(FAQ_ITEMS)],
        )

    # Контакты администраторов
    if conn.execute("SELECT COUNT(*) FROM admin_contacts").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO admin_contacts (fio, phone, telegram, photo_url) "
            "VALUES (?, ?, ?, ?)",
            ADMIN_CONTACTS,
        )

    # Дефолтный мем-пример (код можно поменять через админ-меню)
    if conn.execute("SELECT COUNT(*) FROM memes").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO memes (code_word, text, image_path) VALUES (?, ?, ?)",
            ("служение", "Обучение служением — это сила! 💙", None),
        )

    conn.commit()
