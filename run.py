import os
from app import create_app, db # Assuming app/__init__.py has create_app function
from flask_migrate import Migrate
from app.models import User, Role, County, Property, Tenant, Payment, AuditLog # Import models for Flask-Migrate

# Use python-dotenv to load .env file in development
from dotenv import load_dotenv
load_dotenv()

# Determine config based on environment variable
config_name = os.getenv('FLASK_CONFIG', 'development')
app = create_app(config_name)
migrate = Migrate(app, db)

# Flask shell context (optional, but very useful for development)
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, County=County,
                Property=Property, Tenant=Tenant, Payment=Payment, AuditLog=AuditLog)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # Listen on all interfaces for Docker compatibility