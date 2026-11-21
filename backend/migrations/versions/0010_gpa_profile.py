"""profile look and links copied from UFAZ GPA

Revision ID: 0010
Revises: 0009
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gpa_profile", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gpa_profile")
