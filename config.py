import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = "7662805259:AAF7exxRK6dmeps3rq3RkXek_umMHT3p808"

# Database configuration
DB_USERNAME = "postgres"
DB_PASSWORD = "postgres"
DB_NAME = "Bot"
DB_HOST = "localhost"
DB_PORT = "5432"

# Database URL
DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 