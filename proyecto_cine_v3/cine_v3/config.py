# config.py  –  Configuración de la aplicación
import os

class Config:
    # ── Base de datos MySQL ──────────────────────────────────────
    DB_HOST     = os.getenv('DB_HOST',     'localhost')
    DB_USER     = os.getenv('DB_USER',     'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')        # cambia tu contraseña
    DB_NAME     = os.getenv('DB_NAME',     'cine_db')
    DB_PORT     = int(os.getenv('DB_PORT', 3306))

    SECRET_KEY  = os.getenv('SECRET_KEY',  'cine_secret_2024')

    MAIL_ENABLED   = os.getenv('MAIL_ENABLED', 'false').lower() == 'true'
    MAIL_HOST      = os.getenv('MAIL_HOST', 'smtp.gmail.com')
    MAIL_PORT      = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS   = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL   = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME  = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD  = os.getenv('MAIL_PASSWORD', '')
    MAIL_FROM      = os.getenv('MAIL_FROM', os.getenv('MAIL_USERNAME', ''))
    MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME', 'Aurum Cinema')

    # ── Cadena de conexión SQLAlchemy ────────────────────────────
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
