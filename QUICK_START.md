# ⚡ Быстрый старт

Минимальное руководство для быстрого запуска Telegram бота.

## 🚀 Быстрая установка (5 минут)

### 1. Подготовка
```bash
# Клонирование репозитория
git clone <repository-url>
cd Telegram-bot-for-builders

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка базы данных
```bash
# Установите PostgreSQL и создайте базу данных
# Затем создайте файл .env:

BOT_TOKEN=your_telegram_bot_token
DB_HOST=localhost
DB_PORT=5432
DB_NAME=construction_bot
DB_USER=your_username
DB_PASSWORD=your_password
```

### 4. Инициализация
```bash
python init_db.py
```

### 5. Запуск
```bash
python main.py
```

## 📋 Минимальные требования

- **Python 3.8+**
- **PostgreSQL 12+**
- **Telegram Bot Token**

## 🔧 Быстрая настройка PostgreSQL

### Ubuntu/Debian:
```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql
```

### Windows:
- Скачайте и установите PostgreSQL с официального сайта
- Используйте pgAdmin для управления

### macOS:
```bash
brew install postgresql
brew services start postgresql
```

### Создание базы данных:
```sql
CREATE DATABASE construction_bot;
CREATE USER bot_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE construction_bot TO bot_user;
```

## 🤖 Получение Telegram Bot Token

1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен в `.env`

## ✅ Проверка установки

### Тест подключения к базе данных:
```bash
python -c "
from database.connection import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('✅ База данных подключена успешно!')
"
```

### Тест бота:
1. Запустите `python main.py`
2. Найдите бота в Telegram
3. Отправьте `/start`
4. Проверьте ответ бота

## 🚨 Частые проблемы

### Ошибка подключения к PostgreSQL:
```bash
# Проверьте, что PostgreSQL запущен
sudo systemctl status postgresql

# Проверьте настройки в .env
cat .env
```

### Бот не отвечает:
- Проверьте токен в `.env`
- Убедитесь, что бот не заблокирован
- Проверьте логи в консоли

### Ошибки при инициализации БД:
```bash
# Удалите и пересоздайте базу данных
dropdb construction_bot
createdb construction_bot
python init_db.py
```

## 📱 Первое использование

### Для администратора:
1. Запустите бота
2. Отправьте `/start`
3. Зарегистрируйтесь как первый пользователь
4. Назначьте себе роль "прораб объекта" в базе данных

### Для рабочих:
1. Найдите бота в Telegram
2. Отправьте `/start`
3. Зарегистрируйтесь
4. Дождитесь одобрения бригадиром

### Для бригадиров:
1. Используйте команду `/foreman`
2. Управляйте регистрациями и заявками
3. Проводите инвентаризацию

## 🔄 Обновление

```bash
git pull origin main
pip install -r requirements.txt
python init_db.py  # если есть изменения в БД
python main.py
```

## 📞 Нужна помощь?

- 📖 [Полное руководство](README.md)
- 🚀 [Руководство по развертыванию](DEPLOYMENT.md)
- 👤 [Руководство пользователя](USER_GUIDE.md)

## ⚡ Готово!

Бот готов к использованию! 🎉

**Следующие шаги:**
1. Настройте пользователей и объекты
2. Добавьте инструменты в базу данных
3. Проведите первую инвентаризацию
4. Начните использовать все функции бота 