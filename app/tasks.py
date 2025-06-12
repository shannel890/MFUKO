# app/tasks.py

import requests
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, and_
import json
from flask_babel import lazy_gettext as _l

# Import your models and database instance
from . import db, mail
from .models import Tenant, Property, Payment, User, AuditLog

# THE FIX IS HERE: Use a relative import for your local 'api' module
from .api import mpesa_api # Corrected import

from .utils import send_email, send_sms # Assuming these utility functions exist

# ... rest of your tasks.py code ...

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
    Generate rent invoices for all active tenants on 1st of the month.
    """
    app = current_app._get_current_object()
    with app.app_context():
        try:
            today = datetime.utcnow().date()
            tenants = Tenant.query.filter_by(status='active').all()
            
            for tenant in tenants:
                # Check if a rent payment record already exists for this month
                exists = Payment.query.filter(
                    and_(
                        Payment.tenant_id == tenant.id,
                        Payment.payment_type == 'rent',
                        Payment.status.in_(['pending_confirmation', 'confirmed']),
                        Payment.payment_date.between(
                            datetime(today.year, today.month, 1),
                            datetime(today.year, today.month + 1, 1) if today.month < 12 
                            else datetime(today.year + 1, 1, 1)
                        )
                    )
                ).first()
                
                if not exists:
                    new_payment = Payment(
                        tenant_id=tenant.id,
                        amount=tenant.rent_amount,
                        payment_type='rent',
                        status='pending_confirmation',
                        payment_date=datetime(today.year, today.month, tenant.due_day_of_month)
                    )
                    db.session.add(new_payment)
                    
                    # Send notification if enabled
                    if tenant.email and tenant.user.notification_preferences.get('email', True):
                        send_email(
                            subject=_l("Rent Due for %(month)s", month=today.strftime('%B %Y')),
                            recipient=tenant.email,
                            template='email/rent_due',
                            amount=tenant.rent_amount,
                            due_date=new_payment.payment_date.strftime('%d/%m/%Y'),
                            tenant=tenant
                        )
                    
                    if tenant.phone_number and tenant.user.notification_preferences.get('sms', True):
                        send_sms(
                            to=tenant.phone_number,
                            message=_l("Rent of KSh %(amount).2f is due on %(date)s. Pay to Paybill %(paybill)s, Account: %(property)s-%(tenant)s",
                                amount=tenant.rent_amount,
                                date=new_payment.payment_date.strftime('%d/%m/%Y'),
                                paybill=app.config['MPESA_PAYBILL'],
                                property=tenant.property.name,
                                tenant=tenant.id)
                        )
            
            db.session.commit()
            app.logger.info("Successfully generated rent invoices.")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to generate rent invoices: {e}")


def send_payment_reminders():
    """Send payment reminders to tenants."""
    app = current_app._get_current_object()
    with app.app_context():
        try:
            today = datetime.utcnow().date()
            reminder_days = app.config.get('PAYMENT_REMINDER_DAYS', [5, 3, 1])
            
            # Get all pending payments
            pending_payments = Payment.query.filter(
                and_(
                    Payment.status == 'pending_confirmation',
                    Payment.payment_date >= today,
                    Payment.payment_date <= today + timedelta(days=max(reminder_days))
                )
            ).all()
            
            for payment in pending_payments:
                days_until_due = (payment.payment_date.date() - today).days
                
                if days_until_due in reminder_days:
                    tenant = payment.tenant
                    
                    # Send email reminder
                    if tenant.email and tenant.user.notification_preferences.get('email', True):
                        send_email(
                            subject=_l("Rent Payment Reminder - Due in %(days)d days", days=days_until_due),
                            recipient=tenant.email,
                            template='email/payment_reminder',
                            payment=payment,
                            tenant=tenant,
                            days_until_due=days_until_due
                        )
                    
                    # Send SMS reminder
                    if tenant.phone_number and tenant.user.notification_preferences.get('sms', True):
                        send_sms(
                            to=tenant.phone_number,
                            message=_l("Reminder: Rent payment of KSh %(amount).2f is due in %(days)d days. Pay to Paybill %(paybill)s, Account: %(property)s-%(tenant)s",
                                amount=payment.amount,
                                days=days_until_due,
                                paybill=app.config['MPESA_PAYBILL'],
                                property=tenant.property.name,
                                tenant=tenant.id)
                        )
            
            app.logger.info("Successfully sent payment reminders.")
        except Exception as e:
            app.logger.error(f"Failed to send payment reminders: {e}")

def sync_offline_payments():
    """Sync offline payments when internet connection is available."""
    app = current_app._get_current_object()
    with app.app_context():
        try:
            offline_payments = Payment.query.filter_by(
                is_offline=True,
                sync_status='pending_sync'
            ).limit(app.config.get('OFFLINE_CACHE_LIMIT', 1000)).all()
            
            for payment in offline_payments:
                try:
                    # Verify payment with M-Pesa API if it's an M-Pesa payment
                    if payment.payment_method == 'M-Pesa' and payment.transaction_id:
                        mpesa_api.verify_transaction(payment.transaction_id)
                    
                    payment.sync_status = 'synced'
                    payment.is_offline = False
                    db.session.add(payment)
                    
                    # Create audit log
                    audit_log = AuditLog(
                        user_id=payment.tenant.user_id,
                        action='PAYMENT_SYNC',
                        table_name='payment',
                        record_id=payment.id,
                        details=f"Payment {payment.id} synced from offline mode"
                    )
                    db.session.add(audit_log)
                    
                except Exception as sync_error:
                    app.logger.error(f"Failed to sync payment {payment.id}: {sync_error}")
                    payment.sync_status = 'sync_failed'
                    db.session.add(payment)
            
            db.session.commit()
            app.logger.info("Successfully synced offline payments.")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to sync offline payments: {e}")

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

def check_overdue_payments():
    """Stub for overdue payments check. Implement logic as needed."""
    pass