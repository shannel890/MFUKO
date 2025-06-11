from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Using StringField for username in forms, but email is primary identifier for Flask-Security-Too usually
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255)) # Flask-Security-Too handles hashing
    active = db.Column(db.Boolean(), default=True) # For account activation/deactivation
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False) # Required by Flask-Security-Too
    confirmed_at = db.Column(db.DateTime()) # For email confirmation
    roles = db.relationship('Role', secondary='roles_users', backref=db.backref('users', lazy='dynamic'))

    # Enhanced fields from ExtendRegisterForm
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True) # Made nullable as it's optional
    county_id = db.Column(db.Integer, db.ForeignKey('county.id'), nullable=True) # Assuming county is optional or can be added later

class Role(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class RolesUsers(db.Model):
    __tablename__ = 'roles_users'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column('user_id', db.Integer(), db.ForeignKey('user.id'))
    role_id = db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))

class County(db.Model): # Assuming a County model exists for the SelectField
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    property_type = db.Column(db.String(50), nullable=True) # e.g., Apartment, House, Commercial
    number_of_units = db.Column(db.Integer, default=1)
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    landlord = db.relationship('User', backref=db.backref('properties', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone_number = db.Column(db.String(20), nullable=False)
    national_id = db.Column(db.String(30), unique=True, nullable=True)
    status = db.Column(db.String(20), default='active') # e.g., 'active', 'vacated', 'evicted'

    property_id = db.Column(db.Integer, db.ForeignKey('property.id'))
    property = db.relationship('Property', backref=db.backref('current_tenants', lazy=True)) # 'current_tenants' for clarity

    # Lease details
    rent_amount = db.Column(db.Float, nullable=False)
    due_day_of_month = db.Column(db.Integer, default=1) # E.g., 1st of the month
    grace_period_days = db.Column(db.Integer, default=5)
    lease_start_date = db.Column(db.Date, nullable=False)
    lease_end_date = db.Column(db.Date, nullable=True) # Nullable for month-to-month

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
    tenant = db.relationship('Tenant', backref=db.backref('payments', lazy=True))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50), default='M-Pesa') # e.g., 'M-Pesa', 'Cash', 'Bank Transfer'
    status = db.Column(db.String(50), default='pending_confirmation') # 'pending_confirmation', 'confirmed', 'failed', 'reconciled'
    transaction_id = db.Column(db.String(100), unique=True, nullable=True) # M-Pesa transaction ID
    paybill_number = db.Column(db.String(20), nullable=True) # PayBill used for transaction
    shortcode = db.Column(db.String(20), nullable=True) # Shortcode if applicable
    account_number = db.Column(db.String(50), nullable=True) # Account number used by tenant
    fees = db.Column(db.Float, default=0.0) # Transaction fees
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('audit_logs'))
    action = db.Column(db.String(100), nullable=False) # e.g., 'LOGIN', 'LOGOUT', 'PROPERTY_CREATE', 'PAYMENT_UPDATE'
    table_name = db.Column(db.String(100), nullable=True) # e.g., 'property', 'tenant', 'payment'
    record_id = db.Column(db.Integer, nullable=True) # ID of the record affected
    old_value = db.Column(db.Text, nullable=True) # JSON representation of old data
    new_value = db.Column(db.Text, nullable=True) # JSON representation of new data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True) # IPv4 or IPv6
    details = db.Column(db.Text, nullable=True)