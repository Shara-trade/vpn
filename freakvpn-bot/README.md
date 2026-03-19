# FreakVPN Bot

Telegram-бот для автоматизированной продажи VPN-доступа.

## Возможности

- ✅ Автоматическая выдача VLESS-ключей через X-UI API
- 💰 Внутренний баланс пользователя
- 🎁 Пробный период 3 дня для новых пользователей
- 👥 Реферальная система с бонусами
- 🌍 Выбор сервера из нескольких локаций
- 📊 Админ-панель для управления

## Технический стек

- Python 3.10+
- Aiogram 3.x
- SQLite / PostgreSQL
- X-UI API
- APScheduler

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-repo/freakvpn-bot.git
cd freakvpn-bot
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе примера:
```env
BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789,987654321
```

5. Запустите бота:
```bash
python bot.py
```

## Структура проекта

```
freakvpn-bot/
├── bot.py              # Точка входа
├── config.py           # Конфигурация
├── database/           # Работа с БД
│   ├── db.py           # Подключение к БД
│   ├── models.py       # Модели таблиц
│   └── queries.py      # Запросы к БД
├── handlers/           # Обработчики
│   ├── start.py        # Команда /start
│   ├── admin.py        # Админ-панель
│   ├── menu.py         # Главное меню
│   ├── profile.py      # Профиль
│   ├── key.py          # Ключ
│   ├── purchase.py     # Покупка
│   ├── servers.py      # Серверы
│   ├── support.py      # Поддержка
│   └── callbacks.py    # Callback-обработчики
├── keyboards/          # Клавиатуры
│   ├── reply.py        # Reply-клавиатуры
│   ├── inline.py       # Inline-клавиатуры
│   └── admin.py        # Админ-клавиатуры
├── services/           # Сервисы
│   ├── xui_api.py      # X-UI API
│   ├── payment.py      # Платежи
│   ├── scheduler.py    # Планировщик
│   └── referral.py     # Рефералы
├── middlewares/        # Middleware
│   ├── registration.py # Авто-регистрация
│   └── throttle.py     # Защита от спама
├── utils/              # Утилиты
│   ├── constants.py    # Константы
│   ├── helpers.py      # Помощники
│   └── validators.py   # Валидаторы
└── logs/               # Логи
```

## Команды бота

### Пользовательские
- `/start` - Запуск бота
- `/help` - Справка
- `/profile` - Профиль
- `/key` - Мой ключ
- `/support` - Поддержка

### Административные
- `/admin` - Вход в админ-панель

## Лицензия

MIT
