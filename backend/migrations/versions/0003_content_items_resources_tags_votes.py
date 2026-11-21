"""content items resources tags votes bookmarks

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21 17:16:11.316234
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

CALL_SEQUENCES = ("resource", "article", "collection", "question")

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Search plumbing. `ufaz_search` folds accents (Əə, é, Ş...) before English stemming.
    op.execute("CREATE TEXT SEARCH CONFIGURATION ufaz_search (COPY = english)")
    op.execute(
        "ALTER TEXT SEARCH CONFIGURATION ufaz_search ALTER MAPPING FOR hword, hword_part, word "
        "WITH unaccent, english_stem"
    )
    # unaccent() is only STABLE; this wrapper is what lets trigram indexes use it. The stock rules
    # leave the Azerbaijani schwa alone, so fold it to "e" here (what people type on a plain keyboard).
    op.execute(
        "CREATE FUNCTION f_unaccent(text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE "
        "AS $$ SELECT translate(public.unaccent('public.unaccent', $1), 'əƏ', 'eE') $$"
    )
    # Full-text side of the same fold: index the text as written and, when it has a schwa, folded too.
    op.execute(
        "CREATE FUNCTION ufaz_tsvector(t text) RETURNS tsvector LANGUAGE sql IMMUTABLE PARALLEL SAFE "
        "AS $$ SELECT to_tsvector('ufaz_search', t) || CASE WHEN t ~ '[əƏ]' "
        "THEN to_tsvector('ufaz_search', translate(t, 'əƏ', 'eE')) ELSE ''::tsvector END $$"
    )
    for prefix in CALL_SEQUENCES:
        op.execute(f"CREATE SEQUENCE call_seq_{prefix} START 1")
    op.create_table('tags',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=False),
    sa.Column('slug', sa.String(length=48), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tags')),
    sa.UniqueConstraint('slug', name=op.f('uq_tags_slug'))
    )
    op.create_table('content_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=12), nullable=False),
    sa.Column('call_number', sa.String(length=16), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), server_default='', nullable=False),
    sa.Column('status', sa.String(length=16), server_default='pending_review', nullable=False),
    sa.Column('hidden_reason', sa.Text(), nullable=True),
    sa.Column('is_research', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('vote_score', sa.Integer(), server_default='0', nullable=False),
    sa.Column('bookmark_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('comment_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('view_count', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status <> 'hidden' OR hidden_reason IS NOT NULL", name=op.f('ck_content_items_hidden_reason')),
    sa.CheckConstraint("status IN ('draft', 'pending_review', 'published', 'hidden')", name=op.f('ck_content_items_status')),
    sa.CheckConstraint("type IN ('resource', 'article', 'collection', 'question')", name=op.f('ck_content_items_type')),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_content_items_author_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_content_items')),
    sa.UniqueConstraint('call_number', name=op.f('uq_content_items_call_number'))
    )
    op.create_index(op.f('ix_content_items_author_id'), 'content_items', ['author_id'], unique=False)
    op.create_index('ix_content_items_feed', 'content_items', ['status', 'created_at', 'id'], unique=False)
    op.create_index('ix_content_items_search_vector', 'content_items', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index('ix_content_items_top', 'content_items', ['status', 'vote_score', 'created_at', 'id'], unique=False)
    op.create_table('bookmarks',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['content_items.id'], name=op.f('fk_bookmarks_item_id_content_items'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bookmarks_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'item_id', name=op.f('pk_bookmarks'))
    )
    op.create_index(op.f('ix_bookmarks_item_id'), 'bookmarks', ['item_id'], unique=False)
    op.create_table('content_tags',
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('tag_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['content_items.id'], name=op.f('fk_content_tags_item_id_content_items'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], name=op.f('fk_content_tags_tag_id_tags'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('item_id', 'tag_id', name=op.f('pk_content_tags'))
    )
    op.create_index(op.f('ix_content_tags_tag_id'), 'content_tags', ['tag_id'], unique=False)
    op.create_table('resources',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('resource_type', sa.String(length=12), nullable=False),
    sa.Column('category', sa.String(length=60), server_default='', nullable=False),
    sa.Column('difficulty', sa.String(length=14), nullable=False),
    sa.Column('time_commitment_minutes', sa.Integer(), nullable=True),
    sa.Column('prerequisites', sa.Text(), server_default='', nullable=False),
    sa.Column('best_part', sa.Text(), server_default='', nullable=False),
    sa.Column('warning', sa.Text(), server_default='', nullable=False),
    sa.Column('student_note', sa.Text(), server_default='', nullable=False),
    sa.Column('primary_attachment_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint("difficulty IN ('beginner', 'intermediate', 'advanced')", name=op.f('ck_resources_difficulty')),
    sa.CheckConstraint("resource_type IN ('book', 'video', 'course', 'article', 'paper', 'notes', 'exam', 'tool', 'dataset', 'other')", name=op.f('ck_resources_resource_type')),
    sa.CheckConstraint('time_commitment_minutes IS NULL OR time_commitment_minutes >= 0', name=op.f('ck_resources_time_commitment')),
    sa.ForeignKeyConstraint(['id'], ['content_items.id'], name=op.f('fk_resources_id_content_items'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resources'))
    )
    op.create_index('ix_resources_difficulty', 'resources', ['difficulty'], unique=False)
    op.create_table('votes',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('value', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('value IN (-1, 1)', name=op.f('ck_votes_value')),
    sa.ForeignKeyConstraint(['item_id'], ['content_items.id'], name=op.f('fk_votes_item_id_content_items'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_votes_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'item_id', name=op.f('pk_votes'))
    )
    op.create_index('ix_votes_user_updated', 'votes', ['user_id', 'updated_at'], unique=False)
    op.create_table('resource_links',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('resource_id', sa.Uuid(), nullable=False),
    sa.Column('url', sa.String(length=2048), nullable=False),
    sa.Column('canonical_url', sa.String(length=2048), nullable=False),
    sa.Column('label', sa.String(length=120), server_default='', nullable=False),
    sa.Column('position', sa.SmallInteger(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], name=op.f('fk_resource_links_resource_id_resources'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resource_links')),
    sa.UniqueConstraint('resource_id', 'canonical_url', name=op.f('uq_resource_links_resource_id'))
    )
    op.create_index('ix_resource_links_canonical_url', 'resource_links', ['canonical_url'], unique=False)
    op.create_index(op.f('ix_resource_links_resource_id'), 'resource_links', ['resource_id'], unique=False)
    op.execute(
        "CREATE INDEX ix_content_items_title_trgm ON content_items "
        "USING gin (f_unaccent(lower(title)) gin_trgm_ops)"
    )
    # search_vector is trigger-maintained. Weights: A title, B tags, C description, D resource notes.
    op.execute(
        """
        CREATE FUNCTION content_items_set_search_vector() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          NEW.search_vector :=
            setweight(ufaz_tsvector(coalesce(NEW.title, '')), 'A') ||
            setweight(ufaz_tsvector(coalesce((
              SELECT string_agg(t.name, ' ') FROM content_tags ct
              JOIN tags t ON t.id = ct.tag_id WHERE ct.item_id = NEW.id), '')), 'B') ||
            setweight(ufaz_tsvector(coalesce(NEW.description, '')), 'C') ||
            setweight(ufaz_tsvector(coalesce((
              SELECT concat_ws(' ', r.category, r.prerequisites, r.best_part, r.student_note)
              FROM resources r WHERE r.id = NEW.id), '')), 'D');
          RETURN NEW;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER content_items_search_vector BEFORE INSERT OR UPDATE OF title, description "
        "ON content_items FOR EACH ROW EXECUTE FUNCTION content_items_set_search_vector()"
    )
    # Subtype and tag changes re-fire the trigger above by touching the parent's title.
    op.execute(
        """
        CREATE FUNCTION content_items_touch_search() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE target uuid;
        BEGIN
          IF TG_TABLE_NAME = 'resources' THEN target := NEW.id;
          ELSE target := coalesce(NEW.item_id, OLD.item_id); END IF;
          UPDATE content_items SET title = title WHERE id = target;
          RETURN NULL;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER resources_search AFTER INSERT OR UPDATE ON resources "
        "FOR EACH ROW EXECUTE FUNCTION content_items_touch_search()"
    )
    op.execute(
        "CREATE TRIGGER content_tags_search AFTER INSERT OR DELETE ON content_tags "
        "FOR EACH ROW EXECUTE FUNCTION content_items_touch_search()"
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_resource_links_resource_id'), table_name='resource_links')
    op.drop_index('ix_resource_links_canonical_url', table_name='resource_links')
    op.drop_table('resource_links')
    op.drop_index('ix_votes_user_updated', table_name='votes')
    op.drop_table('votes')
    op.drop_index('ix_resources_difficulty', table_name='resources')
    op.drop_table('resources')
    op.drop_index(op.f('ix_content_tags_tag_id'), table_name='content_tags')
    op.drop_table('content_tags')
    op.drop_index(op.f('ix_bookmarks_item_id'), table_name='bookmarks')
    op.drop_table('bookmarks')
    op.drop_index('ix_content_items_top', table_name='content_items')
    op.drop_index('ix_content_items_search_vector', table_name='content_items', postgresql_using='gin')
    op.drop_index('ix_content_items_feed', table_name='content_items')
    op.drop_index(op.f('ix_content_items_author_id'), table_name='content_items')
    op.drop_table('content_items')
    op.drop_table('tags')
    op.execute("DROP FUNCTION content_items_touch_search()")
    op.execute("DROP FUNCTION content_items_set_search_vector()")
    for prefix in CALL_SEQUENCES:
        op.execute(f"DROP SEQUENCE call_seq_{prefix}")
    op.execute("DROP FUNCTION ufaz_tsvector(text)")
    op.execute("DROP FUNCTION f_unaccent(text)")
    op.execute("DROP TEXT SEARCH CONFIGURATION ufaz_search")
