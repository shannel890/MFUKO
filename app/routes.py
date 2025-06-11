from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from flask_security import roles_required # For role-based access control
from .models import db, User, Property, Tenant, Payment, County, AuditLog
# Assuming forms are defined in app/forms.py
from forms import ExtendRegisterForm, ExtendedLoginForm, UserProfileForm
from datetime import datetime, timedelta
from sqlalchemy import func
import json # For serializing/deserializing audit log values

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    # Example metrics for dashboard
    total_properties = 0
    total_tenants = 0
    total_collected_this_month = 0.0
    overdue_payments_count = 0
    recent_transactions = [] # Placeholder for recent payments

    if current_user.has_role('landlord'): # Use has_role for Flask-Security roles
        properties = Property.query.filter_by(landlord_id=current_user.id).all()
        total_properties = len(properties)

        # Get all tenants for these properties
        property_ids = [p.id for p in properties]
        tenants = Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()
        total_tenants = len(tenants)

        # Calculate metrics for the current month
        today = datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Total collected this month
        collected_payments = Payment.query.join(Tenant).filter(
            Tenant.property_id.in_(property_ids),
            Payment.payment_date >= start_of_month,
            Payment.payment_date <= end_of_month,
            Payment.status == 'confirmed' # Only count confirmed payments
        ).with_entities(func.sum(Payment.amount)).scalar()
        total_collected_this_month = collected_payments if collected_payments is not None else 0.0

        # Overdue payments count
        # A payment is overdue if today is past its due date + grace period
        # This requires a more complex query joining Payments, Tenants, and considering lease dates
        # For simplicity in this snippet, let's count tenants with rent due before today and not yet confirmed paid
        overdue_tenants = 0
        for tenant in tenants:
            rent_due_date_this_month = today.replace(day=tenant.due_day_of_month)
            if today > (rent_due_date_this_month + timedelta(days=tenant.grace_period_days)):
                # Check if a confirmed payment exists for this period
                # This is a simplified check and would need more robust monthly tracking logic
                paid_this_period = Payment.query.filter(
                    Payment.tenant_id == tenant.id,
                    Payment.payment_date >= rent_due_date_this_month,
                    Payment.payment_date <= today,
                    Payment.status == 'confirmed'
                ).first()
                if not paid_this_period:
                    overdue_tenants += 1
        overdue_payments_count = overdue_tenants # Simplified to number of overdue tenants

        # Recent transactions (last 5 confirmed payments for landlord's properties)
        recent_transactions = Payment.query.join(Tenant).filter(
            Tenant.property_id.in_(property_ids),
            Payment.status == 'confirmed'
        ).order_by(Payment.payment_date.desc()).limit(5).all()

        return render_template(
            'dashboard.html',
            properties=properties,
            total_properties=total_properties,
            total_tenants=total_tenants,
            total_collected_this_month=total_collected_this_month,
            overdue_payments_count=overdue_payments_count,
            recent_transactions=recent_transactions
        )
    elif current_user.has_role('tenant'):
        # Tenant dashboard logic
        tenant = Tenant.query.filter_by(email=current_user.email).first() # Assuming email links user to tenant
        if tenant:
            # Show tenant's specific payments, next due date, etc.
            recent_payments = Payment.query.filter_by(tenant_id=tenant.id).order_by(Payment.payment_date.desc()).limit(5).all()
            return render_template('dashboard.html', tenant=tenant, recent_payments=recent_payments)
        flash("You are not linked to a tenant profile yet.", "warning")
        return redirect(url_for('main.index'))
    else:
        # Default for unassigned roles or other cases
        return redirect(url_for('main.index'))

# --- Property Management Routes ---
@main.route('/properties')
@login_required
@roles_required('landlord') # Only landlords can view properties
def property_list():
    properties = Property.query.filter_by(landlord_id=current_user.id).all()
    return render_template('properties/list.html', properties=properties)

@main.route('/property/add', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def add_property():
    # Form for adding property (Flask-WTF form needed)
    return render_template('properties/add_edit.html', title='Add New Property')

# --- Tenant Management Routes ---
@main.route('/tenants')
@login_required
@roles_required('landlord')
def tenant_list():
    # Filter tenants by landlord's properties
    property_ids = [p.id for p in Property.query.filter_by(landlord_id=current_user.id).all()]
    tenants = Tenant.query.filter(Tenant.property_id.in_(property_ids)).all()
    return render_template('tenants/list.html', tenants=tenants)

@main.route('/tenant/add', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def add_tenant():
    # Form for adding tenant (Flask-WTF form needed)
    return render_template('tenants/add_edit.html', title='Add New Tenant')

# --- Payment Recording Route ---
@main.route('/payments/record', methods=['GET', 'POST'])
@login_required
@roles_required('landlord')
def record_payment():
    # Form for recording payment (Flask-WTF form needed)
    # This form might include fields for tenant, amount, date, method, M-Pesa ID if manual
    return render_template('payments/record_payment.html', title='Record Payment')

# --- M-Pesa Callback Route ---
# This route would be publicly accessible for M-Pesa to send confirmation data
@main.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    # This is a critical endpoint for C2B payments
    # It receives transaction data from M-Pesa upon successful payment
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    # Log the incoming callback for audit/debugging
    # Process M-Pesa data: validate, extract M-Pesa ID, amount, sender, etc.
    # Match to pending payments or create new payment record
    # Update payment status in DB to 'confirmed'
    # Send confirmation SMS/Email to tenant/landlord

    # Example:
    # try:
    #     transaction_id = data['Body']['stkCallback']['CheckoutRequestID'] # Or similar
    #     amount = data['Body']['stkCallback']['CallbackMetadata']['Item'][0]['Value']
    #     phone_number = data['Body']['stkCallback']['CallbackMetadata']['Item'][4]['Value'] # Example path
    #     # Find tenant by phone_number, update payment or create new one
    #     # ...
    #     flash("M-Pesa payment confirmed successfully!", "success")
    #     return jsonify({"ResultCode": 0, "ResultDesc": "Callback received successfully"}), 200
    # except Exception as e:
    #     current_app.logger.error(f"Error processing M-Pesa callback: {e} Data: {json.dumps(data)}")
    #     return jsonify({"ResultCode": 1, "ResultDesc": "Error processing callback"}), 200 # M-Pesa usually expects 200 even on internal errors

    # For now, just acknowledge receipt
    print(f"M-Pesa Callback Received: {json.dumps(data, indent=2)}")
    return jsonify({"ResultCode": 0, "ResultDesc": "Callback received successfully"}), 200

# --- Audit Trail View ---
@main.route('/audit')
@login_required
@roles_required('landlord') # Only landlords can view audit trails
def audit_trail_view():
    # Fetch audit logs (e.g., last 100 or filterable)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('audit_trail.html', logs=logs)

# --- Reporting Route ---
@main.route('/reports', methods=['GET'])
@login_required
@roles_required('landlord')
def generate_reports():
    # This view will display filters and trigger report generation
    properties = Property.query.filter_by(landlord_id=current_user.id).all()
    # Logic to filter and display data based on query parameters (date_range, property_id, status)
    return render_template('reports/index.html', properties=properties)

@main.route('/reports/export/<format>', methods=['GET'])
@login_required
@roles_required('landlord')
def export_report(format):
    # Logic to fetch data based on filters, generate report in specified format (CSV, Excel, PDF)
    # Using pandas for data processing before export
    # Using ReportLab for PDF generation
    # Return file as a response
    flash(f"Generating {format.upper()} report...", "info")
    return redirect(url_for('main.generate_reports'))