"""Flask extensions module."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_security import Security
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_babel import Babel
from apscheduler.schedulers.background import BackgroundScheduler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
security = Security()
csrf = CSRFProtect()
mail = Mail()
babel = Babel()
scheduler = BackgroundScheduler()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()
