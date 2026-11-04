import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# OAuth over plain HTTP is refused by default; set OAUTHLIB_INSECURE_TRANSPORT=1 explicitly
# in local dev if your Google redirect URI is http://.
if os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '0') == '1':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
else:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'

_DEV_MODE = (os.environ.get('FLASK_ENV', '').lower() == 'development'
             or os.environ.get('DATABASE_URL', 'sqlite').startswith('sqlite'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'migrc-dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'migrc.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Secure cookies by default; relaxed only for local dev (FLASK_ENV=development or sqlite).
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false' if _DEV_MODE else 'true').lower() == 'true'
    # Login throttling (failed attempts per IP+email within the window)
    LOGIN_MAX_ATTEMPTS = int(os.environ.get('LOGIN_MAX_ATTEMPTS', 10))
    LOGIN_WINDOW_SECONDS = int(os.environ.get('LOGIN_WINDOW_SECONDS', 900))
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file upload
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'csv', 'xlsx', 'doc', 'docx', 'ppt', 'pptx'}

    # Email notifications are opt-in and off by default — set MAIL_ENABLED=true once
    # MAIL_SERVER/USERNAME/PASSWORD are configured for a real SMTP account.
    MAIL_ENABLED = os.environ.get('MAIL_ENABLED', 'false').lower() == 'true'
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@migrc.local')

    # Google Workspace integration (SSO login + Admin SDK directory sync). Inert
    # unless all three are set - see app/routes/google_oauth.py.
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
