"""articles collections comments attachments previews

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-21 17:31:57.629743
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

SEARCH_FN = """
CREATE OR REPLACE FUNCTION content_items_set_search_vector() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.search_vector :=
    setweight(ufaz_tsvector(coalesce(NEW.title, '')), 'A') ||
    setweight(ufaz_tsvector(coalesce((
      SELECT string_agg(t.name, ' ') FROM content_tags ct
      JOIN tags t ON t.id = ct.tag_id WHERE ct.item_id = NEW.id), '')), 'B') ||
    setweight(ufaz_tsvector(coalesce(NEW.description, '')), 'C') ||
    setweight(ufaz_tsvector(coalesce((
      SELECT concat_ws(' ', r.category, r.prerequisites, r.best_part, r.student_note)
      FROM resources r WHERE r.id = NEW.id), '') || {article}), 'D');
  RETURN NEW;
END $$
"""
TOUCH_FN = """
CREATE OR REPLACE FUNCTION content_items_touch_search() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid;
BEGIN
  IF TG_TABLE_NAME IN ({tables}) THEN target := NEW.id;
  ELSE target := coalesce(NEW.item_id, OLD.item_id); END IF;
  UPDATE content_items SET title = title WHERE id = target;
  RETURN NULL;
END $$
"""
# Article bodies join the weight-D text so they are searchable.
ARTICLE_BODY = "coalesce((SELECT ' ' || a.body_md FROM articles a WHERE a.id = NEW.id), '')"


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('attachments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=5), nullable=False),
    sa.Column('mime', sa.String(length=100), nullable=False),
    sa.Column('size', sa.BigInteger(), nullable=False),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('width', sa.Integer(), nullable=True),
    sa.Column('height', sa.Integer(), nullable=True),
    sa.Column('variants', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('image', 'file')", name=op.f('ck_attachments_kind')),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_attachments_owner_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attachments'))
    )
    op.create_index(op.f('ix_attachments_owner_id'), 'attachments', ['owner_id'], unique=False)
    op.create_table('articles',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('body_md', sa.Text(), nullable=False),
    sa.Column('body_html', sa.Text(), nullable=False),
    sa.Column('toc', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('reading_minutes', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('cover_attachment_id', sa.Uuid(), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('reading_minutes >= 1', name=op.f('ck_articles_reading_minutes')),
    sa.ForeignKeyConstraint(['cover_attachment_id'], ['attachments.id'], name=op.f('fk_articles_cover_attachment_id_attachments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['id'], ['content_items.id'], name=op.f('fk_articles_id_content_items'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_articles')),
    sa.UniqueConstraint('slug', name=op.f('uq_articles_slug'))
    )
    op.create_table('collections',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['content_items.id'], name=op.f('fk_collections_id_content_items'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_collections'))
    )
    op.create_table('comments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=True),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_comments_author_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['content_items.id'], name=op.f('fk_comments_item_id_content_items'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_id'], ['comments.id'], name=op.f('fk_comments_parent_id_comments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_comments'))
    )
    op.create_index(op.f('ix_comments_author_id'), 'comments', ['author_id'], unique=False)
    op.create_index('ix_comments_item_created', 'comments', ['item_id', 'created_at', 'id'], unique=False)
    op.create_index(op.f('ix_comments_parent_id'), 'comments', ['parent_id'], unique=False)
    op.create_table('collection_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('collection_id', sa.Uuid(), nullable=False),
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.Column('note', sa.Text(), server_default='', nullable=False),
    sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], name=op.f('fk_collection_items_collection_id_collections'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['content_items.id'], name=op.f('fk_collection_items_item_id_content_items'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_collection_items')),
    sa.UniqueConstraint('collection_id', 'item_id', name=op.f('uq_collection_items_collection_id'))
    )
    op.create_index(op.f('ix_collection_items_collection_id'), 'collection_items', ['collection_id'], unique=False)
    op.create_index(op.f('ix_collection_items_item_id'), 'collection_items', ['item_id'], unique=False)
    op.add_column('resource_links', sa.Column('preview_title', sa.String(length=200), nullable=True))
    op.add_column('resource_links', sa.Column('preview_image', sa.String(length=2048), nullable=True))
    op.add_column('resource_links', sa.Column('preview_favicon', sa.String(length=2048), nullable=True))
    op.add_column('resource_links', sa.Column('preview_fetched_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(op.f('fk_resources_primary_attachment_id_attachments'), 'resources', 'attachments', ['primary_attachment_id'], ['id'], ondelete='SET NULL')
    op.add_column('users', sa.Column('avatar_attachment_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(op.f('fk_users_avatar_attachment_id_attachments'), 'users', 'attachments', ['avatar_attachment_id'], ['id'], ondelete='SET NULL')

    op.execute(SEARCH_FN.format(article=ARTICLE_BODY))
    op.execute(TOUCH_FN.format(tables="'resources', 'articles'"))
    op.execute(
        "CREATE TRIGGER articles_search AFTER INSERT OR UPDATE ON articles "
        "FOR EACH ROW EXECUTE FUNCTION content_items_touch_search()"
    )


def downgrade() -> None:
    op.execute(SEARCH_FN.format(article="''"))
    op.execute(TOUCH_FN.format(tables="'resources'"))
    op.drop_constraint(op.f('fk_users_avatar_attachment_id_attachments'), 'users', type_='foreignkey')
    op.drop_column('users', 'avatar_attachment_id')
    op.drop_constraint(op.f('fk_resources_primary_attachment_id_attachments'), 'resources', type_='foreignkey')
    op.drop_column('resource_links', 'preview_fetched_at')
    op.drop_column('resource_links', 'preview_favicon')
    op.drop_column('resource_links', 'preview_image')
    op.drop_column('resource_links', 'preview_title')
    op.drop_index(op.f('ix_collection_items_item_id'), table_name='collection_items')
    op.drop_index(op.f('ix_collection_items_collection_id'), table_name='collection_items')
    op.drop_table('collection_items')
    op.drop_index(op.f('ix_comments_parent_id'), table_name='comments')
    op.drop_index('ix_comments_item_created', table_name='comments')
    op.drop_index(op.f('ix_comments_author_id'), table_name='comments')
    op.drop_table('comments')
    op.drop_table('collections')
    op.drop_table('articles')
    op.drop_index(op.f('ix_attachments_owner_id'), table_name='attachments')
    op.drop_table('attachments')
