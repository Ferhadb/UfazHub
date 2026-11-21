from tests.conftest import alembic


def test_downgrade_then_upgrade_roundtrip():
    alembic("downgrade", "base")
    alembic("upgrade", "head")


def test_models_match_migrations():
    # Fails when a model change has no migration (drift).
    alembic("check")
