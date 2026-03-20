# 🦎 FreakVPN Bot

Telegram-бот для автоматизированной продажи VPN-доступа.

## Особенности

- 🔑 Автоматическая генерация VLESS-ключей через X-UI API
- 💰 Внутренний баланс пользователя
- 🎁 Пробный период для новых пользователей
- 👥 Реферальная система с бонусами
- 🌍 Выбор сервера из нескольких локаций
- 📊 Удобная админ-панель

## Технический стек

- Python 3.10+
- Aiogram 3.x
- SQLite (с возможностью миграции на PostgreSQL)
- APScheduler для фоновых задач

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd freakvpn-bot
```

### 2. Создание виртуального окружения

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации

```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем .env файл
nano .env
```

Обязательно укажите:
- `BOT_TOKEN` — токен бота от @BotFather
- `ADMIN_IDS` — ID администраторов через запятую

### 5. Запуск бота

```bash
python bot.py
```

## Структура проекта

```
freakvpn-bot/
├── .env                    # Конфигурация (не в git)
├── .env.example            # Пример конфигурации
├── .gitignore
├── requirements.txt        # Зависимости
├── README.md
├── bot.py                  # Точка входа
├── config.py               # Конфигурация
├── database/               # Модуль БД
│   ├── db.py              # Класс для работы с БД
│   ├── models.py          # Модели и инициализация таблиц
│   └── queries.py         # Запросы к БД
├── handlers/               # Обработчики сообщений
├── keyboards/              # Клавиатуры
│   ├── reply.py           # Reply-клавиатуры
│   ├── inline.py          # Inline-клавиатуры пользователя
│   └── admin.py           # Inline-клавиатуры админа
├── services/               # Сервисы (X-UI API, scheduler)
├── middlewares/            # Middleware
│   ├── registration.py    # Авто-регистрация пользователей
│   └── throttle.py        # Защита от спама
├── utils/                  # Утилиты
│   ├── constants.py       # Текстовые константы
│   ├── helpers.py         # Вспомогательные функции
│   └── validators.py      # Валидаторы
└── logs/                   # Логи
    └── bot.log
```

## Команды бота

### Пользовательские команды

- `/start` — запуск бота, регистрация
- `/help` — справка по использованию
- `/profile` — переход в профиль
- `/key` — просмотр текущего ключа
- `/support` — контакты поддержки

### Административные команды

- `/admin` — вход в админ-панель

## База данных

### Таблицы

- `users` — пользователи бота
- `servers` — VPN-серверы
- `transactions` — история операций
- `tariffs` — тарифы
- `referrals` — реферальные связи
- `settings` — настройки бота
- `mailings` — рассылки

## Разработка

### Форматирование кода

```bash
pip install black isort

black .
isort .
```

### Проверка типов

```bash
pip install mypy
mypy .
```

## Лицензия

MIT
