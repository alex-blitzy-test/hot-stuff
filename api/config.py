"""Configuration objects for the application factory.

``DATABASE_URL`` is read in this module and nowhere else, and it is read when
the configuration is consumed — at application construction — rather than at
import. A deployment supplies its own connection string through the
environment: the ``api`` service in ``docker-compose.yml`` for the container,
``.flaskenv`` for a host-side ``flask run``. No deployment credential is
embedded here — the development default below is the compose service's own
public placeholder, not a secret, and it applies only while ``DATABASE_URL``
is unset or empty.
"""

import os

# Development default: the postgres service docker-compose.yml declares
# (POSTGRES_USER/POSTGRES_PASSWORD 'postgres', POSTGRES_DB 'db').
_DEV_DATABASE_URL = 'postgresql://postgres:postgres@postgres/db'


class _DatabaseURL:
    """Resolve DATABASE_URL when the configuration is consumed, not at import.

    A read in a class body would run at import time, so a process whose
    environment is not final yet — the test runner, which loads no
    ``.flaskenv`` — would bind whatever value was present then. Flask's
    ``config.from_object`` fetches this attribute at application construction,
    which is where the credential is read once. ``default`` is used when the
    variable is unset or empty, and only the development configuration names
    one; without it a missing variable raises.
    """

    def __init__(self, default: str | None = None) -> None:
        self._default = default

    def __get__(
        self, instance: object | None, owner: type | None = None
    ) -> str:
        url = os.environ.get('DATABASE_URL')
        if url:
            return url
        if self._default is None:
            raise RuntimeError('DATABASE_URL environment variable is not set')
        return self._default


class Config:
    """Settings every environment shares."""

    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False


class DevConfig(Config):
    """Development and local-run settings: compose database by default."""

    SQLALCHEMY_DATABASE_URI = _DatabaseURL(_DEV_DATABASE_URL)


class TestConfig(Config):
    """Test settings: an in-memory SQLite database, discarded with the fixture.

    The engine is left untouched here. Flask-SQLAlchemy already hands an
    in-memory SQLite URL the single-connection pool it needs, and an explicit
    pool size for one is rejected — a size of 0 by its own check, any size by
    SQLAlchemy, whose StaticPool takes none — so naming a pool option would
    conflict with it.
    """

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'


class ProdConfig(Config):
    """Production settings: DATABASE_URL must come from the environment."""

    SQLALCHEMY_DATABASE_URI = _DatabaseURL()
