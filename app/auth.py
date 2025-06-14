from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_security import current_user, roles_accepted, login_required
from flask_babel import gettext as _

from forms import ExtendedLoginForm, ExtendRegisterForm
from app.models import User, Role
from extension import user_datastore,db

auth = Blueprint('auth_ext', __name__)

@auth.after_request
def add_security_headers(response):
    """Add security headers to each response."""
    response.headers.update(current_app.config['SECURITY_HEADERS'])
    return response

@auth.app_context_processor
def security_context_processor():
    """Add security content processor."""
    return dict(
        admin_base_template=None,
        admin_view=False,
        h=None,
        get_url=None,
        _debug=False
    )

@auth.route('/register/landlord')
def register_landlord():
    """Register as a landlord."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('security.register', next=url_for('auth.assign_landlord_role')))

@auth.route('/register/tenant')
def register_tenant():
    """Register as a tenant."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('security.register', next=url_for('auth.assign_tenant_role')))

@auth.route('/assign-landlord-role')
@login_required
def assign_landlord_role():
    """Assign landlord role to newly registered user."""
    if not current_user.has_role('landlord'):
        landlord_role = Role.query.filter_by(name='landlord').first()
        if landlord_role:
            user_datastore.add_role_to_user(current_user, landlord_role)
            db.session.commit()
            flash(_('You have been registered as a landlord.'), 'success')
    return redirect(url_for('main.dashboard'))

@auth.route('/assign-tenant-role')
@login_required
def assign_tenant_role():
    """Assign tenant role to newly registered user."""
    if not current_user.has_role('tenant'):
        tenant_role = Role.query.filter_by(name='tenant').first()
        if tenant_role:
            user_datastore.add_role_to_user(current_user, tenant_role)
            db.session.commit()
            flash(_('You have been registered as a tenant.'), 'success')
    return redirect(url_for('main.dashboard'))

@auth.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('auth/profile.html', user=current_user)

@auth.route('/password-reset-required')
@login_required
def password_reset_required():
    """Force a password reset."""
    if not current_user.must_reset_password:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('security.change_password'))

# Role Management
@auth.route('/roles')
@login_required
@roles_accepted('admin')
def roles():
    """List all roles."""
    roles = Role.query.all()
    return render_template('auth/roles.html', roles=roles)
