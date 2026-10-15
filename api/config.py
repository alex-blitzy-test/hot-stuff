'''Configuration objects for the application factory.

``DATABASE_URL`` is read in this module and nowhere else, and it is read when
the configuration is consumed — at application construction — rather than
at import. A deployment supplies its own connection string through the
environment: the ``api`` service in ``docker-compose.yml`` for the container,
``.flaskenv`` for a host-side ``flask run``. No deployment credential is
embedded here — the development default below is the compose service's own
public placeholder, not a secret, and it applies only while ``DATABASE_URL``
is unset or empty.

The start-up check below (``check_database_url``) keeps a value this process
cannot use at all — one that will not parse, or that names no installed
dialect or driver — fatal at construction, because no retry repairs it and a
deployment should be told rather than left running with a string it cannot
use. A store that is merely unreachable is reported instead, so a deployment
whose database is not accepting connections yet still starts and serves the
interface that reads none.
'''

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

# Development default: the postgres service docker-compose.yml declares
# (POSTGRES_USER/POSTGRES_PASSWORD 'postgres', POSTGRES_DB 'db').
_DEV_DATABASE_URL = 'postgresql://postgres:postgres@postgres/db'

# The ceiling on one PostgreSQL connection attempt made by the start-up check.
# A host that accepts no connection at all would otherwise hold that check -
# and with it this application's interface, which reads no database - for as
# long as the operating system keeps its own TCP timeout, which is minutes. A
# deployment that names its own timeout in the URL's query keeps it instead.
_CONNECT_TIMEOUT_SECONDS = 5


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


def check_database_url(url: str) -> str | None:
    '''Checks the connection string; reports a store that cannot be reached.

    SQLAlchemy opens its connection lazily, inside the first request that
    reads the database, so without this the constructor would accept any
    string at all — malformed, unreachable, or naming a dialect this
    application has no driver for — and a misconfigured deployment would start
    happily and answer HTTP 500 to its first caller, with the cause visible
    nowhere but the server log.

    Exercising the value here moves that failure to construction, where the
    operator sees it, and separates the two kinds it can be. A value this
    process cannot turn into an engine at all — one that does not parse, or
    that names a dialect or driver no installed package provides — is a
    misconfiguration no retry repairs, so it raises: what fails is re-raised
    as a ``RuntimeError`` naming the variable the operator has to correct and
    the failure's class, and carrying neither the connection string nor any of
    SQLAlchemy's own text. The value is a credential, and this message goes to
    the process's own log at construction. The original exception stays
    reachable through ``__context__`` for a debugger, but its context is
    suppressed, so the log line prints nothing of the value.

    A store that merely cannot be reached is returned instead of raised, as
    the warning text to log, and that difference is what lets a deployment
    start before its database does: under ``docker compose up`` the database
    container needs a moment before it accepts connections, and a store that
    is unreachable, refusing the credential or not yet listening must not keep
    the application from serving the static interface, which reads no database
    at all. Only the endpoints that read the database fail until the store
    answers, and each of those logs its own traceback when it does.

    The connection is closed again immediately, so the check costs one round
    trip and leaves no pool behind.
    '''
    # Two kinds of failure are separated below. What lands in the first except
    # is the value itself, which no restart repairs: a string that does not
    # parse or whose port is unreadable (ArgumentError, ValueError), or a
    # scheme whose dialect or driver no installed package provides
    # (NoSuchModuleError, an ArgumentError here, or the ImportError a missing
    # driver module raises).
    try:
        parsed = make_url(url)
        # A PostgreSQL probe is bounded, because psycopg2 would otherwise wait
        # out the operating system's own TCP timeout against a host that
        # accepts no connection. The bound arrives through connect_args rather
        # than in the URL's query, so the connection string stays exactly as
        # the deployment wrote it, and it is applied to that dialect alone:
        # sqlite3's connect() rejects a keyword it does not know, and
        # SQLAlchemy hands connect_args to the driver unchanged. A query that
        # names its own connect_timeout wins — the deployment knows its store
        # better than this file does.
        connect_args: dict[str, int] = {}
        if parsed.get_dialect().name == 'postgresql':
            if 'connect_timeout' not in parsed.query:
                connect_args['connect_timeout'] = _CONNECT_TIMEOUT_SECONDS
        engine: Engine = create_engine(url, connect_args=connect_args)
    except (ArgumentError, ImportError, ValueError) as exc:
        raise RuntimeError(
            'DATABASE_URL is not a usable connection string '
            f'({type(exc).__name__})'
        ) from None

    try:
        with engine.connect():
            pass
    except (SQLAlchemyError, OSError) as exc:
        return (
            'DATABASE_URL could not be reached from this process '
            f'({type(exc).__name__}): the application starts and serves the '
            'static interface, and the endpoints that read the database fail '
            'until the store is reachable'
        )
    finally:
        engine.dispose()
    return None
