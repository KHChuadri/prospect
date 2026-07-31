import os
import pytest
import psycopg

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/jobtracker",
)


@pytest.fixture
def conn():
    try:
        c = psycopg.connect(TEST_DB)
    except psycopg.OperationalError:
        pytest.skip("no test database available")
    c.autocommit = False
    try:
        yield c
    finally:
        c.rollback()   # discard everything the test wrote
        c.close()
