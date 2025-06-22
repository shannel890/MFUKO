import os
from dotenv import load_dotenv
from app import create_app
from extension import db
from app.models import User, Role, County, Property, Tenant, Payment, AuditLog

# Load environment variables
load_dotenv()

# Create the Flask application instance
app = create_app(os.getenv('FLASK_CONFIG', 'development'))

# Flask shell context (optional, but very useful for development)
@app.shell_context_processor
def make_shell_context():
    return dict( User=User, Role=Role, County=County,
                Property=Property, Tenant=Tenant, Payment=Payment, AuditLog=AuditLog)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # Listen on all interfaces for Docker compatibility