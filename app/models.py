# from flask_login import UserMixin  <-- REMOVED: Replaced with Flask-Security's UserMixin
from flask_security import UserMixin, RoleMixin # Corrected import for UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from extension import db # Corrected import assuming db is initialized in app/__init__.py or a similar structure

# Define the many-to-many relationship table for users and roles
# THIS IS THE CORRECT AND ONLY DEFINITION NEEDED FOR roles_users
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

# Role model (unchanged)
class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    confirmed_at = db.Column(db.DateTime())

    # --- Flask-Security-Too User Tracking Fields (MUST BE PRESENT) ---
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    # --- End Flask-Security-Too Fields ---

    # Your custom fields
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    county_id = db.Column(db.Integer, db.ForeignKey('county.id'), nullable=True)
    language = db.Column(db.String(5), default='en')
    notification_preferences = db.Column(JSONB, nullable=True)

    # Relationships
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    county = db.relationship('County', backref='users', lazy=True)

    def __str__(self):
        return self.email

    def has_role(self, role):
        """Check if user has the specified role."""
        return any(r.name == role for r in self.roles)

    @property
    def full_name(self):
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}"

# --- DELETED: The redundant RolesUsers(db.Model) class definition ---
# You had:
# class RolesUsers(db.Model):
#     __tablename__ = 'roles_users'
#     id = db.Column(db.Integer(), primary_key=True)
#     user_id = db.Column('user_id', db.Integer(), db.ForeignKey('user.id'))
#     role_id = db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
# This class was causing the "Table 'roles_users' is already defined" error.
# The `db.Table` definition above is sufficient.

class County(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

    def __str__(self):
        return self.name

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    property_type = db.Column(db.String(50), nullable=True)
    number_of_units = db.Column(db.Integer, default=1)
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    landlord = db.relationship('User', backref=db.backref('properties', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    county = db.Column(db.String(100), nullable=False)
    amenities = db.Column(db.JSON, default=list)
    utility_bill_types = db.Column(db.JSON, default=list)
    unit_numbers = db.Column(db.JSON, default=list)
    deposit_amount = db.Column(db.Float, nullable=True)
    deposit_policy = db.Column(db.String(255), nullable=True)

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone_number = db.Column(db.String(20), nullable=False)
    national_id = db.Column(db.String(30), unique=True, nullable=True)
    status = db.Column(db.String(20), default='active')

    property_id = db.Column(db.Integer, db.ForeignKey('property.id'))
    property = db.relationship('Property', backref=db.backref('current_tenants', lazy=True))

    # Lease details
    rent_amount = db.Column(db.Float, nullable=False)
    due_day_of_month = db.Column(db.Integer, default=1)
    grace_period_days = db.Column(db.Integer, default=5)
    lease_start_date = db.Column(db.Date, nullable=False)
    lease_end_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
    tenant = db.relationship('Tenant', backref=db.backref('payments', lazy=True))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50), default='M-Pesa')
    status = db.Column(db.String(50), default='pending_confirmation')
    transaction_id = db.Column(db.String(100), unique=True, nullable=True)
    paybill_number = db.Column(db.String(20), nullable=True)
    shortcode = db.Column(db.String(20), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    fees = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    is_offline = db.Column(db.Boolean, default=False)
    sync_status = db.Column(db.String(20), default='synced')
    offline_reference = db.Column(db.String(100), nullable=True)
    receipt_number = db.Column(db.String(100), unique=True, nullable=True)
    payment_evidence = db.Column(db.String(255), nullable=True)
    payment_type = db.Column(db.String(20), default='rent')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(100), nullable=True)
    record_id = db.Column(db.Integer, nullable=True)
    old_value = db.Column(db.JSON, nullable=True)
    new_value = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id} at {self.timestamp}>'

class NotificationTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'sms' or 'email'
    subject_en = db.Column(db.String(255), nullable=True)  # For email only
    subject_sw = db.Column(db.String(255), nullable=True)  # For email only
    body_en = db.Column(db.Text, nullable=False)
    body_sw = db.Column(db.Text, nullable=False)
    variables = db.Column(JSONB, default=list)  # List of variables that can be used in template
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('notification_template.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(20), nullable=False)  # 'sms' or 'email'
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    variables = db.Column(JSONB, nullable=True)  # Variables used in this notification
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    template = db.relationship('NotificationTemplate', backref=db.backref('notifications', lazy=True))
    recipient = db.relationship('User', backref=db.backref('notifications', lazy=True))

class MpesaTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)
    merchant_request_id = db.Column(db.String(100), unique=True)
    checkout_request_id = db.Column(db.String(100), unique=True)
    result_code = db.Column(db.String(5), nullable=True)
    result_desc = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    mpesa_receipt_number = db.Column(db.String(50), unique=True, nullable=True)
    phone_number = db.Column(db.String(15), nullable=False)
    status = db.Column(db.String(20), default='initiated')  # initiated, completed, failed
    raw_request = db.Column(JSONB, nullable=True)
    raw_callback = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    payment = db.relationship('Payment', backref=db.backref('mpesa_transaction', uselist=False))

# Update Payment model with offline sync fields
class OfflinePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    local_reference = db.Column(db.String(100), nullable=False)
    sync_attempts = db.Column(db.Integer, default=0)
    last_sync_attempt = db.Column(db.DateTime, nullable=True)
    sync_error = db.Column(db.Text, nullable=True)
    offline_data = db.Column(JSONB, nullable=False)  # Stored offline payment data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    payment = db.relationship('Payment', backref=db.backref('offline_record', uselist=False))