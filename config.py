# config.py

from decouple import config
import os
from dotenv import load_dotenv
import secrets # Used to generate a strong random salt

load_dotenv()  # Load environment variables from .env file

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False # Set to True for debugging SQL queries

    # Flask-Security-Too Configuration
    # IMPORTANT: SECURITY_PASSWORD_SALT MUST BE SET AND BE A STRONG, RANDOM STRING IN PRODUCTION
    # The value must be a long, random string. It is critical for secure password hashing.
    SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT') # No default - must be set via environment variable
    SECURITY_PASSWORD_HASH = "argon2" # Recommended strong hashing algorithm
    
    # Flask-Limiter Configuration
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL')
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_HEADERS_ENABLED = True

    SECURITY_REGISTERABLE = True
    SECURITY_CONFIRMABLE = False # Set to True to enable email confirmation
    SECURITY_SEND_REGISTER_EMAIL = False # Usually False if confirmable is False
    SECURITY_RECOVERABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False        # Registration confirmation        
    SECURITY_SEND_PASSWORD_RESET_EMAIL = True  # Password reset instructions      
    SECURITY_SEND_PASSWORD_CHANGE_EMAIL = True # Password change notifications
    SECURITY_UNIFIED_SIGNIN = False # Allow login with email or username if applicable
    SECURITY_FLASH_MESSAGES = True # Ensure flash messages are enabled
    SECURITY_POST_REGISTER_VIEW= 'auth.login' # Redirect to login after registration
    SECURITY_BLUEPRINT_NAME = 'fs_auth'

    # Flask-Mail Configuration (for email notifications)
    MAIL_SERVER = config('MAIL_SERVER', 'smtp.mailtrap.io') # Or your actual SMTP server
    MAIL_PORT = config('MAIL_PORT', 2525, cast=int)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes', 'on')                                                                      
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes', 'on')
    MAIL_USERNAME = config('MAIL_USERNAME')
    MAIL_PASSWORD = config('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = config('MAIL_DEFAULT_SENDER')

    # Twilio Configuration (for SMS notifications)
    TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default=None)
    TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default=None)
    TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='+15017122661')

    # M-Pesa API Configuration
    MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default=None)
    MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default=None)
    MPESA_PASSKEY = config('MPESA_PASSKEY', default=None) # For STK Push
    MPESA_PAYBILL = config('MPESA_PAYBILL', default='174379') # Daraja test till number as default
    MPESA_INITIATOR_PASSWORD = config('MPESA_INITIATOR_PASSWORD', default='Safaricom999!') # Daraja test initiator password as default
    MPESA_SAF_CALLBACK_URL = config('MPESA_SAF_CALLBACK_URL', default=None) # Crucial for M-Pesa callbacks

    # APScheduler Configuration
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': True,
        'max_instances': 1
    }
    SCHEDULER_EXECUTORS = {
        'default': {'type': 'threadpool', 'max_workers': 20}
    }

    # Flask-Babel Configuration
    LANGUAGES = ['en', 'sw']
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'Africa/Nairobi'

    # Flask-Limiter config
    # Default to memory storage for dev, but requires a proper backend for production
    RATELIMIT_STORAGE_URL = config('RATELIMIT_STORAGE_URL', default='memory://')


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    DEBUG = True
    SQLALCHEMY_ECHO = True

    # Development-specific security salt
    # WARNING: This is only for development! Never use this default in production!
    # For local development convenience, we provide a default salt to avoid requiring env vars
    # In production, you must set SECURITY_PASSWORD_SALT via environment variables
    SECURITY_PASSWORD_SALT = config('SECURITY_PASSWORD_SALT_DEV', 
                                  default='dev-only-K86tq9PmGXq6yZtS4LkVJp2DrXT7DmYs5fQNhEj8xRv')  # 43-char random string

    # Overrides for development mail/twilio/mpesa
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 1025 # For mailhog/mailtrap development
    MAIL_USE_TLS = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    TWILIO_ACCOUNT_SID = 'ACxxxxxxxxxxxxxxxxxxxxx_DEV' # Dummy
    TWILIO_AUTH_TOKEN = 'your_twilio_auth_token_DEV' # Dummy
    MPESA_CONSUMER_KEY = 'consumer_key_DEV'
    MPESA_CONSUMER_SECRET = 'consumer_secret_DEV'
    MPESA_SAF_CALLBACK_URL = config('MPESA_SAF_CALLBACK_URL_DEV', default='http://127.0.0.1:5000/mpesa/callback') # Local/ngrok URL


class ProductionConfig(Config):
    # These configurations MUST be provided via environment variables in production
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL')
    
    # CRITICAL: PRODUCTION SALT MUST BE SET VIA ENVIRONMENT VARIABLE
    # This MUST be a unique, cryptographically strong random string
    # Generate using: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECURITY_PASSWORD_SALT = config('SECURITY_PASSWORD_SALT')  # Explicitly no default to force env var in production

    # Production sensitive configs (no defaults here, forcing env var)
    SECRET_KEY = config('SECRET_KEY')
    MAIL_USERNAME = config('MAIL_USERNAME')
    MAIL_PASSWORD = config('MAIL_PASSWORD')
    TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER')
    MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY')
    MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET')
    MPESA_PASSKEY = config('MPESA_PASSKEY')
    MPESA_INITIATOR_PASSWORD = config('MPESA_INITIATOR_PASSWORD')
    MPESA_SAF_CALLBACK_URL = config('MPESA_SAF_CALLBACK_URL')
    RATELIMIT_STORAGE_URL = config('RATELIMIT_STORAGE_URL', default='redis://localhost:6379/0') # Recommend Redis in prod

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///'

# Configuration dictionary
config_options = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}