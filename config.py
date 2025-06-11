from decouple import config
import os

class Config:
    SECRET_KEY = config('SECRET_KEY', default='a_very_secret_key_that_should_be_changed_in_prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False # Set to True for debugging SQL queries

    # Flask-Security-Too Configuration
    SECURITY_PASSWORD_SALT = config('SECURITY_PASSWORD_SALT', default='a_long_random_string_for_password_salt')
    SECURITY_REGISTERABLE = True
    SECURITY_CONFIRMABLE = False # Set to True to enable email confirmation
    SECURITY_SEND_REGISTER_EMAIL = False # Usually False if confirmable is False
    SECURITY_RECOVERABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_UNIFIED_SIGNIN = True # Allow login with email or username if applicable

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
    LANGUAGES = ['en', 'sw']
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'Africa/Nairobi'

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///rept_dev.db' # Use a separate dev db
    DEBUG = True
    SQLALCHEMY_ECHO = True # Log SQL queries in development
    # Override mail/twilio for development
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 1025 # For mailhog/mailtrap development
    MAIL_USE_TLS = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MPESA_SAF_CALLBACK_URL = config('MPESA_SAF_CALLBACK_URL_DEV', default='[http://127.0.0.1:5000/mpesa/callback](http://127.0.0.1:5000/mpesa/callback)') # Local/ngrok URL

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL') # Must be provided as env var
    DEBUG = False
    SQLALCHEMY_ECHO = False
    # Ensure all sensitive configs are read from environment variables for production
    SECRET_KEY = config('SECRET_KEY')
    SECURITY_PASSWORD_SALT = config('SECURITY_PASSWORD_SALT')
    MAIL_USERNAME = config('MAIL_USERNAME')
    MAIL_PASSWORD = config('MAIL_PASSWORD')
    TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN')
    MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY')
    MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET')
    MPESA_PASSKEY = config('MPESA_PASSKEY')
    MPESA_INITIATOR_PASSWORD = config('MPESA_INITIATOR_PASSWORD')
    MPESA_SAF_CALLBACK_URL = config('MPESA_SAF_CALLBACK_URL')

    # pgAudit specific settings (these are usually set in postgresql.conf or via ALTER SYSTEM)
    # You might need to add instructions for database setup/provisioning in your deployment docs
    # Pgaudit setup is database-level, not directly Flask config.