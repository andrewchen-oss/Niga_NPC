"""add thread target dedup fields

Revision ID: 4a2f3c642237
Revises:
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a2f3c642237'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- 添加新字段 ----
    op.add_column('processed_mentions', sa.Column('reply_to_tweet_id', sa.String(64), nullable=True))
    op.add_column('processed_mentions', sa.Column('target_handle', sa.String(64), nullable=True))

    # ---- 添加联合索引 (thread + target 去重查询) ----
    op.create_index(
        'ix_processed_mentions_thread_target',
        'processed_mentions',
        ['reply_to_tweet_id', 'target_handle'],
    )


def downgrade() -> None:
    op.drop_index('ix_processed_mentions_thread_target', table_name='processed_mentions')
    op.drop_column('processed_mentions', 'target_handle')
    op.drop_column('processed_mentions', 'reply_to_tweet_id')
