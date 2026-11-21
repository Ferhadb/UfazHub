"""short-lived content view receipts

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_views",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("visitor_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["content_items.id"], name="fk_content_views_item_id_content_items", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("item_id", "visitor_hash", name="pk_content_views"),
    )
    op.create_index("ix_content_views_viewed_at", "content_views", ["viewed_at"])


def downgrade() -> None:
    op.drop_index("ix_content_views_viewed_at", table_name="content_views")
    op.drop_table("content_views")
