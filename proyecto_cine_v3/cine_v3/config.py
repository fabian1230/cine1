# config.py  –  Configuración de la aplicación
import os

class Config:
    # ── Base de datos ─────────────────────────────────────────────
    # En Railway: agrega un plugin MySQL/PostgreSQL y Railway
    # inyecta DATABASE_URL automáticamente.
    # Localmente sigue usando MySQL con las variables individuales.
    _database_url = os.getenv('DATABASE_URL')

    if _database_url:
        # Railway inyecta la URL completa
        SQLALCHEMY_DATABASE_URI = _database_url
    else:
        DB_HOST     = os.getenv('DB_HOST',     'localhost')
        DB_USER     = os.getenv('DB_USER',     'root')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        DB_NAME     = os.getenv('DB_NAME',     'cine_db')
        DB_PORT     = int(os.getenv('DB_PORT', 3306))
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
            f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

    SECRET_KEY = os.getenv('SECRET_KEY', 'cine_secret_2024')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Correo ────────────────────────────────────────────────────
    MAIL_ENABLED   = os.getenv('MAIL_ENABLED', 'false').lower() == 'true'
    MAIL_HOST      = os.getenv('MAIL_HOST', 'smtp.gmail.com')
    MAIL_PORT      = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS   = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL   = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME  = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD  = os.getenv('MAIL_PASSWORD', '')
    MAIL_FROM      = os.getenv('MAIL_FROM', os.getenv('MAIL_USERNAME', ''))
    MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME', 'Aurum Cinema')
