from flask import Flask, request, render_template, g
from flask_security import Security, SQLAlchemySessionUserDatastore, current_user
from flask_babel import _, lazy_gettext as _l
import os
from forms import ExtendedRegisterForm
import requests
from datetime import datetime, timedelta
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure logging for APScheduler
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# Import task functions
from app.tasks import (
    sync_offline_payments,
    refresh_mpesa_token,
    check_and_generate_rent_invoices,
    send_payment_reminders,
    send_upcoming_rent_reminders,
    send_overdue_reminders,
    check_overdue_payments
)

# Import configuration and extensions
from config import config_options
from extension import db, security, csrf, mail, babel, scheduler, limiter, migrate, user_datastore
from forms import ExtendedRegisterForm

def create_app(config_name='development'):
    """
    Application factory function to create and configure the Flask app.
    Args:
        config_name (str): The name of the configuration to load ('development', 'production', 'testing').
    """
    app = Flask(__name__, instance_relative_config=True)  # instance_relative_config for instance folder
    
    # Load configuration from the selected config class
    app.config.from_object(config_options[config_name])
    
    # Set Flask-Limiter configuration
    app.config['RATELIMIT_STORAGE_URL'] = 'memory://'  # Use in-memory storage for development
    app.config['RATELIMIT_DEFAULT'] = "200 per day"  # Default rate limit
    app.config['RATELIMIT_HEADERS_ENABLED'] = True
    app.config['SECURITY_REGISTER_FORM'] = ExtendedRegisterForm  


    # Flask-Security configuration
    app.config['SECURITY_BLUEPRINT_NAME'] = 'fs_auth'  # Use a unique blueprint name
    app.config['SECURITY_URL_PREFIX'] = '/auth'  # Prefix all Flask-Security URLs with /auth
    app.config['SECURITY_REGISTER_URL'] = '/signup'
    app.config['SECURITY_LOGIN_URL'] = '/signin'
    app.config['SECURITY_LOGOUT_URL'] = '/logout'
    app.config['SECURITY_POST_LOGIN_VIEW'] = '/dashboard'
    app.config['SECURITY_POST_REGISTER_VIEW'] = '/dashboard'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@db:5432/dbname')

    # Initialize core extensions with the Flask app
    db.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate
    csrf.init_app(app)
    mail.init_app(app)
    babel.init_app(app)

    # Initialize Flask-Limiter
    global limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    # Configure logging
    if not app.debug and not app.testing:
        # Example for basic file logging (adjust as needed for production)
        if not os.path.exists('logs'):
            os.makedirs('logs')
        file_handler = logging.FileHandler('logs/rept.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('REPT startup')

    # Ensure instance folder exists for configurations/logs
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass  # Folder already exists

    

    

    # Set up Flask-Babel locale selector function
    def get_locale():
         # 1. Try language from URL argument (e.g., /en/dashboard) - not implemented in routes yet
         lang = request.args.get('lang_code')
         if lang:
             return lang
        
        # 2. Try language from cookie
         lang = request.cookies.get('lang')
         if lang in app.config['LANGUAGES']:
            return lang

        # 3. Try language from authenticated user's preferences (if User model has 'language' field)
         if current_user.is_authenticated and hasattr(current_user, 'language') and current_user.language:
            return current_user.language
        
        # 4. Fallback to browser's accepted languages
         return request.accept_languages.best_match(app.config['LANGUAGES']) or app.config['BABEL_DEFAULT_LOCALE']
    
    babel.locale_selector_func = get_locale

    # Import User and Role models outside the app_context block but inside create_app
    from app.models import User, Role

    with app.app_context():
        # Create database tables (only if they don't exist)
        db.create_all()
        
        # Initialize Flask-Security user datastore
        user_datastore.init_datastore(db.session, User, Role)
        
        # Initialize Flask-Security with a SINGLE init_app call
        security.init_app(app, user_datastore,
                      register_form=ExtendedRegisterForm,
                      registerable=True, # THIS MUST BE TRUE for FST to handle registration
                      # ... other FST configs like confirmable, trackable, etc.

                      # Crucial for redirection after successful registration
                      post_register_view='security.login', # Redirects to FST's login page
                      # OR 'main.dashboard' if you want to redirect to a dashboard after register
                      flash_messages=True # Recommended to display FST's internal flash messages
                     )
        
        from app.auth import auth as auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        import uuid

        def create_user(**kwargs):
            kwargs['fs_uniquifier'] = str(uuid.uuid4())
            user = user_datastore.create_user(**kwargs)
            db.session.commit()
            return user

        # Create default roles if they don't exist
        if not user_datastore.find_role('landlord'):
            user_datastore.create_role(name='landlord', description='Property owner/manager')
        if not user_datastore.find_role('tenant'):
            user_datastore.create_role(name='tenant', description='Property occupant')
        if not user_datastore.find_role('admin'):
            user_datastore.create_role(name='admin', description='System administrator')
        db.session.commit()  # Commit role creation

    # Register Blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Initialize and configure APScheduler
    if not scheduler.running:
        # sync_offline_payments: every 15 minutes
        scheduler.add_job(
            func=sync_offline_payments,
            trigger='interval',
            minutes=15,
            args=[app],
            id='sync_offline_payments',
            name='Sync Offline Payments',
            replace_existing=True
        )

        # refresh_mpesa_token: every 1 hour
        scheduler.add_job(
            func=refresh_mpesa_token,
            trigger='interval',
            hours=1,
            args=[app],
            id='mpesa_token_refresh',
            name='Refresh M-Pesa Token',
            replace_existing=True
        )

        # check_and_generate_rent_invoices: once a month on the 1st
        scheduler.add_job(
            func=check_and_generate_rent_invoices,
            trigger='cron',
            day='1',
            hour=2,
            args=[app],
            id='generate_rent_invoices',
            name='Generate Monthly Rent Invoices',
            replace_existing=True
        )

        # send_payment_reminders: daily at 9 AM
        scheduler.add_job(
            func=send_payment_reminders,
            trigger='cron',
            hour=9,
            minute=0,
            args=[app],
            id='send_payment_reminders',
            name='Send Payment Reminders',
            replace_existing=True
        )

        # send_upcoming_rent_reminders: daily at 6 AM
        scheduler.add_job(
            func=send_upcoming_rent_reminders,
            trigger='cron',
            hour=6,
            minute=0,
            args=[app],
            id='send_upcoming_rent_reminders',
            name='Send Upcoming Rent Reminders',
            replace_existing=True
        )

        # send_overdue_reminders: daily at 10 AM
        scheduler.add_job(
            func=send_overdue_reminders,
            trigger='cron',
            hour=10,
            minute=0,
            args=[app],
            id='send_overdue_reminders',
            name='Send Overdue Reminders',
            replace_existing=True
        )

        # check_overdue_payments: daily at 11 AM
        scheduler.add_job(
            func=check_overdue_payments,
            trigger='cron',
            hour=11,
            minute=0,
            args=[app],
            id='check_overdue_payments',
            name='Check Overdue Payments',
            replace_existing=True
        )

        # Start the scheduler
        try:
            scheduler.start()
            app.logger.info('APScheduler started successfully')
        except Exception as e:
            app.logger.error(f'Error starting APScheduler: {e}')

    # Set scheduler as app attribute for later access/shutdown
    app.scheduler = scheduler

    # Set up error handlers
    from .errors import init_error_handlers
    init_error_handlers(app)
    
    # Error handlers for HTTP status codes
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.error(f"404 Not Found: {request.url}")
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Rollback any pending database transactions on 500 error
        app.logger.exception(f"500 Internal Server Error for URL: {request.url}")
        return render_template('errors/500.html'), 500

    # Jinja2 filters and globals available in all templates
    app.jinja_env.filters['currency'] = lambda value: f"KSh {value:,.2f}" if value is not None else "KSh 0.00"
    app.jinja_env.filters['phone'] = lambda number: f"+254{str(number)[-9:]}" if number and len(str(number)) >= 9 else ""
    
    app.jinja_env.globals.update(
        current_year=datetime.utcnow().year,
        site_name="REPT Kenya"
    )

    # Before request handler for offline mode detection
    @app.before_request
    def check_offline_mode():
        g.is_offline = not check_internet_connection()
        g.lang = babel.locale_selector_func()

    return app

def check_internet_connection():
    """
    Checks if there's an active internet connection by trying to reach Google.
    """
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except requests.RequestException:
        return False