# 🚀 Запуск FreakVPN Bot

## Быстрый старт

### 1. Установка зависимостей

```bash
cd freakvpn-bot
pip install -r requirements.txt
```

### 2. Настройка окружения

Скопируй `.env.example` в `.env`:

```bash
cp .env.example .env
```

Отредактируй `.env`:

```env
# Токен бота от @BotFather
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# ID администраторов через запятую
ADMIN_IDS=123456789,987654321

# Остальное можно оставить по умолчанию
DEFAULT_TRIAL_DAYS=3
DEFAULT_REFERRAL_BONUS=5000
DATABASE_PATH=freakvpn.db
TIMEZONE=Europe/Moscow
LOG_LEVEL=INFO
```

### 3. Запуск бота

```bash
python bot.py
```

---

## 📁 Структура проекта

```
freakvpn-bot/
├── .env                    # Конфигурация (не коммитить!)
├── .env.example            # Пример конфигурации
├── bot.py                  # Точка входа
├── config.py               # Загрузка конфигурации
├── requirements.txt        # Зависимости
│
├── database/               # База данных
│   ├── db.py              # Класс для работы с SQLite
│   ├── models.py          # Создание таблиц
│   └── queries.py         # SQL запросы
│
├── handlers/               # Обработчики
│   ├── start.py           # /start, пробный период
│   ├── menu.py            # Главное меню
│   ├── profile.py         # Профиль пользователя
│   ├── key.py             # Управление ключом
│   ├── purchase.py        # Покупка тарифов
│   ├── callbacks.py       # Общие callback-и
│   └── admin.py           # Админ-панель
│
├── keyboards/              # Клавиатуры
│   ├── reply.py           # Reply-клавиатуры
│   ├── inline.py          # Inline-клавиатуры пользователя
│   └── admin.py           # Inline-клавиатуры админа
│
├── services/               # Сервисы
│   ├── xui_api.py         # Интеграция с X-UI
│   ├── vpn_utils.py       # Утилиты для VPN ключей
│   ├── payment.py         # Платежи
│   ├── referral.py        # Реферальная система
│   └── scheduler.py       # Фоновые задачи
│
├── middlewares/            # Middleware
│   ├── registration.py    # Авто-регистрация пользователей
│   └── throttle.py        # Защита от спама
│
├── utils/                  # Утилиты
│   ├── constants.py       # Тексты сообщений
│   ├── helpers.py         # Вспомогательные функции
│   └── validators.py      # Валидаторы
│
├── docs/                   # Документация
│   ├── XUI_INTEGRATION.md # Интеграция с X-UI
│   └── XUI_API_REFERENCE.md
│
└── logs/                   # Логи (создаются автоматически)
    └── bot.log
```

---

## ⚙️ Функционал

### Пользователь

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация, пробный период |
| `/help` | Справка |
| `/profile` | Профиль пользователя |
| `/key` | Мой VPN ключ |
| `/support` | Контакты поддержки |

**Главное меню:**
- 🔌 **Мой ключ** — просмотр, копирование, смена ключа/сервера
- 📊 **Профиль** — баланс, рефералы, история операций
- 💰 **Купить / Продлить** — выбор и покупка тарифов
- 🆘 **Поддержка** — FAQ и контакты

### Администратор

| Команда | Описание |
|---------|----------|
| `/admin` | Вход в админ-панель |

**Админ-панель:**
- 👥 **Пользователи** — поиск, пополнение баланса, продление, блокировка
- 💰 **Пополнить баланс** — быстрое пополнение
- 📊 **Статистика** — общая статистика бота
- 🌍 **Серверы** — управление X-UI серверами
- ✉️ **Рассылка** — массовая рассылка пользователям
- ⚙️ **Настройки** — тарифы, пробный период, контакты

---

## 🔧 Настройка X-UI сервера

### 1. Установка 3X-UI

На VPS сервере установи 3X-UI панель:

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

### 2. Создание inbound

1. Открой X-UI панель: `http://IP:54321`
2. Перейди в **Inbounds** → **Add Inbound**
3. Настрой:
   - **Remark**: `FreakVPN_AMS`
   - **Protocol**: `VLESS`
   - **Port**: `443`
   - **Security**: `tls`
   - **SNI**: `ams.freakvpn.ru`
4. Запомни **Inbound ID** (обычно 1)

### 3. Добавление сервера в бота

Через админ-панель бота:

1. Нажми **🌍 Серверы** → **➕ Добавить сервер**
2. Введи данные:
   ```
   Амстердам;NL;ams.freakvpn.ru;45.67.89.10;54321;admin;password
   ```

Или через код:

```python
from database import queries

await queries.create_server(
    name="Амстердам",
    country_code="NL",
    domain="ams.freakvpn.ru",
    ip="45.67.89.10",
    api_url="http://45.67.89.10:54321",
    api_username="admin",
    api_password="your_password",
    port=443,
    inbound_id=1
)
```

### 4. Тестирование подключения

```bash
python test_xui_connection.py
```

---

## 📊 База данных

### Таблицы

| Таблица | Описание |
|---------|----------|
| `users` | Пользователи бота |
| `servers` | X-UI серверы |
| `transactions` | История операций |
| `tariffs` | Тарифы |
| `referrals` | Реферальные связи |
| `settings` | Настройки бота |
| `mailings` | Рассылки |

### Просмотр БД

```bash
sqlite3 freakvpn.db

.tables
.schema users
SELECT * FROM users;
```

---

## 🔄 Фоновые задачи

Автоматически запускаются при старте бота:

| Задача | Расписание | Описание |
|--------|------------|----------|
| Проверка подписок | 00:00 по МСК | Блокировка истекших |
| Уведомления | 12:00 по МСК | Напоминание за 3 дня |
| Синхронизация трафика | Каждый час | Обновление статистики |

---

## 🧪 Тестирование

### Проверка X-UI

```bash
python test_xui_connection.py --url http://IP:PORT --user admin --pass password
```

### Проверка бота

1. Запусти бота: `python bot.py`
2. Открой бота в Telegram
3. Нажми `/start`
4. Активируй пробный период
5. Проверь получение ключа

---

## 🐛 Отладка

### Включить DEBUG логи

В `.env`:

```env
LOG_LEVEL=DEBUG
```

### Просмотр логов

```bash
tail -f logs/bot.log
```

### Частые проблемы

| Проблема | Решение |
|----------|---------|
| Бот не отвечает | Проверь `BOT_TOKEN` |
| Ошибка БД | Удали `freakvpn.db` и перезапусти |
| Ключ не создается | Проверь подключение к X-UI |
| Админ-панель не открывается | Проверь `ADMIN_IDS` |

---

## 📞 Поддержка

- Telegram: @ShadowRing
- Email: support@freakvpn.ru

---

## 📝 TODO / Roadmap

- [ ] Автоматические платежи (ЮKassa, CryptoBot)
- [ ] Миграция на PostgreSQL
- [ ] Web-админка
- [ ] Мультиязычность
- [ ] Prometheus метрики
- [ ] Docker-compose
