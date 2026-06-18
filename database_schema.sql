-- База данных для MAX GUU Bot (PostgreSQL)

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    chat_id BIGINT,
    name TEXT,
    role TEXT DEFAULT 'student',
    status TEXT DEFAULT 'pending',
    last_name TEXT,
    first_name TEXT,
    patronymic TEXT,
    phone TEXT,
    institute TEXT,
    course TEXT,
    group_name TEXT,
    department TEXT,
    organization TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FAQ
CREATE TABLE IF NOT EXISTS faq (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
);

-- Контакты администраторов
CREATE TABLE IF NOT EXISTS admin_contacts (
    id SERIAL PRIMARY KEY,
    fio TEXT NOT NULL,
    phone TEXT NOT NULL,
    telegram TEXT,
    photo_url TEXT,
    photo_token TEXT
);

-- Вопросы пользователей
CREATE TABLE IF NOT EXISTS user_questions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    question_text TEXT NOT NULL,
    fio TEXT NOT NULL,
    phone TEXT NOT NULL,
    answer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Обратная связь
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    text TEXT NOT NULL,
    answer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Задачи/проекты
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    partner_name TEXT NOT NULL,
    description TEXT NOT NULL,
    max_teams INTEGER NOT NULL,
    program TEXT,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Команды студентов
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    task_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Участники команд
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id)
);

-- События (рассылки, созвоны)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    text TEXT NOT NULL,
    link TEXT,
    admin_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ответы на события
CREATE TABLE IF NOT EXISTS event_recipients (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    response TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    UNIQUE(event_id, user_id)
);

-- Мемы
CREATE TABLE IF NOT EXISTS memes (
    code_word TEXT PRIMARY KEY,
    text TEXT,
    image_token TEXT
);

-- Заявки на проекты
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    project_name TEXT NOT NULL,
    source TEXT NOT NULL,
    org_name TEXT,
    department TEXT,
    description TEXT NOT NULL,
    dobro_link TEXT,
    target_audience TEXT NOT NULL,
    beneficiaries TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    product TEXT NOT NULL,
    skills TEXT NOT NULL,
    directions TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    contact_fio TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    contact_telegram TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_tasks_active ON tasks(active);
CREATE INDEX IF NOT EXISTS idx_events_admin ON events(admin_id);

-- Начальные данные FAQ
INSERT INTO faq (question, answer) VALUES
('Что такое «Обучение служением»?', 'Это программа, в рамках которой студенты ГУУ реализуют социально значимые проекты в партнерстве с некоммерческими организациями и бизнесом. Вы получаете реальный опыт работы над проектами, которые помогают обществу.'),
('Как выбрать проект?', 'Зайдите в раздел «Выбор задачи», создайте команду (если вы лидер) или присоединитесь к существующей команде. После этого лидер команды сможет выбрать проект из доступных задач.'),
('Сколько человек должно быть в команде?', 'Команда может состоять из любого количества участников, но рекомендуется 3-5 человек для эффективной работы над проектом.'),
('Что делать, если я забыл пароль от команды?', 'Обратитесь к лидеру команды или к администраторам программы через раздел «Контакты администраторов».'),
('Как получить помощь по проекту?', 'Вы можете задать вопрос через раздел «Задать вопрос» или связаться с администраторами напрямую через раздел «Контакты администраторов».')
ON CONFLICT DO NOTHING;

-- Начальные контакты администраторов
INSERT INTO admin_contacts (fio, phone, telegram, photo_url) VALUES
('Иванов Иван Иванович', '+7 (999) 123-45-67', '@admin_ivanov', 'https://example.com/photo1.jpg'),
('Петрова Мария Сергеевна', '+7 (999) 765-43-21', '@admin_petrova', 'https://example.com/photo2.jpg')
ON CONFLICT DO NOTHING;

-- Начальные мемы
INSERT INTO memes (code_word, text, image_token) VALUES
('привет', 'Привет! 👋 Рады видеть тебя!', NULL),
('удачи', 'Удачи в проектах! 🍀 У вас всё получится!', NULL),
('спасибо', 'Пожалуйста! 😊 Всегда рады помочь!', NULL)
ON CONFLICT (code_word) DO NOTHING;
