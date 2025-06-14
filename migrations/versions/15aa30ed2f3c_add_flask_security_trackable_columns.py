"""Add Flask Security trackable columns

Revision ID: 15aa30ed2f3c
Revises: 
Create Date: 2025-06-14 14:12:01.469678

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15aa30ed2f3c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add Flask-Security trackable columns
    op.add_column('user', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('current_login_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('last_login_ip', sa.String(length=100), nullable=True))
    op.add_column('user', sa.Column('current_login_ip', sa.String(length=100), nullable=True))
    op.add_column('user', sa.Column('login_count', sa.Integer(), nullable=True))


def downgrade():
    # Remove Flask-Security trackable columns
    op.drop_column('user', 'login_count')
    op.drop_column('user', 'current_login_ip')
    op.drop_column('user', 'last_login_ip')
    op.drop_column('user', 'current_login_at')
    op.drop_column('user', 'last_login_at')
