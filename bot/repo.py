"""Функции доступа к данным (репозиторий) поверх sqlite3."""

from __future__ import annotations

import sqlite3
from typing import Any, Optional

from .database import get_conn


def _c() -> sqlite3.Connection:
    return get_conn()


# ── Пользователи ───────────────────────────────────────────────────────────
def get_user(user_id: int) -> Optional[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()


def upsert_user_contact(user_id: int, chat_id: int | None,
                        display_name: str | None = None) -> None:
    """Создаёт запись пользователя (если нет) и обновляет chat_id/имя."""
    conn = _c()
    existing = get_user(user_id)
    if existing is None:
        conn.execute(
            "INSERT INTO users (user_id, chat_id, display_name, status) "
            "VALUES (?, ?, ?, NULL)",
            (user_id, chat_id, display_name),
        )
    else:
        conn.execute(
            "UPDATE users SET chat_id = COALESCE(?, chat_id), "
            "display_name = COALESCE(?, display_name) WHERE user_id = ?",
            (chat_id, display_name, user_id),
        )
    conn.commit()


def save_registration(user_id: int, role: str, fields: dict[str, Any],
                      status: str = "pending") -> None:
    """Сохраняет данные регистрации. fields — словарь колонок users."""
    conn = _c()
    columns = ["role", "status"] + list(fields.keys())
    placeholders = ", ".join(f"{col} = ?" for col in columns)
    values = [role, status] + list(fields.values())
    conn.execute(
        f"UPDATE users SET {placeholders} WHERE user_id = ?",
        (*values, user_id),
    )
    conn.commit()


def set_user_status(user_id: int, status: str) -> None:
    conn = _c()
    conn.execute("UPDATE users SET status = ? WHERE user_id = ?",
                 (status, user_id))
    conn.commit()


def set_user_role(user_id: int, role: str, status: str = "verified") -> None:
    conn = _c()
    conn.execute("UPDATE users SET role = ?, status = ? WHERE user_id = ?",
                 (role, status, user_id))
    conn.commit()


def update_user_field(user_id: int, field: str, value: str | None) -> None:
    """Обновляет одно поле пользователя."""
    allowed_fields = {
        "last_name", "first_name", "patronymic", "phone",
        "institute", "course", "group_name", "department",
        "organization", "education_program", "teacher_programs"
    }
    if field not in allowed_fields:
        raise ValueError(f"Недопустимое поле: {field}")
    conn = _c()
    conn.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()


def set_was_admin(user_id: int, was_admin: int = 1) -> None:
    """Устанавливает флаг was_admin у пользователя."""
    conn = _c()
    conn.execute("UPDATE users SET was_admin = ? WHERE user_id = ?",
                 (was_admin, user_id))
    conn.commit()


def is_admin(user_id: int) -> bool:
    row = get_user(user_id)
    return bool(row and row["role"] == "admin" and row["status"] == "verified")


def is_verified(user_id: int) -> bool:
    row = get_user(user_id)
    return bool(row and row["status"] == "verified")


def list_admin_user_ids() -> list[int]:
    rows = _c().execute(
        "SELECT user_id FROM users WHERE role = 'admin' AND status = 'verified'"
    ).fetchall()
    return [r["user_id"] for r in rows]


def list_admins() -> list[sqlite3.Row]:
    """Возвращает всех администраторов."""
    return _c().execute(
        "SELECT * FROM users WHERE role = 'admin' AND status = 'verified' ORDER BY created_at"
    ).fetchall()


def list_all_users() -> list[sqlite3.Row]:
    """Возвращает всех пользователей с ролями."""
    return _c().execute(
        "SELECT * FROM users WHERE role IS NOT NULL ORDER BY created_at DESC"
    ).fetchall()


def search_users(query: str) -> list[sqlite3.Row]:
    """Ищет пользователей по подстроке в ФИО, имени пользователя или телефоне."""
    like = f"%{query}%"
    return _c().execute(
        "SELECT * FROM users WHERE role IS NOT NULL AND ("
        "last_name LIKE ? OR first_name LIKE ? OR patronymic LIKE ? "
        "OR display_name LIKE ? OR phone LIKE ? OR CAST(user_id AS TEXT) LIKE ?"
        ") ORDER BY created_at DESC",
        (like, like, like, like, like, like),
    ).fetchall()


def list_users_by_status(status: str) -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM users WHERE status = ? ORDER BY created_at", (status,)
    ).fetchall()


def list_all_active_users() -> list[sqlite3.Row]:
    """Верифицированные пользователи с известным chat_id/user_id."""
    return _c().execute(
        "SELECT * FROM users WHERE status = 'verified'"
    ).fetchall()


def list_students() -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM users WHERE role = 'student' AND status = 'verified'"
    ).fetchall()


def list_teachers() -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM users WHERE role = 'teacher' AND status = 'verified'"
    ).fetchall()


def list_partners() -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM users WHERE role = 'partner' AND status = 'verified'"
    ).fetchall()


def list_student_user_ids() -> list[int]:
    """Возвращает user_id всех подтверждённых студентов."""
    rows = _c().execute(
        "SELECT user_id FROM users WHERE role = 'student' AND status = 'verified'"
    ).fetchall()
    return [r[0] for r in rows]


# ── FAQ ────────────────────────────────────────────────────────────────────
def list_faq() -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM faq ORDER BY position"
    ).fetchall()


def get_faq(faq_id: int) -> Optional[sqlite3.Row]:
    return _c().execute("SELECT * FROM faq WHERE id = ?", (faq_id,)).fetchone()


def add_faq(question: str, answer: str) -> int:
    """Добавляет новый FAQ."""
    conn = _c()
    # Получаем максимальную позицию
    max_pos = conn.execute("SELECT MAX(position) FROM faq").fetchone()[0]
    position = (max_pos or 0) + 1
    
    cur = conn.execute(
        "INSERT INTO faq (question, answer, position) VALUES (?, ?, ?)",
        (question, answer, position),
    )
    conn.commit()
    return cur.lastrowid


def update_faq(faq_id: int, question: str | None = None, answer: str | None = None) -> None:
    """Обновляет существующий FAQ."""
    conn = _c()
    fields: dict[str, Any] = {}
    if question is not None:
        fields["question"] = question
    if answer is not None:
        fields["answer"] = answer
    if not fields:
        return
    placeholders = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE faq SET {placeholders} WHERE id = ?",
        (*fields.values(), faq_id),
    )
    conn.commit()


def delete_faq(faq_id: int) -> None:
    """Удаляет FAQ."""
    conn = _c()
    conn.execute("DELETE FROM faq WHERE id = ?", (faq_id,))
    conn.commit()


# ── Контакты администраторов ───────────────────────────────────────────────
def list_admin_contacts() -> list[sqlite3.Row]:
    return _c().execute("SELECT * FROM admin_contacts ORDER BY id").fetchall()


def get_admin_contact(contact_id: int) -> Optional[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM admin_contacts WHERE id = ?", (contact_id,)
    ).fetchone()


def add_admin_contact(fio: str, phone: str, telegram: str | None = None,
                      photo_token: str | None = None) -> int:
    """Добавляет новый контакт администратора."""
    conn = _c()
    cur = conn.execute(
        "INSERT INTO admin_contacts (fio, phone, telegram, photo_token) "
        "VALUES (?, ?, ?, ?)",
        (fio, phone, telegram, photo_token),
    )
    conn.commit()
    return cur.lastrowid


def update_admin_contact(contact_id: int, **fields) -> None:
    """Обновляет контакт администратора."""
    conn = _c()
    columns = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [contact_id]
    conn.execute(
        f"UPDATE admin_contacts SET {columns} WHERE id = ?",
        values,
    )
    conn.commit()


def delete_admin_contact(contact_id: int) -> None:
    """Удаляет контакт администратора."""
    conn = _c()
    conn.execute("DELETE FROM admin_contacts WHERE id = ?", (contact_id,))
    conn.commit()


# ── Вопросы пользователей («задать свой вопрос») ───────────────────────────
def add_user_question(user_id: int, question_text: str, fio: str,
                      phone: str) -> int:
    conn = _c()
    cur = conn.execute(
        "INSERT INTO user_questions (user_id, question_text, fio, phone) "
        "VALUES (?, ?, ?, ?)",
        (user_id, question_text, fio, phone),
    )
    conn.commit()
    return cur.lastrowid


def get_question(qid: int) -> Optional[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM user_questions WHERE id = ?", (qid,)
    ).fetchone()


def answer_question(qid: int, answer: str) -> None:
    conn = _c()
    conn.execute(
        "UPDATE user_questions SET answer = ?, status = 'answered' WHERE id = ?",
        (answer, qid),
    )
    conn.commit()


# ── Обратная связь ─────────────────────────────────────────────────────────
def add_feedback(user_id: int, text: str) -> int:
    conn = _c()
    cur = conn.execute(
        "INSERT INTO feedback (user_id, text) VALUES (?, ?)", (user_id, text)
    )
    conn.commit()
    return cur.lastrowid


def get_feedback(fid: int) -> Optional[sqlite3.Row]:
    return _c().execute("SELECT * FROM feedback WHERE id = ?", (fid,)).fetchone()


def answer_feedback(fid: int, answer: str) -> None:
    conn = _c()
    conn.execute(
        "UPDATE feedback SET answer = ?, status = 'answered' WHERE id = ?",
        (answer, fid),
    )
    conn.commit()


# ── Задачи ─────────────────────────────────────────────────────────────────
def add_task(number: int | None, title: str, partner_name: str,
             description: str, max_teams: int,
             education_program: str | None = None) -> int:
    conn = _c()
    cur = conn.execute(
        "INSERT INTO tasks (number, title, partner_name, description, "
        "max_teams, education_program) VALUES (?, ?, ?, ?, ?, ?)",
        (number, title, partner_name, description, max_teams, education_program),
    )
    conn.commit()
    return cur.lastrowid


def get_task(task_id: int) -> Optional[sqlite3.Row]:
    return _c().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def search_tasks(query: str) -> list[sqlite3.Row]:
    """Ищет задачи по подстроке в названии, партнёре или описании."""
    like = f"%{query}%"
    return _c().execute(
        "SELECT * FROM tasks WHERE title LIKE ? OR partner_name LIKE ? "
        "OR description LIKE ? ORDER BY id DESC",
        (like, like, like),
    ).fetchall()


def list_tasks(active_only: bool = False) -> list[sqlite3.Row]:
    q = "SELECT * FROM tasks"
    if active_only:
        q += " WHERE active = 1"
    q += " ORDER BY number, id"
    return _c().execute(q).fetchall()


def list_tasks_for_programs(programs: list[str]) -> list[sqlite3.Row]:
    """Задачи для конкретных образовательных программ (для преподавателя).
    Возвращает задачи, у которых education_program входит в список,
    либо задачи без привязки к программе.
    """
    if not programs:
        return list_tasks()
    rows = list_tasks()
    result = []
    for r in rows:
        ep = r["education_program"]
        if not ep or ep in programs:
            result.append(r)
    return result


def list_available_tasks_for_program(program: str | None) -> list[sqlite3.Row]:
    """Активные задачи с доступными слотами, отфильтрованные по программе студента."""
    rows = _c().execute(
        """
        SELECT t.*, (
            SELECT COUNT(*) FROM teams te WHERE te.task_id = t.id
        ) AS taken
        FROM tasks t
        WHERE t.active = 1
        """
    ).fetchall()
    available = [r for r in rows if r["taken"] < r["max_teams"]]
    if not program:
        return available
    return [r for r in available if not r["education_program"] or r["education_program"] == program]


def list_available_tasks() -> list[sqlite3.Row]:
    """Активные задачи, у которых ещё есть свободные слоты для команд."""
    rows = _c().execute(
        """
        SELECT t.*, (
            SELECT COUNT(*) FROM teams te WHERE te.task_id = t.id
        ) AS taken
        FROM tasks t
        WHERE t.active = 1
        """
    ).fetchall()
    return [r for r in rows if r["taken"] < r["max_teams"]]


def task_taken_count(task_id: int) -> int:
    return _c().execute(
        "SELECT COUNT(*) FROM teams WHERE task_id = ?", (task_id,)
    ).fetchone()[0]


def update_task(task_id: int, **fields: Any) -> None:
    if not fields:
        return
    conn = _c()
    placeholders = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE tasks SET {placeholders} WHERE id = ?",
        (*fields.values(), task_id),
    )
    conn.commit()


def delete_task(task_id: int) -> None:
    conn = _c()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()


# ── Команды ────────────────────────────────────────────────────────────────
def create_team(name: str, password: str, leader_id: int) -> int:
    conn = _c()
    cur = conn.execute(
        "INSERT INTO teams (name, password, leader_id) VALUES (?, ?, ?)",
        (name, password, leader_id),
    )
    team_id = cur.lastrowid
    conn.execute(
        "INSERT INTO team_members (team_id, user_id, role_in_team) "
        "VALUES (?, ?, 'leader')",
        (team_id, leader_id),
    )
    conn.commit()
    return team_id


def get_team(team_id: int) -> Optional[sqlite3.Row]:
    return _c().execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()


def get_team_by_name(name: str) -> Optional[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM teams WHERE name = ?", (name,)
    ).fetchone()


def list_teams() -> list[sqlite3.Row]:
    return _c().execute("SELECT * FROM teams ORDER BY name").fetchall()


def search_teams(query: str) -> list[sqlite3.Row]:
    """Ищет команды по подстроке названия (case-insensitive)."""
    return _c().execute(
        "SELECT * FROM teams WHERE name LIKE ? ORDER BY name",
        (f"%{query}%",),
    ).fetchall()


def get_user_team(user_id: int) -> Optional[sqlite3.Row]:
    return _c().execute(
        """
        SELECT t.*, tm.role_in_team AS member_role
        FROM team_members tm JOIN teams t ON t.id = tm.team_id
        WHERE tm.user_id = ?
        """,
        (user_id,),
    ).fetchone()


def get_user_teams(user_id: int) -> list[sqlite3.Row]:
    """Возвращает все команды пользователя."""
    return _c().execute(
        """
        SELECT t.*, tm.role_in_team AS member_role
        FROM team_members tm JOIN teams t ON t.id = tm.team_id
        WHERE tm.user_id = ?
        ORDER BY t.created_at DESC
        """,
        (user_id,),
    ).fetchall()


def add_team_member(team_id: int, user_id: int) -> bool:
    conn = _c()
    try:
        conn.execute(
            "INSERT INTO team_members (team_id, user_id, role_in_team) "
            "VALUES (?, ?, 'member')",
            (team_id, user_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def list_team_members(team_id: int) -> list[sqlite3.Row]:
    return _c().execute(
        """
        SELECT tm.role_in_team, u.*
        FROM team_members tm JOIN users u ON u.user_id = tm.user_id
        WHERE tm.team_id = ?
        """,
        (team_id,),
    ).fetchall()


def set_team_task(team_id: int, task_id: int) -> None:
    conn = _c()
    conn.execute("UPDATE teams SET task_id = ? WHERE id = ?", (task_id, team_id))
    conn.commit()


# ── Рассылки / события ─────────────────────────────────────────────────────
def create_event(kind: str, text: str, link: str | None,
                 created_by: int) -> int:
    conn = _c()
    cur = conn.execute(
        "INSERT INTO events (kind, text, link, created_by) VALUES (?, ?, ?, ?)",
        (kind, text, link, created_by),
    )
    conn.commit()
    return cur.lastrowid


def get_event(event_id: int) -> Optional[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()


def add_event_recipient(event_id: int, user_id: int) -> None:
    conn = _c()
    try:
        conn.execute(
            "INSERT INTO event_recipients (event_id, user_id) VALUES (?, ?)",
            (event_id, user_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass


def set_event_response(event_id: int, user_id: int, response: str) -> None:
    conn = _c()
    conn.execute(
        "UPDATE event_recipients SET response = ? "
        "WHERE event_id = ? AND user_id = ?",
        (response, event_id, user_id),
    )
    conn.commit()


def list_event_responses(event_id: int) -> list[sqlite3.Row]:
    return _c().execute(
        """
        SELECT er.response, u.*
        FROM event_recipients er JOIN users u ON u.user_id = er.user_id
        WHERE er.event_id = ?
        """,
        (event_id,),
    ).fetchall()


def list_events_by_admin(admin_id: int) -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM events WHERE created_by = ? ORDER BY id DESC",
        (admin_id,),
    ).fetchall()


# ── Мемы ───────────────────────────────────────────────────────────────────
def get_meme(code_word: str) -> Optional[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM memes WHERE lower(code_word) = lower(?)", (code_word,)
    ).fetchone()


def list_memes() -> list[sqlite3.Row]:
    return _c().execute("SELECT * FROM memes ORDER BY id").fetchall()


def upsert_meme(code_word: str, text: str, image_path: str | None) -> None:
    conn = _c()
    conn.execute(
        """
        INSERT INTO memes (code_word, text, image_path) VALUES (?, ?, ?)
        ON CONFLICT(code_word) DO UPDATE SET text = excluded.text,
            image_path = COALESCE(excluded.image_path, memes.image_path)
        """,
        (code_word, text, image_path),
    )
    conn.commit()


def delete_meme(code_word: str) -> None:
    conn = _c()
    conn.execute("DELETE FROM memes WHERE lower(code_word) = lower(?)",
                 (code_word,))
    conn.commit()


# ── Статистика ─────────────────────────────────────────────────────────────
def get_statistics() -> dict[str, int]:
    """Возвращает общую статистику программы."""
    conn = _c()
    
    # Пользователи
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE role IS NOT NULL").fetchone()[0]
    students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    teachers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'teacher'").fetchone()[0]
    partners = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'partner'").fetchone()[0]
    admins = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'").fetchone()[0]
    
    # Проекты
    total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    active_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE active = 1").fetchone()[0]
    inactive_tasks = total_tasks - active_tasks
    
    # Команды
    total_teams = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    team_members = conn.execute("SELECT COUNT(*) FROM team_members").fetchone()[0]
    avg_team_size = round(team_members / total_teams, 1) if total_teams > 0 else 0
    
    # Активность
    questions = conn.execute("SELECT COUNT(*) FROM user_questions").fetchone()[0]
    feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    applications = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    memes = conn.execute("SELECT COUNT(*) FROM memes").fetchone()[0]
    
    return {
        'total_users': total_users,
        'students': students,
        'teachers': teachers,
        'partners': partners,
        'admins': admins,
        'pending': pending,
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
        'inactive_tasks': inactive_tasks,
        'total_teams': total_teams,
        'team_members': team_members,
        'avg_team_size': avg_team_size,
        'questions': questions,
        'feedback': feedback,
        'applications': applications,
        'memes': memes,
    }


# ── Справочники (институты, кафедры, направления) ──────────────────────────
def list_institutes() -> list[str]:
    rows = _c().execute("SELECT name FROM institutes ORDER BY position, name").fetchall()
    return [r["name"] for r in rows]


def add_institute(name: str) -> None:
    conn = _c()
    pos = (conn.execute("SELECT MAX(position) FROM institutes").fetchone()[0] or 0) + 1
    conn.execute("INSERT OR IGNORE INTO institutes (name, position) VALUES (?, ?)", (name.strip(), pos))
    conn.commit()


def delete_institute(name: str) -> None:
    _c().execute("DELETE FROM institutes WHERE name = ?", (name,))
    _c().commit()


def list_departments() -> list[str]:
    rows = _c().execute("SELECT name FROM departments ORDER BY position, name").fetchall()
    return [r["name"] for r in rows]


def add_department(name: str) -> None:
    conn = _c()
    pos = (conn.execute("SELECT MAX(position) FROM departments").fetchone()[0] or 0) + 1
    conn.execute("INSERT OR IGNORE INTO departments (name, position) VALUES (?, ?)", (name.strip(), pos))
    conn.commit()


def delete_department(name: str) -> None:
    conn = _c()
    conn.execute("DELETE FROM departments WHERE name = ?", (name,))
    conn.commit()


def list_study_programs() -> list[str]:
    rows = _c().execute("SELECT name FROM study_programs ORDER BY position, name").fetchall()
    return [r["name"] for r in rows]


def add_study_program(name: str) -> None:
    conn = _c()
    pos = (conn.execute("SELECT MAX(position) FROM study_programs").fetchone()[0] or 0) + 1
    conn.execute("INSERT OR IGNORE INTO study_programs (name, position) VALUES (?, ?)", (name.strip(), pos))
    conn.commit()


def delete_study_program(name: str) -> None:
    conn = _c()
    conn.execute("DELETE FROM study_programs WHERE name = ?", (name,))
    conn.commit()


# ── Заявки на проект (2.12) ────────────────────────────────────────────────
APPLICATION_COLUMNS = [
    "project_name", "org_name", "source", "department", "description",
    "dobro_link", "target_audience", "beneficiaries_count", "mechanism",
    "desired_product", "skills", "study_directions", "period_start",
    "period_end", "contact_fio", "contact_phone", "contact_telegram",
]


def add_application(user_id: int, data: dict[str, Any]) -> int:
    conn = _c()
    cols = ["user_id"] + APPLICATION_COLUMNS
    values = [user_id] + [data.get(c) for c in APPLICATION_COLUMNS]
    placeholders = ", ".join("?" for _ in cols)
    cur = conn.execute(
        f"INSERT INTO applications ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cur.lastrowid


def get_application(app_id: int) -> Optional[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM applications WHERE id = ?", (app_id,)
    ).fetchone()


def list_applications() -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM applications ORDER BY id DESC"
    ).fetchall()


def search_applications(query: str) -> list[sqlite3.Row]:
    """Ищет заявки по подстроке в названии проекта, организации или контакте."""
    like = f"%{query}%"
    return _c().execute(
        "SELECT * FROM applications WHERE project_name LIKE ? OR org_name LIKE ? "
        "OR contact_fio LIKE ? ORDER BY id DESC",
        (like, like, like),
    ).fetchall()
