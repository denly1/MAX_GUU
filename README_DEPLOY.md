# 🚀 Деплой MAX GUU Bot на сервер

## 📋 Данные сервера

- **IP:** 186.246.11.208
- **User:** root
- **Password:** ba+N.M+68gPu4G
- **БД:** max_guu
- **DB User:** postgres
- **DB Password:** 1
- **DB Port:** 5432

---

## 1️⃣ Подготовка на локальной машине

```bash
cd c:\Users\User\Desktop\MAX_GUU

# Инициализация git (если еще не сделано)
git init
git add .
git commit -m "Initial commit: MAX GUU Bot"

# Подключение к GitHub
git remote add origin https://github.com/denly1/MAX_GUU.git
git branch -M main

# Пуш в GitHub
git push -u origin main
```

---

## 2️⃣ Настройка GitHub Secrets

Перейдите: https://github.com/denly1/MAX_GUU/settings/secrets/actions

Добавьте секреты:
- **Name:** `SERVER_HOST` | **Value:** `186.246.11.208`
- **Name:** `SERVER_USER` | **Value:** `root`
- **Name:** `SERVER_PASSWORD` | **Value:** `ba+N.M+68gPu4G`

---

## 3️⃣ Подключение к серверу

```bash
ssh root@186.246.11.208
# Пароль: ba+N.M+68gPu4G
```

---

## 4️⃣ Установка зависимостей на сервере

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка необходимых пакетов
apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib

# Проверка версий
python3 --version
psql --version
```

---

## 5️⃣ Настройка PostgreSQL

```bash
# Войти в PostgreSQL
sudo -u postgres psql

# Создать базу данных и пользователя
CREATE DATABASE max_guu;
ALTER USER postgres WITH PASSWORD '1';
GRANT ALL PRIVILEGES ON DATABASE max_guu TO postgres;

# Выход
\q
```

---

## 6️⃣ Клонирование проекта

```bash
# Создать директорию
mkdir -p /opt/MAX_GUU
cd /opt/MAX_GUU

# Клонировать репозиторий
git clone https://github.com/denly1/MAX_GUU.git .

# Проверить файлы
ls -la
```

---

## 7️⃣ Импорт схемы базы данных

```bash
# Импортировать схему
sudo -u postgres psql -d max_guu -f database_schema.sql

# Проверить таблицы
sudo -u postgres psql -d max_guu -c "\dt"
```

---

## 8️⃣ Настройка Python окружения

```bash
# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate

# Установить зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Проверить установку
pip list | grep maxapi
```

---

## 9️⃣ Создание .env файла

```bash
nano .env
```

**Вставьте:**
```env
MAX_BOT_TOKEN=f9LHodD0cOLJNwcoW5R0bGwoZExUjHFcbk_3BD-igXj9cV-Ijg6nX6AK3fJPnBqs0OyaEd0GQZ6kNXBxxFb0
ADMIN_IDS=ваш_user_id_из_команды_/id
DB_PATH=data/bot.db
```

**Сохранить:** `Ctrl+O` → `Enter` → `Ctrl+X`

---

## 🔟 Создание директорий

```bash
mkdir -p data exports assets
chmod 755 data exports assets
```

---

## 1️⃣1️⃣ Установка systemd service

```bash
# Скопировать service файл
cp max_guu_bot.service /etc/systemd/system/

# Перезагрузить systemd
systemctl daemon-reload

# Включить автозапуск
systemctl enable max_guu_bot

# Запустить бота
systemctl start max_guu_bot

# Проверить статус
systemctl status max_guu_bot
```

---

## 1️⃣2️⃣ Проверка работы

```bash
# Просмотр логов в реальном времени
journalctl -u max_guu_bot -f

# Последние 100 строк логов
journalctl -u max_guu_bot -n 100

# Проверка статуса
systemctl status max_guu_bot
```

---

## 🔧 Управление ботом

```bash
# Перезапуск
systemctl restart max_guu_bot

# Остановка
systemctl stop max_guu_bot

# Запуск
systemctl start max_guu_bot

# Просмотр логов
journalctl -u max_guu_bot -f
```

---

## 🔄 Обновление бота с GitHub

```bash
cd /opt/MAX_GUU
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart max_guu_bot
```

---

## 🤖 GitHub Actions (Автодеплой)

После настройки секретов, каждый `git push` в ветку `main` автоматически:
1. Подключается к серверу
2. Обновляет код (`git pull`)
3. Устанавливает зависимости
4. Перезапускает бота

**Проверить деплой:** https://github.com/denly1/MAX_GUU/actions

---

## 🐛 Решение проблем

### Бот не запускается
```bash
journalctl -u max_guu_bot -n 50
```

### Проблемы с БД
```bash
sudo -u postgres psql -d max_guu
\dt
SELECT * FROM users LIMIT 5;
\q
```

### Права доступа
```bash
chown -R root:root /opt/MAX_GUU
chmod -R 755 /opt/MAX_GUU
```

### Переустановка зависимостей
```bash
cd /opt/MAX_GUU
source venv/bin/activate
pip install --force-reinstall -r requirements.txt
```

---

## ✅ Готово!

Бот работает на сервере 24/7 и автоматически обновляется при каждом пуше в GitHub! 🎉
