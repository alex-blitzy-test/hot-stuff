"""Configuration objects for the application factory.

``DATABASE_URL`` is read in this module and nowhere else. A deployment supplies its
own connection string through the environment — the ``api`` service in
``docker-compose.yml`` for the container, ``.flaskenv`` for a host-side
``flask run`` — so no credential lives in the source tree.
"""

import os

# Development default: the postgres service docker-compose.yml declares
# (POSTGRES_USER/POSTGRES_PASSWORD 'postgres', POSTGRES_DB 'db').
_DEV_DATABASE_URL = 'postgresql://postgres:postgres@postgres/db'


class Config:
    """Settings every environment shares."""

    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False


class DevConfig(Config):
    """Development and local-run settings, defaulting to the compose database."""

    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL') or _DEV_DATABASE_URL


class TestConfig(Config):
    """Test settings: an in-memory SQLite database, discarded with the fixture.

    The engine is left untouched here. Flask-SQLAlchemy already hands an
    in-memory SQLite URL the single-connection pool it needs, and refuses an
    explicit pool size for one, so naming a pool option would conflict with it.
    """

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'


class _RequiredDatabaseURL:
    """Resolve DATABASE_URL when the configuration is consumed, not when it is imported.

    A read in ``ProdConfig``'s class body would run at import time, so importing
    this module with the variable unset — as the test runner does, since it loads
    no ``.flaskenv`` — would fail before a single test ran. Flask's
    ``config.from_object`` fetches this attribute at application construction,
    which is where a missing credential belongs.
    """

    def __get__(self, instance: object | None, owner: type | None = None) -> str:
        url = os.environ.get('DATABASE_URL')
        if not url:
            raise RuntimeError('DATABASE_URL environment variable is not set')
        return url


class ProdConfig(Config):
    """Production settings: the connection string must come from the environment."""

    SQLALCHEMY_DATABASE_URI = _RequiredDatabaseURL()
