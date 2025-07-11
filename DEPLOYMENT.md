# 🚀 Руководство по развертыванию

Подробное руководство по развертыванию Telegram бота для управления инструментами на строительных объектах.

## 📋 Предварительные требования

### Системные требования
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- Python 3.8+
- PostgreSQL 12+
- Git

### Минимальные характеристики сервера
- CPU: 1 ядро
- RAM: 2 GB
- Диск: 20 GB
- Сеть: стабильное интернет-соединение

## 🛠️ Пошаговая установка

### 1. Подготовка сервера

#### Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

#### Установка необходимых пакетов
```bash
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git nginx
```

### 2. Настройка PostgreSQL

#### Запуск и настройка PostgreSQL
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Создание пользователя и базы данных
```bash
sudo -u postgres psql
```

В консоли PostgreSQL выполните:
```sql
CREATE DATABASE construction_bot;
CREATE USER bot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE construction_bot TO bot_user;
ALTER USER bot_user CREATEDB;
\q
```

#### Настройка аутентификации
```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Найдите строку:
```
local   all             postgres                                peer
```

Измените на:
```
local   all             postgres                                md5
```

Перезапустите PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 3. Настройка Python окружения

#### Создание пользователя для бота
```bash
sudo useradd -m -s /bin/bash botuser
sudo usermod -aG sudo botuser
```

#### Переключение на пользователя бота
```bash
sudo su - botuser
```

#### Клонирование репозитория
```bash
git clone <your-repository-url>
cd Telegram-bot-for-builders
```

#### Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации

#### Создание файла .env
```bash
nano .env
```

Содержимое файла:
```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=construction_bot
DB_USER=bot_user
DB_PASSWORD=your_secure_password

# Logging
LOG_LEVEL=INFO
```

#### Установка прав доступа
```bash
chmod 600 .env
```

### 5. Инициализация базы данных

```bash
python init_db.py
```

### 6. Настройка systemd сервиса

#### Создание файла сервиса
```bash
sudo nano /etc/systemd/system/construction-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=Construction Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=botuser
Group=botuser
WorkingDirectory=/home/botuser/Telegram-bot-for-builders
Environment=PATH=/home/botuser/Telegram-bot-for-builders/venv/bin
ExecStart=/home/botuser/Telegram-bot-for-builders/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Активация сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable construction-bot
sudo systemctl start construction-bot
```

#### Проверка статуса
```bash
sudo systemctl status construction-bot
```

### 7. Настройка Nginx (опционально)

#### Создание конфигурации
```bash
sudo nano /etc/nginx/sites-available/construction-bot
```

Содержимое:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Активация сайта
```bash
sudo ln -s /etc/nginx/sites-available/construction-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Настройка SSL (рекомендуется)

#### Установка Certbot
```bash
sudo apt install certbot python3-certbot-nginx
```

#### Получение SSL сертификата
```bash
sudo certbot --nginx -d your-domain.com
```

## 🔧 Мониторинг и обслуживание

### Просмотр логов
```bash
# Логи systemd
sudo journalctl -u construction-bot -f

# Логи PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*.log

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Управление сервисом
```bash
# Перезапуск бота
sudo systemctl restart construction-bot

# Остановка бота
sudo systemctl stop construction-bot

# Проверка статуса
sudo systemctl status construction-bot
```

### Резервное копирование

#### Создание скрипта резервного копирования
```bash
nano backup.sh
```

Содержимое:
```bash
#!/bin/bash
BACKUP_DIR="/home/botuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Резервное копирование базы данных
pg_dump -h localhost -U bot_user construction_bot > $BACKUP_DIR/db_backup_$DATE.sql

# Резервное копирование конфигурации
cp /home/botuser/Telegram-bot-for-builders/.env $BACKUP_DIR/env_backup_$DATE

# Удаление старых бэкапов (старше 7 дней)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "env_backup_*" -mtime +7 -delete

echo "Backup completed: $DATE"
```

#### Настройка автоматического резервного копирования
```bash
chmod +x backup.sh
crontab -e
```

Добавьте строку для ежедневного бэкапа в 2:00:
```
0 2 * * * /home/botuser/backup.sh
```

## 🔒 Безопасность

### Настройка файрвола
```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Обновление системы
```bash
# Настройка автоматических обновлений
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Мониторинг безопасности
```bash
# Установка fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 🚨 Устранение неполадок

### Бот не запускается
```bash
# Проверка логов
sudo journalctl -u construction-bot -n 50

# Проверка конфигурации
sudo systemctl status construction-bot
```

### Проблемы с базой данных
```bash
# Проверка подключения
psql -h localhost -U bot_user -d construction_bot

# Проверка логов PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Проблемы с сетью
```bash
# Проверка DNS
nslookup your-domain.com

# Проверка портов
sudo netstat -tlnp
```

## 📊 Мониторинг производительности

### Установка мониторинга
```bash
# Установка htop для мониторинга ресурсов
sudo apt install htop

# Установка iotop для мониторинга дисковых операций
sudo apt install iotop
```

### Создание скрипта мониторинга
```bash
nano monitor.sh
```

Содержимое:
```bash
#!/bin/bash
echo "=== System Resources ==="
free -h
echo ""
echo "=== Disk Usage ==="
df -h
echo ""
echo "=== Bot Status ==="
sudo systemctl status construction-bot --no-pager
echo ""
echo "=== Recent Logs ==="
sudo journalctl -u construction-bot -n 10 --no-pager
```

## 🔄 Обновление

### Обновление кода
```bash
cd /home/botuser/Telegram-bot-for-builders
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart construction-bot
```

### Обновление базы данных
```bash
# Создание резервной копии
pg_dump -h localhost -U bot_user construction_bot > backup_before_update.sql

# Применение миграций (если есть)
python migrate.py

# Перезапуск бота
sudo systemctl restart construction-bot
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `sudo journalctl -u construction-bot -f`
2. Убедитесь, что все сервисы запущены
3. Проверьте конфигурацию в файле `.env`
4. Создайте Issue в репозитории проекта

## 📝 Чек-лист развертывания

- [ ] Установлены все системные зависимости
- [ ] Настроена база данных PostgreSQL
- [ ] Создан пользователь для бота
- [ ] Настроен файл `.env`
- [ ] Инициализирована база данных
- [ ] Настроен systemd сервис
- [ ] Бот запущен и работает
- [ ] Настроен SSL (опционально)
- [ ] Настроено резервное копирование
- [ ] Настроена безопасность
- [ ] Протестированы все функции бота 