from decouple import config
import os

class Config:
    SECRET_KEY = config('SECRET_KEY', default='a_very_secret_key_that_should_be_changed_in_prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Enable for debugging SQL queries
    SQLALCHEMY_DATABASE_URI = config(
        'DATABASE_URL',
        default=f"postgresql://{config('POSTGRES_USER')}:{config('POSTGRES_PASSWORD')}@"
                f"{config('POSTGRES_HOST')}:{config('POSTGRES_PORT')}/{config('POSTGRES_DB')}"
    )

    # Flask-Security-Too Configuration
    SECURITY_PASSWORD_SALT = config('SECURITY_PASSWORD_SALT', default='a_long_random_string_for_password_salt')
    SECURITY_REGISTERABLE = True
    SECURITY_CONFIRMABLE = False
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_RECOVERABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_TWO_FACTOR = False  # Disable two-factor auth for now
    SECURITY_UNIFIED_SIGNIN = False  # Disable unified signin
    SECURITY_USER_IDENTITY_ATTRIBUTES = [{"email": {"mapper": lambda x: x, "case_insensitive": True}}]
    SECURITY_PASSWORD_LENGTH_MIN = 8
    SECURITY_PASSWORD_COMPLEXITY_CHECKER = 'zxcvbn'

    # Flask-Mail Configuration (for email notifications)
    MAIL_SERVER = config('MAIL_SERVER', default='smtp.mailtrap.io') # Or your actual SMTP server
    MAIL_PORT = config('MAIL_PORT', default=2525, cast=int)
    MAIL_USE_TLS = config('MAIL_USE_TLS', default=True, cast=bool)
    MAIL_USERNAME = config('MAIL_USERNAME', default='your_mail_username')
    MAIL_PASSWORD = config('MAIL_PASSWORD', default='your_mail_password')
    MAIL_DEFAULT_SENDER = config('MAIL_DEFAULT_SENDER', default='noreply@countyportal.com')

    # Twilio Configuration (for SMS notifications)
    TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='ACxxxxxxxxxxxxxxxxxxxxx')
    TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='your_twilio_auth_token')
    TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='+15017122661') # Your Twilio number

    # M-Pesa API Configuration
    MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='your_mpesa_consumer_key')
    MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='your_mpesa_consumer_secret')
    MPESA_PASSKEY = config('MPESA_PASSKEY', default='your_mpesa_passkey') # For STK Push
    MPESA_PAYBILL = config('MPESA_PAYBILL', default='your_mpesa_paybill') # Your PayBill number
    MPESA_INITIATOR_PASSWORD = config('MPESA_INITIATOR_PASSWORD', default='your_initiator_password') # For B2C/C2B validation
    MPESA_SAF_CALLBACK_URL = config('MPESA_SAF_CALLBACK_URL', default='[https://yourdomain.com/mpesa/callback](https://yourdomain.com/mpesa/callback)') # Publicly accessible URL

    # APScheduler Configuration (if using Flask-APScheduler)
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': True,
        'max_instances': 1
    }
    SCHEDULER_EXECUTORS = {
        'default': {'type': 'threadpool', 'max_workers': 20}
    }
    # For persistence across restarts (production)
    # SCHEDULER_JOBSTORES = {
    #     'default': {'type': 'sqlalchemy', 'url': 'sqlite:///jobs.sqlite'}
    # }

    # Flask-Babel Configuration
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'Africa/Nairobi'
    LANGUAGES = ['en', 'sw']
    
    # Flask-Limiter Configuration
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = "memory://"  # Use Redis in production
    
    # Report Generation
    REPORT_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'reports')
    ALLOWED_EXTENSIONS = {'pdf', 'csv', 'xlsx'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Offline Mode Configuration
    OFFLINE_CACHE_LIMIT = 1000  # Maximum number of offline transactions to store
    SYNC_RETRY_LIMIT = 3  # Number of times to retry syncing offline data
    
    # Audit Trail Configuration
    AUDIT_LOG_DAYS = 365  # Days to keep audit logs
    AUDIT_ENABLED = True
    
    # Payment Configuration
    PAYMENT_GRACE_PERIOD = 5  # Default grace period in days
    PAYMENT_REMINDER_DAYS = [5, 3, 1]  # Days before due date to send reminders
    PAYMENT_LATE_FEE_PERCENTAGE = 0.05  # 5% late fee
    
    # Security Configuration
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_COMPLEXITY = True  # Require mixed case, numbers, and special characters
    SESSION_TIMEOUT = 3600  # 1 hour session timeout
    REMEMBER_COOKIE_DURATION = 2592000  # 30 days for "remember me"

    # Database Configuration
    POSTGRES_HOST = config('POSTGRES_HOST', default='localhost')
    POSTGRES_PORT = config('POSTGRES_PORT', default=5432, cast=int)
    POSTGRES_DB = config('POSTGRES_DB', default='county')
    POSTGRES_USER = config('POSTGRES_USER', default='devuser')
    POSTGRES_PASSWORD = config('POSTGRES_PASSWORD', default='devpassword')
    SQLALCHEMY_DATABASE_URI = config(
        'DATABASE_URL',
        default='postgresql://devuser:devpassword@localhost:5432/county'
    )

    @staticmethod
    def init_app(app):
        # Create upload directories if they don't exist
        if not os.path.exists(Config.REPORT_UPLOAD_FOLDER):
            os.makedirs(Config.REPORT_UPLOAD_FOLDER)

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    # Override mail/twilio for development
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 1025 # For mailhog/mailtrap development
    MAIL_USE_TLS = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MPESA_SAF_CALLBACK_URL = config('MPESA_SAF_CALLBACK_URL_DEV', default='[http://127.0.0.1:5000/mpesa/callback](http://127.0.0.1:5000/mpesa/callback)') # Local/ngrok URL

class ProductionConfig(Config):
    DEBUG = False
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    RATELIMIT_STORAGE_URL = config('REDIS_URL', default='redis://localhost:6379/0')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config_options = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}