"""link users to UFAZ GPA accounts; allow passwordless (GPA sign-in) users

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gpa_id", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_users_gpa_id", "users", ["gpa_id"])
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(255), nullable=True
    )


def downgrade() -> None:
    # Passwordless users cannot satisfy NOT NULL; an unusable hash keeps them locked out.
    op.execute("UPDATE users SET password_hash = '!' WHERE password_hash IS NULL")
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(255), nullable=False
    )
    op.drop_constraint("uq_users_gpa_id", "users", type_="unique")
    op.drop_column("users", "gpa_id")
