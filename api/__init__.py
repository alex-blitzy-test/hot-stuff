"""Flask application bootstrap for the hot-stuff API package.

Package initializer for the ``api`` package. Constructs the single Flask
application that powers the hot-stuff Billboard Hot 100 analytics backend and
wires together static-file serving, CORS, the PostgreSQL connection, and
Marshmallow serialization before registering the HTTP route handlers.

Single-origin design (CRITICAL): the app is created with
Flask(__name__, static_folder='../frontend/build', static_url_path='/'), so a
single Flask process serves BOTH the compiled React single-page application
(SPA) at the site root and the JSON API. static_url_path='/' maps the built
frontend under ../frontend/build to '/', while the handlers registered in
api/routes.py add the JSON endpoints under /api/*. (Source: api/__init__.py:L50)

CORS: CORS(app) enables cross-origin requests so clients served from another
origin may call the /api/* endpoints. (Source: api/__init__.py:L51)

Database: SQLALCHEMY_DATABASE_URI is set to
postgresql://postgres:postgres@postgres/db. The host segment "postgres" is the
Docker Compose service name of the PostgreSQL 15 container
(Source: docker-compose.yml:L15-L22), not a literal DNS hostname; Compose's internal
network resolves it to the database container. SQLALCHEMY_TRACK_MODIFICATIONS
is disabled to suppress SQLAlchemy's event-notification overhead.
(Source: api/__init__.py:L55,L57-L58)

Deliberate trailing side-effect import: "from api import routes" is
intentionally the LAST statement in this module. Importing it executes the
@app.route(...) decorators in api/routes.py, registering every handler against
the already-initialized app. It must remain at the bottom to avoid a
circular-import / partial-initialization error, because api/routes.py imports
app back from this module. (Source: api/__init__.py:L68)

Attributes:
    app (flask.Flask): The Flask application/server instance. Imported by
        api/routes.py to register the route handlers.
    db (flask_sqlalchemy.SQLAlchemy): SQLAlchemy handle and ORM base, imported
        by api/models.py to declare the Tracks and YearlyAvg models.
    ma (flask_marshmallow.Marshmallow): Marshmallow handle, imported by
        api/models.py to declare TrackSchema and YearlyAvgSchema.
        (Source: api/__init__.py:L62-L63)
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import os

# init app: create the Flask server; static_folder serves the compiled React
# build (../frontend/build) at the site root '/' (single-origin: SPA + API)
app = Flask(__name__, static_folder='../frontend/build', static_url_path='/')
CORS(app)  # enable cross-origin requests for the /api/* endpoints

# database: host segment "postgres" is the docker-compose service name of the
# PostgreSQL 15 container (see docker-compose.yml), not a literal hostname
dbURL = f'postgresql://postgres:postgres@postgres/db'

app.config['SQLALCHEMY_DATABASE_URI'] = dbURL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize db and ma: module-level singletons shared across the package
# (api/models.py uses db and ma; api/routes.py uses app)
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Deliberate side-effect import: registers all @app.route handlers against the
# initialized app. MUST remain the LAST statement; api/routes.py imports app
# back from this module, so importing earlier would raise a circular-import error.
from api import routes
