"""questions answers reputation notifications

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-21 17:52:20.453146
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


TYPES = "'resource', 'article', 'collection', 'question'"


def _type_check(types: str) -> None:
    op.drop_constraint("type", "content_items", type_="check")
    op.create_check_constraint("type", "content_items", f"type IN ({types})")


def upgrade() -> None:
    _type_check(TYPES + ", 'answer'")
    op.execute("CREATE SEQUENCE call_seq_answer START 1")
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("call_number", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), server_default="", nullable=False),
        sa.Column("dedupe_key", sa.String(length=100), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('reply', 'answer', 'answer_accepted', 'vote_milestone', 'moderation')",
            name=op.f("ck_notifications_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_notifications_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["content_items.id"],
            name=op.f("fk_notifications_item_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        sa.UniqueConstraint(
            "user_id", "dedupe_key", name=op.f("uq_notifications_user_id")
        ),
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "reputation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("points", sa.SmallInteger(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reason IN ('vote_up', 'vote_down', 'answer_accepted', 'accepted_answer')",
            name=op.f("ck_reputation_events_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["content_items.id"],
            name=op.f("fk_reputation_events_item_id_content_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_reputation_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reputation_events")),
        sa.UniqueConstraint(
            "user_id", "event_key", name=op.f("uq_reputation_events_user_id")
        ),
    )
    op.create_index(
        "ix_reputation_events_user_created",
        "reputation_events",
        ["user_id", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=60), nullable=False),
        sa.Column("linked_resource_id", sa.Uuid(), nullable=True),
        sa.Column("duplicate_of_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "duplicate_of_id <> id", name=op.f("ck_questions_not_own_duplicate")
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_id"],
            ["questions.id"],
            name=op.f("fk_questions_duplicate_of_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["content_items.id"],
            name=op.f("fk_questions_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["linked_resource_id"],
            ["resources.id"],
            name=op.f("fk_questions_linked_resource_id_resources"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
    )
    op.create_index(
        op.f("ix_questions_duplicate_of_id"),
        "questions",
        ["duplicate_of_id"],
        unique=False,
    )
    op.create_index("ix_questions_topic", "questions", ["topic"], unique=False)
    op.create_table(
        "answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"],
            ["content_items.id"],
            name=op.f("fk_answers_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_answers_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answers")),
    )
    op.create_index(
        op.f("ix_answers_question_id"), "answers", ["question_id"], unique=False
    )
    op.create_index(
        "uq_answers_accepted",
        "answers",
        ["question_id"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NOT NULL"),
    )
    op.create_index(
        "uq_answers_pinned",
        "answers",
        ["question_id"],
        unique=True,
        postgresql_where=sa.text("pinned_at IS NOT NULL"),
    )
    op.add_column(
        "users",
        sa.Column("reputation", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("email_digest", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.execute("DELETE FROM content_items WHERE type = 'answer'")  # cascades to answers
    op.drop_column("users", "email_digest")
    op.drop_column("users", "reputation")
    op.drop_index(
        "uq_answers_pinned",
        table_name="answers",
        postgresql_where=sa.text("pinned_at IS NOT NULL"),
    )
    op.drop_index(
        "uq_answers_accepted",
        table_name="answers",
        postgresql_where=sa.text("accepted_at IS NOT NULL"),
    )
    op.drop_index(op.f("ix_answers_question_id"), table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_questions_topic", table_name="questions")
    op.drop_index(op.f("ix_questions_duplicate_of_id"), table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_reputation_events_user_created", table_name="reputation_events")
    op.drop_table("reputation_events")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
    op.execute("DROP SEQUENCE call_seq_answer")
    _type_check(TYPES)
