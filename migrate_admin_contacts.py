"""Скрипт для загрузки контактов администраторов из texts.py в базу данных.

Запуск: python migrate_admin_contacts.py
"""

import sqlite3
from pathlib import Path

# Контакты из ТЗ
ADMIN_CONTACTS = [
    ("Алейников Никита Алексеевич", "89202948804", "@nekitosinaaa", "https://disk.yandex.ru/i/mgsgWvKjTt899Q"),
    ("Насырова Алина Викторовна", "89267622606", "@Ovwall", "https://disk.yandex.ru/i/Bi3fEH3p1R7pRg"),
    ("Попеляев Илья Александрович", "89823451111", "@popelyaevilya", "https://disk.yandex.ru/i/LsWQ3zV_eDWtag"),
    ("Попова Анастасия Александровна", "89624333569", "@stasya_18", "https://disk.yandex.ru/i/j2xfaZcAe_K4_A"),
    ("Пушенко Кристина Станиславовна", "89260802868", "@pushenkins", "https://disk.yandex.ru/i/0IH6XlQNUPrrAQ"),
    ("Усердная Мария Ильинична", "89100827862", "@qwmusz", "https://disk.yandex.ru/i/DsT8JmXqGT9vYg"),
]


def find_photo_for_admin(project_dir: Path, fio: str) -> Path | None:
    """Ищет фото администратора в папке проекта по фамилии."""
    # Берём фамилию из ФИО
    last_name = fio.split()[0].lower()
    
    # Расширения фото
    extensions = [".jpg", ".jpeg", ".png", ".webp"]
    
    # Ищем файл, начинающийся с фамилии
    for ext in extensions:
        for photo_file in project_dir.rglob(f"*{last_name}*{ext}"):
            return photo_file
        # Также пробуем по имени файла без учёта регистра
        for photo_file in project_dir.iterdir():
            if photo_file.is_file() and photo_file.suffix.lower() in extensions:
                if last_name in photo_file.stem.lower():
                    return photo_file
    
    return None


def main():
    project_dir = Path(__file__).parent
    db_path = project_dir / "data" / "bot.db"
    
    if not db_path.exists():
        print(f"❌ База данных не найдена: {db_path}")
        print("Сначала запустите бота для создания БД")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Добавляем колонку photo_token если её нет (для старых БД)
    try:
        cursor.execute("ALTER TABLE admin_contacts ADD COLUMN photo_token TEXT")
        print("✅ Добавлена колонка photo_token")
    except sqlite3.OperationalError:
        print("ℹ️ Колонка photo_token уже существует")
    
    # Очищаем таблицу
    cursor.execute("DELETE FROM admin_contacts")
    print("🗑 Очистил таблицу admin_contacts")
    
    # Загружаем контакты
    photos_found = 0
    for fio, phone, telegram, _ in ADMIN_CONTACTS:
        # Ищем фото в проекте
        photo_path = find_photo_for_admin(project_dir, fio)
        photo_url = str(photo_path) if photo_path else None
        
        cursor.execute(
            "INSERT INTO admin_contacts (fio, phone, telegram, photo_url, photo_token) VALUES (?, ?, ?, ?, ?)",
            (fio, phone, telegram, photo_url, None)
        )
        
        if photo_path:
            print(f"✅ Добавлен: {fio} (фото: {photo_path.name})")
            photos_found += 1
        else:
            print(f"✅ Добавлен: {fio} (фото не найдено)")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Загружено {len(ADMIN_CONTACTS)} контактов администраторов")
    print(f"📸 Найдено фото: {photos_found} из {len(ADMIN_CONTACTS)}")
    
    if photos_found < len(ADMIN_CONTACTS):
        print("\n⚠️ Для контактов без фото загрузите фото вручную через бота:")
        print("Контакты → ⚙️ Управление контактами → ✏️ → 📸 Изменить фото")


if __name__ == "__main__":
    main()
