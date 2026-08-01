import os
import pytest
import psycopg

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/jobtracker",
)

MIGRATE_HINT = (
    "test database is not migrated — the agent no longer creates its own "
    "tables. Run:\n"
    "  cd prospect-backend/src/JobApplicationTracker && dotnet ef database update"
)


@pytest.fixture
def conn():
    try:
        c = psycopg.connect(TEST_DB)
    except psycopg.OperationalError:
        pytest.skip("no test database available")
    c.autocommit = False
    # Schema is owned by the .NET project's EF migrations. Without this check a
    # reachable-but-unmigrated database fails every test with an opaque
    # UndefinedTable and no hint about what to do.
    with c.cursor() as cur:
        cur.execute("SELECT to_regclass('public.events')")
        if cur.fetchone()[0] is None:
            c.close()
            pytest.skip(MIGRATE_HINT)
    try:
        yield c
    finally:
        c.rollback()   # discard everything the test wrote
        c.close()
