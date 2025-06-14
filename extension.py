"""Flask extensions module."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_security import Security, SQLAlchemySessionUserDatastore
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_babel import Babel
from apscheduler.schedulers.background import BackgroundScheduler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
import logging

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
babel = Babel()

# Initialize Flask-Security (base configuration, will be fully configured in create_app)
security = Security()

# Configure scheduler
scheduler = BackgroundScheduler(
    daemon=True,
    job_defaults={
        'coalesce': True,  # Combine multiple pending jobs into one
        'max_instances': 1,  # Only allow one instance of each job to run at a time
        'misfire_grace_time': 15 * 60  # Allow jobs to start up to 15 minutes late
    },
    executors={
        'default': {
            'type': 'threadpool',
            'max_workers': 20  # Max number of concurrent jobs
        }
    }
)

# Configure scheduler logging
logging.getLogger('apscheduler').setLevel(logging.INFO)

# Initialize extensions that will be configured in create_app
limiter = None  # Will be initialized in create_app
migrate = Migrate()

# Initialize Flask-Security datastore with placeholder
class LazyUserDatastore:
    def __init__(self):
        self._user_datastore = None

    def init_datastore(self, db_session, user_cls, role_cls):
        if not self._user_datastore:
            self._user_datastore = SQLAlchemySessionUserDatastore(db_session, user_cls, role_cls)
        return self._user_datastore

    def __getattr__(self, name):
        if not self._user_datastore:
            raise RuntimeError('User datastore not initialized. Call init_datastore first.')
        return getattr(self._user_datastore, name)
        self._user_datastore = SQLAlchemySessionUserDatastore(db_session, user_cls, role_cls)
        return self._user_datastore

    def __getattr__(self, name):
        if self._user_datastore is None:
            raise RuntimeError("UserDatastore not initialized. Call init_datastore first.")
        return getattr(self._user_datastore, name)

user_datastore = LazyUserDatastore()
