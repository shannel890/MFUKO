# app/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
# app/routes.py

from flask import Blueprint, render_template, request, flash, redirect, url_for,current_app
from flask_login import login_required, current_user
from flask_security import roles_required # For role-based access control
from .models import db, User, Property, Tenant, Payment, County, AuditLog
# Assuming forms are defined in app/forms.py
from forms import ExtendRegisterForm, ExtendedLoginForm, UserProfileForm, PropertyForm, TenantForm, RecordPaymentForm
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import json
from flask_babel import lazy_gettext as _l

# Define your main Blueprint
main = Blueprint('main', __name__)

# --- Dashboard Route ---
@main.route('/')
@main.route('/dashboard')
@login_required # User must be logged in to access the dashboard
@roles_required('landlord') # Only landlords can access the main dashboard
def dashboard():
    """
    Renders the main dashboard with key metrics and recent payments.
    """
    # Initialize metrics with default values
    metrics = {
        'overdue_payments': 0,
        'total_collections': 0.00,
        'vacancy_rate': 0.00,
        'recent_transactions': 0 # This might need a specific count
    }
    recent_payments = []

    try:
        # Fetch properties owned by the current landlord
        landlord_properties = Property.query.filter_by(landlord_id=current_user.id).all()
        landlord_property_ids = [p.id for p in landlord_properties]

        if landlord_property_ids:
            # 1. Overdue Payments: Active tenants with confirmed rent due, but no confirmed payment for current month
            # This logic can be complex; simplifying for dashboard display
            # A more robust check would involve checking 'pending_due' payments from tasks.py
            # and comparing with confirmed payments.
            today = datetime.utcnow().date()
            current_month_start = today.replace(day=1)
            next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)

            overdue_tenants = Tenant.query.filter(
                Tenant.property_id.in_(landlord_property_ids),
                Tenant.status == 'active',
                # Check for tenants whose due date + grace period has passed
                # This requires more complex SQL or iterated Python logic to be precise
                # Simplified: count payments that are 'pending_due' and past their date
                # Or count active tenants who haven't paid for the current month
            ).all()

            overdue_count = 0
            for tenant in overdue_tenants:
                try:
                    due_date_this_month = today.replace(day=tenant.due_day_of_month)
                    effective_due_date = due_date_this_month + timedelta(days=tenant.grace_period_days)
                    
                    if today > effective_due_date:
                        # Check if a payment exists for this tenant for this month
                        payment_this_month = Payment.query.filter(
                            Payment.tenant_id == tenant.id,
                            Payment.payment_date.between(current_month_start, next_month_start - timedelta(days=1)),
                            Payment.status == 'confirmed'
                        ).first()
                        
                        if not payment_this_month:
                            overdue_count += 1
                except ValueError: # Handle cases where due_day_of_month is invalid for the current month
                    continue # Skip this tenant for now or handle specifically

            metrics['overdue_payments'] = overdue_count

            # 2. Total Collections (e.g., for the current month or year-to-date)
            # Let's do current month for simplicity
            total_collections_query = db.session.query(func.sum(Payment.amount)).filter(
                Payment.tenant_id.in_([t.id for t in Tenant.query.filter(Tenant.property_id.in_(landlord_property_ids)).all()]),
                Payment.status == 'confirmed',
                Payment.payment_date >= current_month_start,
                Payment.payment_date < next_month_start
            ).scalar()
            metrics['total_collections'] = total_collections_query if total_collections_query is not None else 0.00

            # 3. Vacancy Rate
            total_units = db.session.query(func.sum(Property.number_of_units)).filter(
                Property.id.in_(landlord_property_ids)
            ).scalar() or 0

            occupied_units = db.session.query(func.count(Tenant.id)).filter(
                Tenant.property_id.in_(landlord_property_ids),
                Tenant.status == 'active'
            ).scalar() or 0

            if total_units > 0:
                metrics['vacancy_rate'] = round(((total_units - occupied_units) / total_units) * 100, 2)
            else:
                metrics['vacancy_rate'] = 0.00 # Or 100 if no units

            # 4. Recent Transactions (count of confirmed payments in last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            metrics['recent_transactions'] = Payment.query.filter(
                Payment.tenant_id.in_([t.id for t in Tenant.query.filter(Tenant.property_id.in_(landlord_property_ids)).all()]),
                Payment.status == 'confirmed',
                Payment.payment_date >= seven_days_ago.date()
            ).count()

            # Recent Payments Table Data (last 5 confirmed payments)
            recent_payments_query = Payment.query.filter(
                Payment.tenant_id.in_([t.id for t in Tenant.query.filter(Tenant.property_id.in_(landlord_property_ids)).all()]),
                Payment.status == 'confirmed'
            ).order_by(Payment.payment_date.desc()).limit(5).all()

            for payment in recent_payments_query:
                tenant = payment.tenant
                property_name = tenant.property.name if tenant and tenant.property else _l('N/A')
                recent_payments.append({
                    'tenant_name': f"{tenant.first_name} {tenant.last_name}" if tenant else _l('Unknown Tenant'),
                    'property_name': property_name,
                    'amount': payment.amount,
                    'payment_date': payment.payment_date,
                    'status': payment.status
                })

    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard metrics for user {current_user.id}: {e}")
        flash(_l('Error loading dashboard data.'), 'danger')
        # Metrics will remain default 0 in case of error

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
    tenants = Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()
    return render_template('tenants/list.html', tenants=tenants)

@main.route('/tenants/add', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def tenant_add():
    form = TenantForm()
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
    if tenant.property.landlord_id != current_user.id:
        flash(_l('Access denied.'), 'danger')
        return redirect(url_for('main.tenants_list'))
    form = TenantForm(obj=tenant)
    form.property_id.choices = [(p.id, p.name) for p in Property.query.filter_by(landlord_id=current_user.id).all()]
    if form.validate_on_submit():
        form.populate_obj(tenant)
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
    form.tenant_id.choices = [(t.id, f"{t.first_name} {t.last_name}") 
                             for t in Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()]
    if form.validate_on_submit():
        payment = Payment(
            amount=form.amount.data,
            tenant_id=form.tenant_id.data,
            payment_method=form.payment_method.data,
            transaction_id=form.transaction_id.data,
            payment_date=form.payment_date.data or datetime.utcnow(),
            status='confirmed'
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
    tenant_ids = [t.id for t in Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()]
    payments = Payment.query.filter(Payment.tenant_id.in_(tenant_ids)).order_by(Payment.payment_date.desc()).all()
    return render_template('payments/history.html', payments=payments)

# --- Reports and Audit Routes ---
@main.route('/reports')
@login_required
@roles_required('landlord')
def reports():
    return render_template('reports/index.html')

@main.route('/audit-trail')
@login_required
@roles_required('landlord')
def audit_trail():
    logs = AuditLog.query.filter_by(user_id=current_user.id).order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit_trail.html', logs=logs)

# --- Set Language Route ---
@main.route('/set_language', methods=['POST'])
def set_language():
    lang = request.form.get('lang')
    if lang:
        session['lang'] = lang
        flash(_l('Language changed.'), 'success')
    return redirect(request.referrer or url_for('main.dashboard'))

# Add other route definitions here as needed