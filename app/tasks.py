# app/tasks.py

import requests
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, and_
import json
from flask_babel import lazy_gettext as _l

# Import your models and database instance
from extension import db, mail # Assuming 'db' and 'mail' are initialized in app/__init__.py
from app.models import Tenant, Property, Payment, User, AuditLog # Import all necessary models
from api import mpesa_api # Assuming you'll have M-Pesa API client logic here
from utils import send_email, send_sms # Assuming these utility functions exist


def refresh_mpesa_token():
    """
    Schedules an M-Pesa OAuth token refresh.
    This task should run periodically (e.g., every hour).
    """
    app = current_app._get_current_object() # Get the actual app object
    with app.app_context():
        consumer_key = app.config.get('MPESA_CONSUMER_KEY')
        consumer_secret = app.config.get('MPESA_CONSUMER_SECRET')
        auth_url = app.config.get('MPESA_AUTH_URL', 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials')

        if not consumer_key or not consumer_secret:
            app.logger.error("MPESA_CONSUMER_KEY or MPESA_CONSUMER_SECRET not configured.")
            return

        try:
            headers = {
                'Authorization': 'Basic ' + requests.auth.HTTPBasicAuth(consumer_key, consumer_secret).headeval(),
                'Content-Type': 'application/json'
            }
            response = requests.get(auth_url, headers=headers)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            access_token = data.get('access_token')
            expires_in = data.get('expires_in', 3599) # Default to just under 1 hour

            if access_token:
                # Store the token globally or in app.config
                # A more robust solution might store this in the DB if multiple instances are run
                app.config['MPESA_ACCESS_TOKEN'] = access_token
                app.config['MPESA_TOKEN_EXPIRATION'] = datetime.utcnow() + timedelta(seconds=expires_in)
                app.logger.info("M-Pesa access token refreshed successfully.")

                # You might also update the mpesa_api client with the new token
                mpesa_api.set_access_token(access_token)
            else:
                app.logger.warning(f"M-Pesa token refresh failed: No access_token in response. Data: {data}")

        except requests.exceptions.RequestException as e:
            app.logger.error(f"Failed to refresh M-Pesa token: {e}")
        except json.JSONDecodeError:
            app.logger.error(f"Failed to decode M-Pesa token response JSON: {response.text}")
        except Exception as e:
            app.logger.error(f"An unexpected error occurred during M-Pesa token refresh: {e}")


def check_and_generate_rent_invoices():
    """
    Periodically checks active tenants and generates 'pending_due' payment records
    for the upcoming month's rent. This acts as an internal 'invoice'.
    Runs, for example, on the 25th of each month.
    """
    app = current_app._get_current_object()
    with app.app_context():
        app.logger.info("Running scheduled job: Check and generate rent invoices.")
        today = datetime.utcnow().date()
        # Consider generating for the NEXT month, e.g., on the 25th of current month
        # to prepare for payments due on 1st of next month.
        next_month_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1)

        active_tenants = Tenant.query.filter_by(status='active').all()

        for tenant in active_tenants:
            # Determine the expected due date for the upcoming month
            try:
                expected_due_date = next_month_date.replace(day=tenant.due_day_of_month)
            except ValueError: # Handle cases where day might be 30/31 in shorter months
                expected_due_date = next_month_date.replace(day=28) # Default to 28th if invalid day

            # Check if a payment for this period (month and year) already exists
            # This is a simplified check and might need to be more robust for partial payments etc.
            existing_payment_this_period = Payment.query.filter(
                Payment.tenant_id == tenant.id,
                Payment.payment_date.between(expected_due_date.replace(day=1), (expected_due_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)),
                Payment.status.in_(['confirmed', 'partially_paid']) # Consider already confirmed or partially paid
            ).first()

            if not existing_payment_this_period:
                # Create a pending payment record for this month's expected rent
                new_payment = Payment(
                    amount=tenant.rent_amount,
                    tenant_id=tenant.id,
                    payment_date=expected_due_date,
                    payment_method='Scheduled', # Indicate it's an internal scheduled entry
                    status='pending_due', # Custom status for expected payments
                    description=f"Monthly rent due for {expected_due_date.strftime('%B %Y')}"
                )
                db.session.add(new_payment)
                app.logger.info(f"Generated pending rent record for tenant {tenant.id} for {expected_due_date.strftime('%B %Y')}.")
            else:
                app.logger.info(f"Skipping rent record generation for tenant {tenant.id} for {expected_due_date.strftime('%B %Y')}: Payment already exists or confirmed.")
        
        try:
            db.session.commit()
            app.logger.info("Successfully generated rent invoices and committed to DB.")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to commit rent invoice generation: {e}")


def send_upcoming_rent_reminders():
    """
    Sends SMS/Email reminders to tenants whose rent is due in the next few days.
    Runs daily (e.g., at 6 AM).
    """
    app = current_app._get_current_object()
    with app.app_context():
        app.logger.info("Running scheduled job: Send upcoming rent reminders.")
        today = datetime.utcnow().date()
        
        # Tenants whose rent is due within the next N days (e.g., 3 days)
        # and haven't paid yet for the current month.
        reminder_days_before = 3 # Configure this in app.config if needed

        tenants_to_remind = []
        for tenant in Tenant.query.filter_by(status='active').all():
            if not tenant.due_day_of_month: # Skip if due day is not set
                continue

            # Calculate rent due date for the current month
            try:
                rent_due_date_this_month = today.replace(day=tenant.due_day_of_month)
            except ValueError:
                rent_due_date_this_month = today.replace(day=28) # Fallback

            # Only remind if the due date is in the future AND within the reminder window
            if rent_due_date_this_month > today and \
               (rent_due_date_this_month - today).days <= reminder_days_before:

                # Check if tenant has already made a confirmed payment for this month's cycle
                # (Simplified check: looks for any confirmed payment within the current month)
                payment_confirmed = Payment.query.filter(
                    Payment.tenant_id == tenant.id,
                    Payment.payment_date.between(today.replace(day=1), (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)),
                    Payment.status == 'confirmed'
                ).first()

                # Also, check if a reminder for this period was already sent.
                # A robust solution might use a 'reminders_sent' table or a flag on the Payment record.
                # For simplicity, we'll assume no duplicate sending for now.
                
                if not payment_confirmed:
                    tenants_to_remind.append(tenant)

        for tenant in tenants_to_remind:
            try:
                message = _l("Hi {tenant_name}, just a friendly reminder that your rent of KES {amount:.2f} for {property_name} is due on {due_date}. Please pay via M-Pesa PayBill {paybill_number} Account {account_number}. Thank you!",
                             tenant_name=f"{tenant.first_name} {tenant.last_name}",
                             amount=tenant.rent_amount,
                             property_name=tenant.property.name, # Assuming tenant.property is loaded
                             due_date=rent_due_date_this_month.strftime('%Y-%m-%d'),
                             paybill_number=app.config.get('MPESA_PAYBILL', 'YOUR_PAYBILL'),
                             account_number=f"TENANT-{tenant.id}" # Or actual tenant account number
                            )

                send_sms(tenant.phone_number, message)
                send_email(tenant.email, _l("Rent Reminder"), message) # Only if email is not None
                app.logger.info(f"Sent upcoming rent reminder to tenant {tenant.id}.")
                # TODO: Add a mechanism to mark that this reminder was sent to prevent duplicates
            except Exception as e:
                app.logger.error(f"Failed to send upcoming rent reminder to tenant {tenant.id}: {e}")


def send_overdue_reminders():
    """
    Sends SMS/Email reminders to tenants with overdue payments.
    Runs daily (e.g., at 9 AM).
    """
    app = current_app._get_current_object()
    with app.app_context():
        app.logger.info("Running scheduled job: Send overdue reminders.")
        today = datetime.utcnow().date()

        overdue_tenants = []
        for tenant in Tenant.query.filter_by(status='active').all():
            if not tenant.due_day_of_month or not tenant.grace_period_days:
                continue

            # Calculate the effective due date (due day + grace period)
            try:
                effective_due_date_this_month = today.replace(day=tenant.due_day_of_month) + timedelta(days=tenant.grace_period_days)
            except ValueError:
                 effective_due_date_this_month = today.replace(day=28) + timedelta(days=tenant.grace_period_days) # Fallback

            # Check if the payment is overdue (today is past effective due date)
            if today > effective_due_date_this_month:
                # Check if tenant has made a confirmed payment for the current month
                payment_confirmed = Payment.query.filter(
                    Payment.tenant_id == tenant.id,
                    Payment.payment_date.between(today.replace(day=1), (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)),
                    Payment.status == 'confirmed'
                ).first()

                # If no confirmed payment, and no overdue reminder for this period already sent
                if not payment_confirmed:
                    overdue_tenants.append(tenant)

        for tenant in overdue_tenants:
            try:
                # You might want to send different messages for different stages of overdue
                message = _l("URGENT: Hi {tenant_name}, your rent of KES {amount:.2f} for {property_name} due on {due_date} is now overdue. Please make your payment immediately to M-Pesa PayBill {paybill_number} Account {account_number} to avoid further penalties. Thank you!",
                             tenant_name=f"{tenant.first_name} {tenant.last_name}",
                             amount=tenant.rent_amount,
                             property_name=tenant.property.name,
                             due_date=effective_due_date_this_month.strftime('%Y-%m-%d'),
                             paybill_number=app.config.get('MPESA_PAYBILL', 'YOUR_PAYBILL'),
                             account_number=f"TENANT-{tenant.id}"
                            )

                send_sms(tenant.phone_number, message)
                send_email(tenant.email, _l("URGENT: Overdue Rent Notice"), message)
                app.logger.warning(f"Sent overdue reminder to tenant {tenant.id}.")
                # TODO: Add a mechanism to mark that this overdue reminder was sent
                # or log overdue status change
            except Exception as e:
                app.logger.error(f"Failed to send overdue reminder to tenant {tenant.id}: {e}")