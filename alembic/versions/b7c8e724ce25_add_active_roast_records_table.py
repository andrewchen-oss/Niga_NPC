"""add active_roast_records table

Revision ID: b7c8e724ce25
Revises: 4a2f3c642237
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'b7c8e724ce25'
down_revision = '4a2f3c642237'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'active_roast_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tweet_id', sa.String(64), unique=True, nullable=False),
        sa.Column('author_id', sa.String(64), nullable=False),
        sa.Column('author_username', sa.String(64), nullable=False),
        sa.Column('roast_content', sa.Text(), nullable=False),
        sa.Column('reply_tweet_id', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_active_roast_tweet_id', 'active_roast_records', ['tweet_id'])
    op.create_index('ix_active_roast_author_id', 'active_roast_records', ['author_id'])


def downgrade() -> None:
    op.drop_index('ix_active_roast_author_id', table_name='active_roast_records')
    op.drop_index('ix_active_roast_tweet_id', table_name='active_roast_records')
    op.drop_table('active_roast_records')
