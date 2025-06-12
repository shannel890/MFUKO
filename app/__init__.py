from flask import Flask, request, render_template, g
from flask_security import SQLAlchemySessionUserDatastore
from flask_babel import _, lazy_gettext as _l
import os
import requests
from datetime import datetime
from flask_login import current_user

from config import Config
from extension import db, login_manager, security, csrf, mail, babel, scheduler, limiter, migrate
from forms import ExtendRegisterForm, ExtendedLoginForm # Import your custom forms

# Initialize extensions

# db = SQLAlchemy()
# security = Security()
# mail = Mail()
# babel = Babel()
# limiter = Limiter(key_func=get_remote_address)
# scheduler = BackgroundScheduler()

def create_app(config_name='development'):
    app = Flask(__name__)

    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    babel.init_app(app) # Initialize Babel with the app

    def get_locale():
        if current_user.is_authenticated:
            return current_user.language
        return request.accept_languages.best_match(app.config['LANGUAGES'])
    babel.locale_selector_func = get_locale

    limiter.init_app(app) # Initialize Limiter with the app

    # Setup Flask-Security-Too
    from app.models import User, Role # Import models needed for user_datastore
    user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role)
    security.init_app(app, user_datastore)

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

    # Initialize APScheduler tasks
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        with app.app_context():
            scheduler.add_job(
                'app.tasks:check_and_generate_rent_invoices',
                trigger='cron',
                id='rent_invoices',
                day='1',  # Run on 1st of every month
                hour='0',
                minute='0',
                replace_existing=True
            )
            scheduler.add_job(
                'app.tasks:send_payment_reminders',
                trigger='cron',
                id='payment_reminders',
                hour='9',  # Run daily at 9 AM
                minute='0',
                replace_existing=True
            )
            scheduler.add_job(
                'app.tasks:sync_offline_payments',
                trigger='interval',
                id='sync_offline_payments',
                minutes=30,  # Run every 30 minutes
                replace_existing=True
            )
            scheduler.add_job(
                'app.tasks:refresh_mpesa_token',
                trigger='interval',
                id='mpesa_token_refresh',
                minutes=50,  # Token expires after 1 hour
                replace_existing=True
            )
            if not scheduler.running:
                scheduler.start()

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Jinja2 filters and globals
    app.jinja_env.filters['currency'] = lambda value: f"KSh {value:,.2f}"
    app.jinja_env.filters['phone'] = lambda number: f"+254{number[-9:]}" if number else ""
    
    app.jinja_env.globals.update(
        current_year=datetime.utcnow().year,
        site_name="REPT Kenya"
    )

    # Before request handler for offline mode detection
    @app.before_request
    def check_offline_mode():
        g.is_offline = not check_internet_connection()

    return app

def check_internet_connection():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except requests.RequestException:
        return False