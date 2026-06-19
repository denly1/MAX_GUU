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


def main():
    db_path = Path(__file__).parent / "data" / "bot.db"
    
    if not db_path.exists():
        print(f"❌ База данных не найдена: {db_path}")
        print("Сначала запустите бота для создания БД")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Очищаем таблицу
    cursor.execute("DELETE FROM admin_contacts")
    print("🗑 Очистил таблицу admin_contacts")
    
    # Загружаем контакты
    for fio, phone, telegram, photo_url in ADMIN_CONTACTS:
        cursor.execute(
            "INSERT INTO admin_contacts (fio, phone, telegram, photo_token) VALUES (?, ?, ?, ?)",
            (fio, phone, telegram, None)  # photo_token пока None, фото нужно загрузить отдельно
        )
        print(f"✅ Добавлен: {fio}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Загружено {len(ADMIN_CONTACTS)} контактов администраторов")
    print("\n⚠️ ВАЖНО: Фотографии нужно загрузить через бота:")
    print("1. Зайдите в бота как админ")
    print("2. Контакты → ⚙️ Управление контактами")
    print("3. Для каждого контакта: ✏️ → 📸 Изменить фото")
    print("4. Скачайте фото по ссылкам из ТЗ и загрузите в бота")


if __name__ == "__main__":
    main()
