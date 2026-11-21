"""SQLAlchemy models. Every module here is imported so Alembic sees it."""

from app.models.audit import AuditLog  # noqa: F401
from app.models.user import AuthToken, RefreshToken, User  # noqa: F401
from app.models.media import Attachment  # noqa: F401
from app.models.content import (  # noqa: F401
    Article,
    Bookmark,
    Collection,
    CollectionItem,
    Comment,
    ContentItem,
    ContentTag,
    Resource,
    ResourceLink,
    Tag,
    Vote,
)
from app.models.qa import Answer, Notification, Question, ReputationEvent  # noqa: F401
from app.models.moderation import Appeal, Report  # noqa: F401
from app.models.library import (  # noqa: F401
    ContentCourse,
    Course,
    Program,
    ReadingList,
    ReadingListItem,
    TagFollow,
)
