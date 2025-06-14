## GitHub Copilot Prompt for Real Estate Payment Tracker (REPT)
---
# Objective
Create a Flask-based web application for a **Real Estate Payment Tracker (REPT)** tailored to Kenya’s real estate market. The application should provide a balanced user experience, being **simple for less tech-savvy users** while offering **advanced functionality for experienced landlords**. Key features include automated rent payment tracking, M-Pesa integration, multi-language support (English and Swahili), SMS/email notifications, robust offline payment handling, comprehensive reporting, audit trails, and a mobile-first user interface. The technology stack and features must align with the provided prototype specifications.

---
# Project Structure
Generate the following directory structure:
rept/
├── app/
│   ├── init.py
│   ├── models.py
│   ├── routes.py
│   ├── forms.py
│   ├── api.py           # For M-Pesa integration and external APIs
│   ├── translations/    # For multi-language support (e.g., Flask-Babel .po/.mo files)
│   │   ├── en/
│   │   │   └── LC_MESSAGES/
│   │   │       └── messages.po
│   │   ├── sw/
│   │   │   └── LC_MESSAGES/
│   │   │       └── messages.po
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── auth/        # Login, Register, Forgot Password templates
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── dashboard.html
│   │   ├── properties/  # Property management templates
│   │   │   ├── list.html
│   │   │   └── add_edit.html
│   │   ├── tenants/     # Tenant management templates
│   │   │   ├── list.html
│   │   │   └── add_edit.html
│   │   ├── payments/    # Payment recording and history
│   │   │   └── record_payment.html
│   │   ├── reports/     # Reporting specific templates
│   │   │   └── index.html
│   │   ├── audit_trail.html # For viewing audit logs
│   │   └── flash_macros.html # For consistent flash message rendering
│   ├── static/
│   │   ├── css/
│   │   │   ├── styles.css
│   │   ├── js/
│   │   │   ├── scripts.js
│   │   └── img/         # For logos, favicons, etc.
├── migrations/
├── config.py
├── run.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                 # For environment variables
└── tests/               # For unit and integration tests
├── init.py
├── test_models.py
└── test_routes.py


---
# Technology Stack

**Backend:** Flask, Flask-Login, Flask-WTF, Flask-Migrate, Flask-SQLAlchemy, **Flask-Babel** (for i18n/l10n), **Flask-Limiter** (for rate limiting)
**Frontend:** Jinja2, Bootstrap 5, Vanilla JavaScript
**Database:** SQLite (development), PostgreSQL (production) with pgAudit for audit trails
**Integrations:** Twilio (SMS), Flask-Mail (email), M-Pesa API (payment - using `requests` or a dedicated library if available, e.g., `daraja`), **APScheduler** (automated tasks), `python-decouple` (environment variables), **pandas** (for Excel reports), **ReportLab** (PDF reports)
**Deployment:** Docker, Heroku
**Other Libraries:** Gunicorn (production WSGI server), python-dotenv (for local .env loading)

---
# Core Features

## Authentication & Authorization:
* Implement user registration/login with Flask-Login.
* Support **landlord and tenant roles** with role-based access control (RBAC).
* Use Flask-WTF for secure form handling and CSRF protection.
* **Password Management:** Implement secure password hashing and basic policies (e.g., minimum length).
* Automate OAuth token renewal for M-Pesa API using APScheduler.
* **Rate Limiting:** Implement rate limiting on login and registration routes to prevent brute-force attacks.

## Property & Tenant Management:
* Create models for `Property`, `Tenant`, and `Payment` using Flask-SQLAlchemy.
* Allow landlords to add/edit/view **detailed property information** (address, type, number of units, amenities).
* Enable landlords to add/edit/view **tenant profiles** (contact info, lease start/end, rent amount, due day, grace period, tenant status e.g., `active`, `vacated`).
* **Assign Tenants:** Landlords should be able to assign tenants to specific properties.
* Validate tenant data (e.g., phone number, email) during onboarding using Flask-WTF validators.
* Support **multi-language form labels** (English/Swahili) using Flask-Babel.

## Rent Payment Tracking:
* Implement automated **monthly rent schedules** with APScheduler based on lease terms.
* **M-Pesa API Integration (Daraja API):** Integrate C2B (Customer to Business) callbacks for automatic payment confirmation. Consider STK Push for tenant-initiated payments.
* **Payment Statuses:** Track payment states (`paid`, `partially_paid`, `overdue`, `pending_confirmation`).
* **Transaction Logging:** Record all payment transactions with details like `PayBill number`, `M-Pesa transaction ID`, `amount`, `date`, `fees`, and `status`.
* **Manual Payment Recording:** Allow landlords to manually record cash or bank payments.

## SMS/Email Notifications:
* Send **automated notifications** via Twilio (SMS) and Flask-Mail (email).
* **Customizable Templates:** Allow landlords to customize notification messages.
* **Notification Types:** `payment_confirmation` (after M-Pesa callback/manual record), `rent_due_reminder` (e.g., 3 days before due date), `overdue_payment_notice` (e.g., 1 day after grace period).
* Support **multi-language notifications** (English/Swahili) via Flask-Babel.
* Schedule reminders for overdue payments using APScheduler.

## Advanced Reporting:
* Generate customizable tenant payment reports using ReportLab (for PDF) and pandas (for CSV/Excel).
* Include key metrics: `overdue payments`, `total collections (by period/property)`, `income vs. expenses`, `vacancy rates`, `payment success rate`.
* **Export Options:** Allow export of reports to CSV, Excel, and PDF formats.
* **Dashboard Display:** Display summarized reports on the dashboard with **interactive filters** (e.g., date range picker, property dropdown, payment status checkboxes).
* **Audit Trail Report:** A separate report showing user actions.

## Audit Trails:
* Utilize PostgreSQL’s `pgAudit` extension to track detailed changes to `Property`, `Tenant`, and `Payment` records (CRUD operations).
* Log user actions (e.g., `login`, `logout`, `password_change`, `payment_update`, `property_add/edit`) with timestamps, user IDs, and originating IP addresses.
* Provide a dedicated **audit trail view** for landlords to review historical changes and resolve disputes.

## User Interface:
* Design a **mobile-first, responsive interface** using Bootstrap 5 and Jinja2 templates, prioritizing usability on small screens.
* **Dashboard Design:** Create a clean dashboard showing key metrics (`overdue payments`, `total collections`, `recent transactions`) at a glance for **less tech-savvy users**.
* **Progressive Disclosure:** Advanced settings and detailed data tables should be accessible via clear "More Details" links, tabs, or dedicated "Advanced" sections to avoid overwhelming basic users.
* Support **Swahili translations** for all UI elements (buttons, labels, messages) using Flask-Babel.
* Use Vanilla JavaScript for dynamic features like real-time form validation feedback (leveraging Bootstrap's `needs-validation`), report filters, and interactive tables.
* Implement clear and consistent **empty states** (e.g., "No tenants yet. Click here to add one!").

## Offline Payment Handling:
* Cache **pending M-Pesa transactions** and **manually recorded offline payments** locally using SQLite.
* Implement a synchronization mechanism to push cached data to PostgreSQL when network connectivity is restored.
* Provide a basic, **USSD-like web interface** or flow for simple payment confirmation *if the primary M-Pesa callback fails* or for manual payments, ensuring minimal input is required.

---
# Regulatory and Local Considerations

* Ensure compliance with Kenya’s **CBK (Central Bank of Kenya)** oversight and **KRA (Kenya Revenue Authority)** data protection regulations.
* Align with the **VASPs Bill, 2025**, for M-Pesa API integration, specifically concerning data handling and transaction reporting.
* Prepare for **ISO 20022 migration** by structuring payment transaction data (amount, currency, timestamps, parties, unique reference) appropriately from the outset.
* Optimize for **mobile-first design** to suit Kenya’s high mobile penetration, ensuring intuitive navigation and reduced data consumption where possible.
* Use **Swahili localization** to enhance accessibility and inclusivity for a broader Kenyan audience.

---
# Development Guidelines

* **Phase 1 (Foundation & Auth):** Set up the basic Flask application, Flask-Login, Flask-WTF. Implement initial `User` and `Role` models. Automate M-Pesa API OAuth token renewal with APScheduler.
* **Phase 2 (Core Management):** Implement `Property`, `Tenant`, and `Payment` models. Develop landlord workflows for adding/editing properties and assigning tenants. Set up automated rent schedules. Use pre-built libraries for API validation.
* **Phase 3 (Payments & Reporting):** Integrate C2B M-Pesa API callbacks. Develop core payment tracking and dashboard displays. Implement advanced reporting (ReportLab, pandas). Optimize endpoints for high transaction volumes.
* **Phase 4 (Notifications & Audit & Deployment):** Add SMS/email notifications (Twilio, Flask-Mail). Implement audit trails using `pgAudit`. Develop offline payment handling (SQLite caching/sync). Prepare Dockerfile and `docker-compose.yml` for Heroku deployment. Conduct initial testing for regulatory compliance.

---

# Additional Instructions

Use environment variables (via python-decouple) for sensitive data like API keys and database URLs.
Include a requirements.txt with all dependencies (e.g., Flask, Flask-Login, ReportLab, Twilio, pandas).
Write a Dockerfile and docker-compose.yml for containerized deployment.
Add Swahili translation dictionaries in app/translations.py for UI and notifications.
Test M-Pesa API integration in sandbox mode and mock offline scenarios.
Ensure audit trails are enabled in PostgreSQL production setup using pgAudit.
Optimize database queries for scalability using indexes on Payment and Tenant tables.

# Expected Output

A fully functional Flask application with the specified features.
Mobile-first, responsive UI with English/Swahili support.
M-Pesa-integrated payment system with offline caching.
Comprehensive reports in CSV, Excel, and PDF formats.
Audit trails for transparency and compliance.
Dockerized setup deployable to Heroku.

# Precautions
do not hallucinate.
avoid circular imports.


# Notes

Refer to the prototype’s emphasis on Kenya’s socio-economic context (e.g., M-Pesa penetration, Swahili usage).
Address potential challenges like OAuth complexity and high transaction volumes as outlined in the timeline.
Engage legal experts for compliance with CBK, KRA, and VASPs Bill, 2025, during Week 4 testing.
Future iterations could explore predictive analytics or decentralized ledger technologies, but focus on core features for now.

