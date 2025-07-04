# app/forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField, # Keep if you use Flask-Security's default password field
    SubmitField,
    BooleanField,
    SelectField,
    TelField,
    DecimalField, # For amounts
    DateField,    # For dates
    TextAreaField,
    IntegerField  # For numbers
)
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    NumberRange,
    Optional,
    ValidationError,
    EqualTo, # Custom validator for phone numbers
    Regexp # For more specific pattern matching if needed
)
from flask_security.forms import  LoginForm, RegisterForm
from flask_wtf import FlaskForm
from flask_babel import lazy_gettext as _l

class ExtendedRegisterForm(RegisterForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone_number = StringField('Phone Number', validators=[Length(max=15)])
    county_id = SelectField('County', coerce=int, validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
   
    submit = SubmitField(_l('Register'))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import County  # import here to avoid circular imports
        self.county_id.choices = [(c.id, c.name) for c in County.query.order_by(County.name).all()]


try:
    from app.models import County, Property, Tenant
except ImportError:
    # Fallback mock classes for environments where models might not be instantly available
    # during initial forms.py import (e.g., some shell contexts, or if db isn't fully set up yet)
    # In a fully running Flask app, these should successfully import.
    print("Warning: Could not import models directly in forms.py. Dynamic choices might rely on app context.")
    class County:
        id = 0
        name = "Default County"
        @staticmethod
        def query(): return type('', (), {'filter_by': lambda **kw: type('', (), {'all': lambda: []})(), 'order_by': lambda *a: type('', (), {'all': lambda: []})()})()
    class Property:
        id = 0
        name = "Default Property"
        @staticmethod
        def query(): return type('', (), {'filter_by': lambda **kw: type('', (), {'all': lambda: []})(), 'order_by': lambda *a: type('', (), {'all': lambda: []})()})()
    class Tenant:
        id = 0
        name = "Default Tenant"
        @staticmethod
        def query(): return type('', (), {'filter_by': lambda **kw: type('', (), {'all': lambda: []})(), 'order_by': lambda *a: type('', (), {'all': lambda: []})()})()


# --- Custom Validators ---
def validate_phone_number_format(form, field):
    """Custom validator for phone number: checks digits only and minimum length."""
    if field.data:
        digits_only = ''.join(filter(str.isdigit, field.data))
        if not digits_only.isdigit() and digits_only: # Check if it's not all digits, but not empty string
            raise ValidationError(_l('Phone number must contain only digits.'))
        if len(digits_only) < 9:
            raise ValidationError(_l('Phone number must contain at least 9 digits (excluding country code).'))
        field.data = digits_only # Clean the data for storage

def validate_date_order(form, field):
    """Custom validator to ensure end date is not before start date."""
    if form.lease_start_date.data and field.data and field.data < form.lease_start_date.data:
        raise ValidationError(_l('Lease end date cannot be before lease start date.'))


# --- Authentication Forms (Extending Flask-Security-Too) ---


class ExtendedLoginForm(LoginForm):
    """Enhanced login form with better styling support."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply render_kw for styling and autocomplete attributes
        self.email.render_kw = {
            'placeholder': _l('Enter your email address'),
            'class': 'form-control form-control-lg',
            'autocomplete': 'username'
        }
        self.password.render_kw = {
            'placeholder': _l('Enter your password'),
            'class': 'form-control form-control-lg',
            'autocomplete': 'current-password'
        }
        self.remember.render_kw = {
            'class': 'form-check-input'
        }
        # Flask-Security's forms usually provide a default submit field,
        # but you can customize its render_kw if needed.
        if hasattr(self, 'submit') and self.submit:
            self.submit.render_kw = {
                'class': 'btn btn-primary btn-lg'
            }

# --- User Profile Form ---
class UserProfileForm(FlaskForm):
    """Form for users to update their profile information."""
    first_name = StringField(
        _l('First Name'),
        validators=[
            DataRequired(_l('First name is required.')),
            Length(min=2, max=50, message=_l('First name must be between 2 and 50 characters.'))
        ],
        render_kw={"placeholder": _l("Your first name"), "autocomplete": "given-name"}
    )

    last_name = StringField(
        _l('Last Name'),
        validators=[
            DataRequired(_l('Last name is required.')),
            Length(min=2, max=50, message=_l('Last name must be between 2 and 50 characters.'))
        ],
        render_kw={"placeholder": _l("Your last name"), "autocomplete": "family-name"}
    )

    phone_number = TelField(
        _l('Phone Number'),
        validators=[
            Optional(),
            Length(min=9, max=20, message=_l('Phone number must be between 9 and 20 characters.')),
            validate_phone_number_format
        ],
        render_kw={"placeholder": _l("e.g., 0712345678"), "autocomplete": "tel-national"}
    )

    submit = SubmitField(_l('Update Profile'))


# --- Property Management Form ---
class PropertyForm(FlaskForm):
    """Form for landlords to add or edit property details."""
    name = StringField(
        _l('Property Name'),
        validators=[
            DataRequired(_l('Property name is required.')),
            Length(min=3, max=100, message=_l('Name must be between 3 and 100 characters.'))
        ],
        render_kw={"placeholder": _l("e.g., Sunny Apartments, Kilimani Block A")}
    )

    address = StringField(
        _l('Address'),
        validators=[
            DataRequired(_l('Address is required.')),
            Length(min=5, max=255, message=_l('Address must be between 5 and 255 characters.'))
        ],
        render_kw={"placeholder": _l("e.g., Plot 123, Off Ring Road, Nairobi")}
    )

    property_type = SelectField(
        _l('Property Type'),
        validators=[DataRequired(_l('Property type is required.'))],
        choices=[
            ('', _l('Select Type...')),
            ('Apartment', _l('Apartment')),
            ('House', _l('House')),
            ('Commercial', _l('Commercial')),
            ('Other', _l('Other'))
        ],
        render_kw={"class": "form-select"}
    )

    number_of_units = IntegerField(
        _l('Number of Units'),
        validators=[
            DataRequired(_l('Number of units is required.')),
            NumberRange(min=1, message=_l('Must be at least 1 unit.'))
        ],
        render_kw={"placeholder": _l("e.g., 10")}
    )

    county = StringField( # Changed from SelectField to StringField if just storing name directly
        _l('County (Property Location)'),
        validators=[
            DataRequired(_l('County is required.')),
            Length(min=2, max=100, message=_l('County must be between 2 and 100 characters.'))
        ],
        render_kw={"placeholder": _l("e.g., Nairobi, Kilifi")}
    )

    amenities = TextAreaField(
        _l('Amenities (comma separated)'),
        validators=[Optional(), Length(max=500, message=_l('Amenities list too long.'))],
        render_kw={"rows": 3, "placeholder": _l("e.g., Swimming pool, Gym, Balcony")}
    )

    utility_bill_types = TextAreaField(
        _l('Utility Bill Types (comma separated)'),
        validators=[Optional(), Length(max=255, message=_l('Utility types list too long.'))],
        render_kw={"rows": 2, "placeholder": _l("e.g., Water, Electricity, Garbage")}
    )

    unit_numbers = TextAreaField(
        _l('Unit Numbers/Identifiers (comma separated)'),
        validators=[Optional(), DataRequired(_l('At least one unit number is required.')), Length(max=500, message=_l('Unit numbers list too long.'))],
        render_kw={"rows": 3, "placeholder": _l("e.g., A1, B2, Penthouse")}
    )

    deposit_amount = DecimalField(
        _l('Security Deposit Amount (KSh)'),
        validators=[Optional(), NumberRange(min=0, message=_l('Deposit cannot be negative.'))],
        places=2,
        render_kw={"placeholder": _l("e.g., 20000.00")}
    )

    deposit_policy = TextAreaField(
        _l('Security Deposit Policy (Optional)'),
        validators=[Optional(), Length(max=500, message=_l('Policy text too long.'))],
        render_kw={"rows": 3, "placeholder": _l("e.g., Refundable within 30 days of vacation, less damages.")}
    )

    submit = SubmitField(_l('Save Property'))


# --- Tenant Management Form ---
class TenantForm(FlaskForm):
    """Form for landlords to add or edit tenant details and lease terms."""
    property_id = SelectField(
        _l('Assigned Property'),
        validators=[DataRequired(_l('Property assignment is required.'))],
        coerce=int,
        choices=[],
        render_kw={"class": "form-select"}
    )

    first_name = StringField(
        _l('First Name'),
        validators=[
            DataRequired(_l('First name is required.')),
            Length(min=2, max=100, message=_l('First name must be between 2 and 100 characters.'))
        ],
        render_kw={"placeholder": _l("Tenant's first name")}
    )

    last_name = StringField(
        _l('Last Name'),
        validators=[
            DataRequired(_l('Last name is required.')),
            Length(min=2, max=100, message=_l('Last name must be between 2 and 100 characters.'))
        ],
        render_kw={"placeholder": _l("Tenant's last name")}
    )

    email = StringField(
        _l('Email (Optional)'),
        validators=[
            Optional(),
            Email(message=_l('Invalid email address.')),
            Length(max=120, message=_l('Email cannot exceed 120 characters.'))
        ],
        render_kw={"placeholder": _l("tenant@example.com")}
    )

    phone_number = TelField(
        _l('Phone Number'),
        validators=[
            DataRequired(_l('Phone number is required.')),
            Length(min=9, max=20, message=_l('Phone number must be between 9 and 20 characters.')),
            validate_phone_number_format
        ],
        render_kw={"placeholder": _l("e.g., 0712345678")}
    )

    national_id = StringField(
        _l('National ID (Optional)'),
        validators=[
            Optional(),
            Length(min=6, max=30, message=_l('National ID must be between 6 and 30 characters.'))
        ],
        render_kw={"placeholder": _l("e.g., 12345678")}
    )

    status = SelectField(
        _l('Tenant Status'),
        validators=[DataRequired(_l('Tenant status is required.'))],
        choices=[
            ('active', _l('Active')),
            ('vacated', _l('Vacated')),
            ('evicted', _l('Evicted'))
        ],
        render_kw={"class": "form-select"}
    )

    rent_amount = DecimalField(
        _l('Monthly Rent Amount (KSh)'),
        validators=[
            DataRequired(_l('Rent amount is required.')),
            NumberRange(min=0.01, message=_l('Rent must be greater than 0.'))
        ],
        places=2,
        render_kw={"placeholder": _l("e.g., 15000.00")}
    )

    due_day_of_month = IntegerField(
        _l('Rent Due Day of Month'),
        validators=[
            DataRequired(_l('Due day is required.')),
            NumberRange(min=1, max=31, message=_l('Day must be between 1 and 31.'))
        ],
        render_kw={"placeholder": _l("e.g., 1 (for 1st of month)")}
    )

    grace_period_days = IntegerField(
        _l('Grace Period (days)'),
        validators=[
            DataRequired(_l('Grace period is required.')),
            NumberRange(min=0, message=_l('Grace period cannot be negative.'))
        ],
        render_kw={"placeholder": _l("e.g., 5")}
    )

    lease_start_date = DateField(
        _l('Lease Start Date'),
        validators=[DataRequired(_l('Lease start date is required.'))],
        format='%Y-%m-%d',
        render_kw={"placeholder": "YYYY-MM-DD"}
    )

    lease_end_date = DateField(
        _l('Lease End Date (Optional)'),
        validators=[
            Optional(),
            validate_date_order
        ],
        format='%Y-%m-%d',
        render_kw={"placeholder": "YYYY-MM-DD"}
    )

    submit = SubmitField(_l('Save Tenant'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate property choices dynamically for landlord
        try:
            from flask_security import current_user
            from app import db # Import db here
            from app.models import Property # Import Property model here

            if current_user.is_authenticated and hasattr(current_user, 'has_role') and current_user.has_role('landlord'):
                properties = Property.query.filter_by(landlord_id=current_user.id).order_by(Property.name).all()
                self.property_id.choices = [
                    (p.id, _l(p.name)) for p in properties
                ]
            else:
                self.property_id.choices = []
        except Exception as e:
            from flask import current_app # Import for logging
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error populating property choices for TenantForm: {e}")
            else:
                print(f"Error populating property choices for TenantForm: {e}")
            self.property_id.choices = [] # Fallback
        
        # Add default "Select a Property..." option, only if not already present
        if not self.property_id.choices or self.property_id.choices[0][0] != 0:
            self.property_id.choices.insert(0, (0, _l('Select a Property...')))

    def validate_property_id(self, field):
        """Ensure a valid property is selected."""
        if field.data == 0:
            raise ValidationError(_l('Please select a property.'))


# --- Payment Recording Form ---
class RecordPaymentForm(FlaskForm):
    """Form for landlords to manually record payments received."""
    tenant_id = SelectField(
        _l('Tenant'),
        validators=[DataRequired(_l('Tenant selection is required.'))],
        coerce=int,
        choices=[],
        render_kw={"class": "form-select"}
    )

    amount = DecimalField(
        _l('Amount Paid (KSh)'),
        validators=[
            DataRequired(_l('Amount is required.')),
            NumberRange(min=0.01, message=_l('Amount must be greater than 0.'))
        ],
        places=2,
        render_kw={"placeholder": _l("e.g., 15000.00")}
    )

    payment_date = DateField(
        _l('Payment Date'),
        validators=[DataRequired(_l('Payment date is required.'))],
        format='%Y-%m-%d',
        render_kw={"placeholder": "YYYY-MM-DD"}
    )

    payment_method = SelectField(
        _l('Payment Method'),
        validators=[DataRequired(_l('Payment method is required.'))],
        choices=[
            ('', _l('Select Method...')),
            ('M-Pesa', _l('M-Pesa')),
            ('Cash', _l('Cash')),
            ('Bank Transfer', _l('Bank Transfer')),
            ('Other', _l('Other'))
        ],
        render_kw={"class": "form-select"}
    )

    transaction_id = StringField(
        _l('M-Pesa Transaction ID (Optional)'),
        validators=[
            Optional(),
            Length(max=100, message=_l('Transaction ID cannot exceed 100 characters.'))
        ],
        render_kw={"placeholder": _l("e.g., RA123ABCDEF")}
    )

    description = TextAreaField(
        _l('Description (Optional)'),
        validators=[Length(max=255, message=_l('Description cannot exceed 255 characters.'))],
        render_kw={"rows": 3, "placeholder": _l("Any additional notes about this payment")}
    )

    is_offline = BooleanField(_l('Record as Offline Payment (Sync later)'))

    offline_reference = StringField(
        _l('Offline Reference (Optional)'),
        validators=[Optional(), Length(max=100, message=_l('Reference cannot exceed 100 characters.'))],
        render_kw={"placeholder": _l("e.g., Manual Receipt #123")}
    )

    submit = SubmitField(_l('Record Payment'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate tenant choices dynamically for landlord
        try:
            from flask_security import current_user
            from app import db
            from app.models import Property, Tenant

            if current_user.is_authenticated and hasattr(current_user, 'has_role') and current_user.has_role('landlord'):
                # Get all tenants belonging to the current landlord's properties
                property_ids = [p.id for p in Property.query.filter_by(landlord_id=current_user.id).all()]
                tenants = Tenant.query.filter(Tenant.property_id.in_(property_ids)).order_by(Tenant.first_name).all()
                self.tenant_id.choices = [
                    (t.id, _l(f"{t.first_name} {t.last_name} ({t.property.name})"))
                    for t in tenants
                ]
            else:
                self.tenant_id.choices = []
        except Exception as e:
            from flask import current_app
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error populating tenant choices for RecordPaymentForm: {e}")
            else:
                print(f"Error populating tenant choices for RecordPaymentForm: {e}")
            self.tenant_id.choices = []

        if not self.tenant_id.choices or self.tenant_id.choices[0][0] != 0:
            self.tenant_id.choices.insert(0, (0, _l('Select a Tenant...')))

    def validate_tenant_id(self, field):
        """Ensure a valid tenant is selected."""
        if field.data == 0:
            raise ValidationError(_l('Please select a tenant.'))

    def validate_transaction_id(self, field):
        """Ensure transaction ID is provided if payment method is M-Pesa."""
        if self.payment_method.data == 'M-Pesa' and not field.data:
            raise ValidationError(_l('M-Pesa Transaction ID is required for M-Pesa payments.'))

    def validate_offline_reference(self, field):
        """Ensure offline reference is provided if payment is marked as offline."""
        if self.is_offline.data and not field.data:
            raise ValidationError(_l('Offline reference is required for offline payments.'))