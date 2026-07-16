"""Flask application bootstrap for the hot-stuff API package.

This package initializer builds the single, shared Flask application that
powers the hot-stuff Billboard Hot 100 audio-feature analytics backend. It
is imported for its side effects: it creates the ``app`` object, configures
the database, instantiates the shared SQLAlchemy and Marshmallow
extensions, and (via the trailing import) registers the HTTP route
handlers.

Single-origin design:
    The app is created with ``Flask(__name__,
    static_folder='../frontend/build', static_url_path='/')``, so a SINGLE
    Flask process serves BOTH the compiled React single-page application
    (SPA) and the JSON API. ``static_url_path='/'`` maps the built frontend
    under ``../frontend/build`` to the site root ``/``, while the route
    handlers in ``api/routes.py`` add the ``/api/*`` JSON endpoints on top
    of the same process. (Source: api/__init__.py:L64)

CORS:
    ``CORS(app)`` enables cross-origin requests against the API so browser
    clients loaded from a different origin can call the ``/api/*``
    endpoints. (Source: api/__init__.py:L66)

Database configuration:
    ``SQLALCHEMY_DATABASE_URI`` is set to
    ``postgresql://postgres:postgres@postgres/db``. The host segment
    ``postgres`` is the Docker Compose service name of the PostgreSQL 15
    container (Source: docker-compose.yml:L15-L22), not a literal hostname;
    Compose resolves it to the database container on the shared network. The
    ``postgres:postgres`` username/password are the repository's existing
    Docker Compose development-only defaults
    (Source: docker-compose.yml:L19-L22) and must be replaced with secure
    credentials before any production deployment.
    ``SQLALCHEMY_TRACK_MODIFICATIONS`` is disabled to suppress the
    SQLAlchemy event-notification overhead.
    (Source: api/__init__.py:L71,L73-L75)

Shared extensions:
    ``db = SQLAlchemy(app)`` and ``ma = Marshmallow(app)`` are
    module-level singletons imported across the package: ``api/models.py``
    imports ``db`` and ``ma`` to declare the ORM models and schemas, while
    ``api/routes.py`` imports ``app`` to register its endpoints.
    (Source: api/__init__.py:L80-L81; api/models.py:L1, api/routes.py:L29)

Deliberate trailing side-effect import:
    ``from api import routes`` intentionally appears LAST. Importing it
    executes ``api/routes.py``, registering every ``@app.route(...)``
    handler against the already-initialized ``app``. It must stay at the
    bottom because ``api/routes.py`` imports ``app`` back from this module,
    so importing routes any earlier would raise a circular-import /
    partial-initialization error. (Source: api/__init__.py:L87)
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import os

# init app: a single Flask process serves the whole application.
# static_folder points at the compiled React build (../frontend/build) and
# static_url_path='/' mounts it at the site root, so this one process
# serves both the SPA and the JSON API (single-origin design).
app = Flask(__name__, static_folder='../frontend/build', static_url_path='/')
# enable cross-origin requests so browser clients can reach /api/* endpoints
CORS(app)

# database: the 'postgres' host segment below is the Docker Compose
# service name of the PostgreSQL 15 container (see docker-compose.yml:L15-L22),
# not a literal hostname; Compose resolves it to the DB container.
dbURL = f'postgresql://postgres:postgres@postgres/db'

app.config['SQLALCHEMY_DATABASE_URI'] = dbURL
# disable modification tracking to avoid SQLAlchemy event-notify overhead
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize db and ma: module-level singletons shared across the api
# package (api/models.py imports db and ma to declare models/schemas;
# api/routes.py imports app to register endpoints).
db = SQLAlchemy(app)
ma = Marshmallow(app)

# deliberate side-effect import: executing api/routes.py registers every
# @app.route(...) handler against the initialized app above. MUST remain
# the LAST statement: api/routes.py imports app back from this module,
# so importing it any earlier would raise a circular-import error.
from api import routes
