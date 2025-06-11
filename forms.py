# app/forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    BooleanField,
    SelectField,
    TelField,
    DecimalField,
    DateField,
    TextAreaField,
    IntegerField # For number_of_units, due_day_of_month, grace_period_days
)
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    NumberRange,
    Optional,
    ValidationError,
    Regexp
)
from flask_security.forms import RegisterForm, LoginForm # For extending Flask-Security forms
from flask_babel import lazy_gettext as _l # For multi-language support

# Import your database models for dynamic choices
# Ensure these models are accessible (e.g., app.models)
try:
    from app.models import County, Property, Tenant
    # For dynamic choices, you might need to ensure you have an active Flask app context
    # or pass a list of objects to the form's __init__ method if querying outside a request context.
    # For simplicity, these queries will typically run within a request context where db.session is available.
except ImportError:
    # Fallback for when models might not be fully initialized during initial Flask-WTF import
    # This might happen during app startup or when forms are imported before db is fully set up.
    # In a real app, ensure your app context is correct or pass choices dynamically.
    print("Warning: Could not import models directly in forms.py. Dynamic choices might fail without app context.")
    class County:
        id = 0
        name = "Default County"
        @staticmethod
        def query(): return type('', (), {'all': lambda: []})() # Mock for initial import
    class Property:
        id = 0
        name = "Default Property"
        @staticmethod
        def query(): return type('', (), {'all': lambda: []})()
    class Tenant:
        id = 0
        name = "Default Tenant"
        @staticmethod
        def query(): return type('', (), {'all': lambda: []})()


# --- Custom Validators ---
def validate_phone_number_format(form, field):
    """Custom validator for phone number: checks digits only and minimum length."""
    if field.data:
        # Remove any non-digit characters for validation and cleaning
        digits_only = ''.join(filter(str.isdigit, field.data))
        if not digits_only.isdigit():
            raise ValidationError(_l('Phone number must contain only digits.'))
        if len(digits_only) < 9: # Kenyan phone numbers are typically 9 or 10 digits after leading 0
            raise ValidationError(_l('Phone number must contain at least 9 digits (excluding country code).'))
        field.data = digits_only # Clean the data for storage

def validate_date_order(form, field):
    """Custom validator to ensure end date is not before start date."""
    if form.lease_start_date.data and field.data and field.data < form.lease_start_date.data:
        raise ValidationError(_l('Lease end date cannot be before lease start date.'))


# --- Authentication Forms (Extending Flask-Security-Too) ---

class ExtendRegisterForm(RegisterForm):
    """Enhanced registration form with additional user fields."""
    first_name = StringField(
        _l('First Name'),
        validators=[
            DataRequired(_l('First name is required.')),
            Length(min=2, max=50, message=_l('First name must be between 2 and 50 characters.'))
        ],
        render_kw={"placeholder": _l("Enter your first name"), "autocomplete": "given-name"}
    )

    last_name = StringField(
        _l('Last Name'),
        validators=[
            DataRequired(_l('Last name is required.')),
            Length(min=2, max=50, message=_l('Last name must be between 2 and 50 characters.'))
        ],
        render_kw={"placeholder": _l("Enter your last name"), "autocomplete": "family-name"}
    )

    phone_number = TelField(
        _l('Phone Number (Optional)'),
        validators=[
            Optional(), # Allows the field to be empty
            Length(min=9, max=20, message=_l('Phone number must be between 9 and 20 characters.')),
            validate_phone_number_format # Custom validator for digits and min length
        ],
        render_kw={"placeholder": _l("e.g., 0712345678"), "autocomplete": "tel-national"}
    )

    county_id = SelectField(
        _l('County'),
        validators=[DataRequired(message=_l('Please select your county.'))],
        coerce=int,
        choices=[], # Populated dynamically in __init__
        render_kw={"class": "form-select"}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate county choices dynamically
        # Ensure County model is accessible and db.session is active
        try:
            counties = County.query.filter_by(active=True).order_by(County.name).all()
            self.county_id.choices = [
                (county.id, _l(county.name)) # Translate county names if they are static strings
                for county in counties
            ]
        except Exception as e:
            print(f"Error populating county choices: {e}")
            self.county_id.choices = [] # Fallback
        # Add default "Select County" option
        self.county_id.choices.insert(0, (0, _l('Select your county...')))

    def validate_county_id(self, field):
        """Ensure a valid county is selected (not the default placeholder)."""
        if field.data == 0:
            raise ValidationError(_l('Please select your county.'))


class ExtendedLoginForm(LoginForm):
    """Enhanced login form with better styling support."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add placeholder text and styling classes directly, as done previously
        # The render_kw attributes might be passed by Flask-Security automatically
        # if you configure it to use your forms. If not, this is the place.
        self.email.render_kw = {
            'placeholder': _l('Enter your email address'),
            'class': 'form-control form-control-lg',
            'autocomplete': 'username' # HTML5 autocomplete for email
        }
        self.password.render_kw = {
            'placeholder': _l('Enter your password'),
            'class': 'form-control form-control-lg',
            'autocomplete': 'current-password' # HTML5 autocomplete for password
        }
        self.remember.render_kw = {
            'class': 'form-check-input'
        }
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

    submit = SubmitField(_l('Save Property'))


# --- Tenant Management Form ---

class TenantForm(FlaskForm):
    """Form for landlords to add or edit tenant details and lease terms."""
    property_id = SelectField(
        _l('Assigned Property'),
        validators=[DataRequired(_l('Property assignment is required.'))],
        coerce=int,
        choices=[], # Populated dynamically
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
            validate_phone_number_format # Custom validator
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
        places=2, # Two decimal places
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
        format='%Y-%m-%d', # Expected date format
        render_kw={"placeholder": "YYYY-MM-DD"}
    )

    lease_end_date = DateField(
        _l('Lease End Date (Optional)'),
        validators=[
            Optional(),
            validate_date_order # Custom validator to check order
        ],
        format='%Y-%m-%d',
        render_kw={"placeholder": "YYYY-MM-DD"}
    )

    submit = SubmitField(_l('Save Tenant'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate property choices dynamically for landlord
        try:
            # Assuming current_user is available in the context where the form is created (e.g., Flask route)
            from flask_login import current_user
            if current_user.is_authenticated and current_user.has_role('landlord'):
                properties = Property.query.filter_by(landlord_id=current_user.id).order_by(Property.name).all()
                self.property_id.choices = [
                    (p.id, _l(p.name)) for p in properties
                ]
            else:
                self.property_id.choices = [] # No properties if not authenticated/not landlord
        except Exception as e:
            print(f"Error populating property choices for TenantForm: {e}")
            self.property_id.choices = [] # Fallback
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
        choices=[], # Populated dynamically
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

    submit = SubmitField(_l('Record Payment'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate tenant choices dynamically for landlord
        try:
            from flask_login import current_user
            if current_user.is_authenticated and current_user.has_role('landlord'):
                # Get all tenants belonging to the current landlord's properties
                property_ids = [p.id for p in Property.query.filter_by(landlord_id=current_user.id).all()]
                tenants = Tenant.query.filter(Tenant.property_id.in_(property_ids)).order_by(Tenant.first_name).all()
                self.tenant_id.choices = [
                    (t.id, _l(f"{t.first_name} {t.last_name} ({t.property.name})")) # Include property name for clarity
                    for t in tenants
                ]
            else:
                self.tenant_id.choices = []
        except Exception as e:
            print(f"Error populating tenant choices for RecordPaymentForm: {e}")
            self.tenant_id.choices = [] # Fallback
        self.tenant_id.choices.insert(0, (0, _l('Select a Tenant...')))

    def validate_tenant_id(self, field):
        """Ensure a valid tenant is selected."""
        if field.data == 0:
            raise ValidationError(_l('Please select a tenant.'))

    def validate_transaction_id(self, field):
        """Ensure transaction ID is provided if payment method is M-Pesa."""
        if self.payment_method.data == 'M-Pesa' and not field.data:
            raise ValidationError(_l('M-Pesa Transaction ID is required for M-Pesa payments.'))