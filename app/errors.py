from flask import render_template
from flask_babel import _

def init_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', title=_('Page Not Found')), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html', title=_('Server Error')), 500
