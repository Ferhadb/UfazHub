"""reports appeals

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-21 18:03:24.551455
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appeals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=10), server_default="open", nullable=False
        ),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(kind = 'content') = (item_id IS NOT NULL)",
            name=op.f("ck_appeals_item_matches_kind"),
        ),
        sa.CheckConstraint("kind IN ('content', 'ban')", name=op.f("ck_appeals_kind")),
        sa.CheckConstraint(
            "status IN ('open', 'accepted', 'rejected')", name=op.f("ck_appeals_status")
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["content_items.id"],
            name=op.f("fk_appeals_item_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["users.id"],
            name=op.f("fk_appeals_resolved_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_appeals_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appeals")),
    )
    op.create_index(
        "ix_appeals_status_created",
        "appeals",
        ["status", "created_at", "id"],
        unique=False,
    )
    op.create_index(op.f("ix_appeals_user_id"), "appeals", ["user_id"], unique=False)
    op.create_index(
        "uq_appeals_open_ban",
        "appeals",
        ["user_id"],
        unique=True,
        postgresql_where="status = 'open' AND item_id IS NULL",
    )
    op.create_index(
        "uq_appeals_open_item",
        "appeals",
        ["user_id", "item_id"],
        unique=True,
        postgresql_where="status = 'open' AND item_id IS NOT NULL",
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "status", sa.String(length=10), server_default="open", nullable=False
        ),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reason IN ('spam', 'offensive', 'copyright', 'inaccurate', 'broken_link', 'off_topic', 'other')",
            name=op.f("ck_reports_reason"),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'actioned', 'dismissed')",
            name=op.f("ck_reports_status"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["content_items.id"],
            name=op.f("fk_reports_item_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name=op.f("fk_reports_reporter_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["users.id"],
            name=op.f("fk_reports_resolved_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint("item_id", "reporter_id", name=op.f("uq_reports_item_id")),
    )
    op.create_index(
        "ix_reports_item_status", "reports", ["item_id", "status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_reports_item_status", table_name="reports")
    op.drop_table("reports")
    op.drop_index(
        "uq_appeals_open_item",
        table_name="appeals",
        postgresql_where="status = 'open' AND item_id IS NOT NULL",
    )
    op.drop_index(
        "uq_appeals_open_ban",
        table_name="appeals",
        postgresql_where="status = 'open' AND item_id IS NULL",
    )
    op.drop_index(op.f("ix_appeals_user_id"), table_name="appeals")
    op.drop_index("ix_appeals_status_created", table_name="appeals")
    op.drop_table("appeals")
