"""init

Revision ID: 001
Revises:
Create Date: 2025-11-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('USER', 'PREMIUM', 'ADMIN', name='userrole'), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=True),
        sa.Column('total_photos', sa.Integer(), nullable=True),
        sa.Column('total_voice', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)

    # Create requests table
    op.create_table(
        'requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.Enum('TEXT', 'PHOTO', 'VOICE', 'DOCUMENT', name='requesttype'), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('voice_url', sa.String(500), nullable=True),
        sa.Column('document_url', sa.String(500), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('response_tokens', sa.Integer(), nullable=True),
        sa.Column('defect_type', sa.String(100), nullable=True),
        sa.Column('defect_severity', sa.Enum('CRITICAL', 'MAJOR', 'MINOR', 'INFO', name='defectseverity'), nullable=True),
        sa.Column('mentioned_regulations', sa.JSON(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('cached', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_requests_user_id'), 'requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_requests_created_at'), 'requests', ['created_at'], unique=False)

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create analytics table
    op.create_table(
        'analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=True),
        sa.Column('total_users', sa.Integer(), nullable=True),
        sa.Column('new_users', sa.Integer(), nullable=True),
        sa.Column('photo_requests', sa.Integer(), nullable=True),
        sa.Column('text_requests', sa.Integer(), nullable=True),
        sa.Column('voice_requests', sa.Integer(), nullable=True),
        sa.Column('defects_found', sa.Integer(), nullable=True),
        sa.Column('critical_defects', sa.Integer(), nullable=True),
        sa.Column('major_defects', sa.Integer(), nullable=True),
        sa.Column('minor_defects', sa.Integer(), nullable=True),
        sa.Column('avg_response_time', sa.Float(), nullable=True),
        sa.Column('cache_hit_rate', sa.Float(), nullable=True),
        sa.Column('top_regulations', sa.JSON(), nullable=True),
        sa.Column('top_defect_types', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('analytics')
    op.drop_table('projects')
    op.drop_index(op.f('ix_requests_created_at'), table_name='requests')
    op.drop_index(op.f('ix_requests_user_id'), table_name='requests')
    op.drop_table('requests')
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_table('users')
