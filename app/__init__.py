from flask import Flask,request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_security import Security, SQLAlchemySessionUserDatastore
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_babel import Babel, _, lazy_gettext as _l # Import Babel for i18n
from apscheduler.schedulers.background import BackgroundScheduler # For background tasks
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config, DevelopmentConfig, ProductionConfig # Import config classes
from ..forms import ExtendRegisterForm, ExtendedLoginForm # Import your custom forms

db = SQLAlchemy()
login_manager = LoginManager()
security = Security()
csrf = CSRFProtect()
mail = Mail()
babel = Babel() # Initialize Babel
scheduler = BackgroundScheduler() # Initialize scheduler
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]) # Initialize limiter

def create_app(config_name='development'):
    app = Flask(__name__)

    if config_name == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    babel.init_app(app) # Initialize Babel with the app
    limiter.init_app(app) # Initialize Limiter with the app

    # Setup Flask-Security-Too
    from app.models import User, Role, County # Import models needed for user_datastore
    user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role)
    security.init_app(app, user_datastore,
                      register_form=ExtendRegisterForm,
                      login_form=ExtendedLoginForm)

    # Register Blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # --- Scheduler Setup ---
    # Moved scheduler start here to ensure app context is available
    from .tasks import check_overdue_payments, refresh_mpesa_token # Assuming tasks.py exists
    if not scheduler.running:
        scheduler.start()
        # Add tasks to scheduler (example)
        scheduler.add_job(refresh_mpesa_token, 'interval', hours=1, id='mpesa_token_refresh', replace_existing=True)
        scheduler.add_job(check_overdue_payments, 'cron', hour=3, minute=0, id='overdue_check', replace_existing=True)

    # --- Babel Locale Selector ---
    @babel.localeselector
    def get_locale():
        # Try to guess the language from the user accept header first
        # You might also store user's preferred language in the User model
        return request.accept_languages.best_match(app.config['LANGUAGES'])

    # --- Login Manager User Loader ---
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app