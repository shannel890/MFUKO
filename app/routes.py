from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_security import roles_required # For role-based access control
from app.models import User, Property, Tenant, Payment, County, AuditLog
# Assuming forms are defined in app/forms.py (using relative import)
from forms import RegistrationForm, ExtendedLoginForm, UserProfileForm, PropertyForm, TenantForm, RecordPaymentForm
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import json
from flask_babel import lazy_gettext as _l
from extension import db

# Define your main Blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """
    Renders the landing page or redirects to the dashboard if the user is authenticated.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html', now=datetime.now())
# --- Register Page ---
from werkzeug.security import generate_password_hash # Import for hashing passwords

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data # This is the plain text password from the form
        first_name = form.first_name.data
        last_name = form.last_name.data
        # Safely get optional fields
        phone_number = form.phone_number.data if hasattr(form, 'phone_number') and form.phone_number.data else None
        county_id = form.county_id.data if hasattr(form, 'county_id') and form.county_id.data else None

        # Hash the password before creating the User object
        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password_hash=hashed_password, # Store the hashed password
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            county_id=county_id
        )
        db.session.add(user)
        db.session.commit() # Commit only if validation is successful

        flash(f'Registration for {user.username} successful! You can now log in.', 'success')
        return redirect(url_for('main.login')) # Redirect to login page upon success

    # If GET request or form validation fails, render the template
    return render_template('register.html', form=form)

@main.route('/dashboard')
@login_required
@roles_required('landlord')
def dashboard():
    """
    Renders the main dashboard with key metrics and recent payments for the logged-in landlord.
    """
    # Initialize metrics with default values
    metrics = {
        'overdue_payments': 0,
        'total_collections': 0.00,
        'vacancy_rate': 0.00,
        'recent_transactions': 0
    }
    recent_payments = []

    try:
        # Fetch properties owned by the current landlord
        landlord_properties = Property.query.filter_by(landlord_id=current_user.id).all()
        landlord_property_ids = [p.id for p in landlord_properties]

        if landlord_property_ids:
            # Fetch all active tenants associated with the landlord's properties once
            landlord_tenants = Tenant.query.filter(
                Tenant.property_id.in_(landlord_property_ids),
                Tenant.status == 'active'
            ).all()
            landlord_tenant_ids = [t.id for t in landlord_tenants]

            today = datetime.utcnow().date()
            current_month_start = today.replace(day=1)
            # Calculate next_month_start precisely for date range queries
            if today.month == 12:
                next_month_start = datetime(today.year + 1, 1, 1).date()
            else:
                next_month_start = datetime(today.year, today.month + 1, 1).date()


            # 1. Overdue Payments: Active tenants who haven't paid for the current month
            overdue_count = 0
            for tenant in landlord_tenants:
                try:
                    due_day = tenant.due_day_of_month
                    if due_day is None: # Ensure due_day_of_month is not None
                        current_app.logger.warning(f"Tenant {tenant.id} has no due_day_of_month set. Skipping overdue calculation for this tenant.")
                        continue

                    # Determine the exact due date for the current month for this tenant
                    try:
                        due_date_this_month = current_month_start.replace(day=due_day)
                    except ValueError:
                        # If due_day is too large for the current month, set to last day of month
                        last_day_of_month = (next_month_start - timedelta(days=1)).day
                        due_date_this_month = current_month_start.replace(day=last_day_of_month)

                    # Ensure grace_period_days is not None before adding
                    grace_period = tenant.grace_period_days if tenant.grace_period_days is not None else 0
                    effective_due_date = due_date_this_month + timedelta(days=grace_period)

                    if today > effective_due_date:
                        # Check if a 'confirmed' payment exists for this tenant for the current month
                        payment_this_month = Payment.query.filter(
                            Payment.tenant_id == tenant.id,
                            Payment.payment_date >= current_month_start,
                            Payment.payment_date < next_month_start,
                            Payment.status == 'confirmed'
                        ).first()
                        
                        if not payment_this_month:
                            overdue_count += 1
                except Exception as overdue_e: # Catch any other errors within this loop
                    current_app.logger.error(f"Error calculating overdue status for tenant {tenant.id}: {overdue_e}", exc_info=True)
                    continue # Skip this tenant but log the error

            metrics['overdue_payments'] = overdue_count

            # 2. Total Collections for the current month
            total_collections_query = db.session.query(func.sum(Payment.amount)).filter(
                Payment.tenant_id.in_(landlord_tenant_ids),
                Payment.status == 'confirmed',
                Payment.payment_date >= current_month_start,
                Payment.payment_date < next_month_start
            ).scalar()
            metrics['total_collections'] = total_collections_query if total_collections_query is not None else 0.00

            # 3. Vacancy Rate
            total_units = db.session.query(func.sum(Property.number_of_units)).filter(
                Property.id.in_(landlord_property_ids)
            ).scalar() or 0

            occupied_units = len(landlord_tenants) # We already filtered for active tenants earlier

            if total_units > 0:
                metrics['vacancy_rate'] = round(((total_units - occupied_units) / total_units) * 100, 2)
            else:
                metrics['vacancy_rate'] = 0.00 # Or 100 if no units to avoid division by zero

            # 4. Recent Transactions (count of confirmed payments in last 7 days)
            seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
            metrics['recent_transactions'] = Payment.query.filter(
                Payment.tenant_id.in_(landlord_tenant_ids),
                Payment.status == 'confirmed',
                Payment.payment_date >= seven_days_ago
            ).count()

            # Recent Payments Table Data (last 5 confirmed payments)
            recent_payments_query = Payment.query.filter(
                Payment.tenant_id.in_(landlord_tenant_ids),
                Payment.status == 'confirmed'
            ).order_by(Payment.payment_date.desc()).limit(5).all()

            for payment in recent_payments_query:
                tenant = payment.tenant
                # Defensive check for tenant and property existence
                property_name = tenant.property.name if tenant and tenant.property else _l('N/A')
                recent_payments.append({
                    'tenant_name': f"{tenant.first_name} {tenant.last_name}" if tenant else _l('Unknown Tenant'),
                    'property_name': property_name,
                    'amount': payment.amount,
                    'payment_date': payment.payment_date,
                    'status': payment.status
                })

    except Exception as e:
        # Log the full traceback for any unhandled exception in the dashboard logic
        current_app.logger.exception(f"Critical error fetching dashboard metrics for user {current_user.id}.")
        flash(_l('Error loading dashboard data. Please try again later.'), 'danger')
        # Metrics will remain default 0 in case of error, and recent_payments will be empty

    # This render_template call itself could fail if template is missing or context is bad.
    # The global error handler in __init__.py should catch those.
    return render_template('dashboard.html', metrics=metrics, recent_payments=recent_payments)

# --- Properties Routes ---
@main.route('/properties')
@login_required
@roles_required('landlord')
def properties_list():
    properties = Property.query.filter_by(landlord_id=current_user.id).all()
    return render_template('properties/list.html', properties=properties)

@main.route('/properties/add', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def property_add():
    form = PropertyForm()
    if form.validate_on_submit():
        property = Property(
            name=form.name.data,
            address=form.address.data,
            property_type=form.property_type.data,
            number_of_units=form.number_of_units.data,
            landlord_id=current_user.id
        )
        db.session.add(property)
        db.session.commit()
        flash(_l('Property added successfully.'), 'success')
        return redirect(url_for('main.properties_list'))
    return render_template('properties/add_edit.html', form=form, edit=False)

@main.route('/properties/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def property_edit(id):
    property = Property.query.get_or_404(id)
    # Ensure the landlord owns this property
    if property.landlord_id != current_user.id:
        flash(_l('Access denied.'), 'danger')
        return redirect(url_for('main.properties_list'))
    form = PropertyForm(obj=property)
    if form.validate_on_submit():
        property.name = form.name.data
        property.address = form.address.data
        property.property_type = form.property_type.data
        property.number_of_units = form.number_of_units.data
        db.session.commit()
        flash(_l('Property updated successfully.'), 'success')
        return redirect(url_for('main.properties_list'))
    return render_template('properties/add_edit.html', form=form, edit=True)

# --- Tenants Routes ---
@main.route('/tenants')
@login_required
@roles_required('landlord')
def tenants_list():
    landlord_properties = Property.query.filter_by(landlord_id=current_user.id).all()
    property_ids = [p.id for p in landlord_properties]
    # Filter tenants by properties belonging to the current landlord
    tenants = Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()
    return render_template('tenants/list.html', tenants=tenants)

@main.route('/tenants/add', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def tenant_add():
    form = TenantForm()
    # Populate property choices with only properties belonging to the current landlord
    form.property_id.choices = [(p.id, p.name) for p in Property.query.filter_by(landlord_id=current_user.id).all()]
    if form.validate_on_submit():
        tenant = Tenant(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone_number=form.phone_number.data,
            property_id=form.property_id.data,
            rent_amount=form.rent_amount.data,
            due_day_of_month=form.due_day_of_month.data,
            grace_period_days=form.grace_period_days.data,
            lease_start_date=form.lease_start_date.data,
            lease_end_date=form.lease_end_date.data
        )
        db.session.add(tenant)
        db.session.commit()
        flash(_l('Tenant added successfully.'), 'success')
        return redirect(url_for('main.tenants_list'))
    return render_template('tenants/add_edit.html', form=form, edit=False)

@main.route('/tenants/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def tenant_edit(id):
    tenant = Tenant.query.get_or_404(id)
    # Ensure the tenant is associated with a property owned by the current landlord
    if tenant.property.landlord_id != current_user.id:
        flash(_l('Access denied.'), 'danger')
        return redirect(url_for('main.tenants_list'))
    form = TenantForm(obj=tenant)
    form.property_id.choices = [(p.id, p.name) for p in Property.query.filter_by(landlord_id=current_user.id).all()]
    if form.validate_on_submit():
        form.populate_obj(tenant) # Populate all fields from the form object
        db.session.commit()
        flash(_l('Tenant updated successfully.'), 'success')
        return redirect(url_for('main.tenants_list'))
    return render_template('tenants/add_edit.html', form=form, edit=True)

# --- Payments Routes ---
@main.route('/payments/record', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def record_payment():
    form = RecordPaymentForm()
    landlord_properties = Property.query.filter_by(landlord_id=current_user.id).all()
    property_ids = [p.id for p in landlord_properties]
    # Populate tenant choices only for tenants associated with the current landlord's properties
    form.tenant_id.choices = [(t.id, f"{t.first_name} {t.last_name}") 
                             for t in Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()]
    if form.validate_on_submit():
        payment = Payment(
            amount=form.amount.data,
            tenant_id=form.tenant_id.data,
            payment_method=form.payment_method.data,
            transaction_id=form.transaction_id.data,
            payment_date=form.payment_date.data or datetime.utcnow().date(), # Use .date() for consistency
            status='confirmed' # Manually recorded payments are confirmed by default
        )
        db.session.add(payment)
        db.session.commit()
        flash(_l('Payment recorded successfully.'), 'success')
        return redirect(url_for('main.payments_history'))
    return render_template('payments/record_payment.html', form=form)

@main.route('/payments/history')
@login_required
@roles_required('landlord')
def payments_history():
    landlord_properties = Property.query.filter_by(landlord_id=current_user.id).all()
    property_ids = [p.id for p in landlord_properties]
    # Filter payments by tenants associated with the current landlord's properties
    tenant_ids = [t.id for t in Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()]
    payments = Payment.query.filter(Payment.tenant_id.in_(tenant_ids)).order_by(Payment.payment_date.desc()).all()
    return render_template('payments/history.html', payments=payments)

# --- Reports and Audit Routes ---
@main.route('/reports')
@roles_required('landlord')
def reports():
    return render_template('reports/index.html')

@main.route('/audit-trail')
@login_required
@roles_required('landlord')
def audit_trail():
    # This currently shows audit logs for actions performed by the current user.
    # If you intend to show logs for actions *affecting* properties owned by the landlord,
    # or all system-wide logs, the query would need to be adjusted.
    logs = AuditLog.query.filter_by(user_id=current_user.id).order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit_trail.html', logs=logs)

# --- Set Language Route ---
@main.route('/set_language', methods=['POST'])
def set_language():
    lang = request.form.get('lang')
    if lang in current_app.config['LANGUAGES']:
        response = redirect(request.referrer or url_for('main.index')) # Corrected: 'main.landing' -> 'main.index'
        response.set_cookie('lang', lang)
        # If storing user language preference in DB (uncomment if you add User.language field)
        # if current_user.is_authenticated:
        #    current_user.language = lang
        #    db.session.commit()
        flash(_l('Language changed successfully!'), 'success')
        return response
    flash(_l('Invalid language selected.'), 'danger')
    return redirect(request.referrer or url_for('main.index')) # Corrected: 'main.landing' -> 'main.index'

# Add other route definitions here as needed