'''Configuration objects for the application factory.

``DATABASE_URL`` is read in this module and nowhere else, and it is read when
the configuration is consumed — at application construction — rather than
at import. A deployment supplies its own connection string through the
environment: the ``api`` service in ``docker-compose.yml`` for the container,
``.flaskenv`` for a host-side ``flask run``. No deployment credential is
embedded here — the development default below is the compose service's own
public placeholder, not a secret, and it applies only while ``DATABASE_URL``
is unset or empty.
'''

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Development default: the postgres service docker-compose.yml declares
# (POSTGRES_USER/POSTGRES_PASSWORD 'postgres', POSTGRES_DB 'db').
_DEV_DATABASE_URL = 'postgresql://postgres:postgres@postgres/db'


class _DatabaseURL:
    '''Resolve DATABASE_URL when the configuration is consumed, not at import.

    A read in a class body would run at import time, so a process whose
    environment is not final yet — the test runner, which loads no
    ``.flaskenv`` — would bind whatever value was present then. Flask's
    ``config.from_object`` fetches this attribute at application construction,
    which is where the credential is read once. ``default`` is used when the
    variable is unset or empty, and only the development configuration names
    one; without it a missing variable raises.
    '''

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
    '''Settings every environment shares.'''

    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False


class DevConfig(Config):
    '''Development and local-run settings: compose database by default.'''

    SQLALCHEMY_DATABASE_URI = _DatabaseURL(_DEV_DATABASE_URL)


class TestConfig(Config):
    '''Test settings: an in-memory SQLite database, discarded with the fixture.

    The engine is left untouched here. Flask-SQLAlchemy already hands an
    in-memory SQLite URL the single-connection pool it needs, and an explicit
    pool size for one is rejected — a size of 0 by its own check, any size by
    SQLAlchemy, whose StaticPool takes none — so naming a pool option would
    conflict with it.
    '''

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'


class ProdConfig(Config):
    '''Production settings: DATABASE_URL must come from the environment.'''

    SQLALCHEMY_DATABASE_URI = _DatabaseURL()


def check_database_url(url: str) -> None:
    '''Raise unless this process can use the connection string.

    SQLAlchemy opens its connection lazily, inside the first request that reads
    the database, so without this the constructor would accept any string at all
    — malformed, unreachable, or naming a dialect this application has no driver
    for — and a misconfigured deployment would start happily and answer HTTP 500
    to its first caller, with the cause visible nowhere but the server log.

    Exercising the value here moves that failure to construction, where the
    operator sees it. Connecting is what catches all of it: parsing alone accepts
    an unregistered scheme, and only a connection attempt reports a missing
    directory or a refused port. The connection is closed again immediately, so
    the check costs one round trip and leaves no pool behind.

    What fails is re-raised as a ``RuntimeError`` naming the variable the
    operator has to correct and the failure's class, and carrying neither
    the connection string nor any of SQLAlchemy's own text: the value is
    a credential, and this message goes to the process's own log at
    construction. The original exception stays reachable through
    ``__context__`` for a debugger, but its context is suppressed, so the
    log line prints nothing of the value. No response carries the message
    either, because no request exists yet.
    '''
    engine: Engine | None = None
    try:
        engine = create_engine(url)
        with engine.connect():
            pass
    except (SQLAlchemyError, ImportError, ValueError, OSError) as exc:
        raise RuntimeError(
            'DATABASE_URL is not a usable connection string '
            f'({type(exc).__name__})'
        ) from None
    finally:
        if engine is not None:
            engine.dispose()
