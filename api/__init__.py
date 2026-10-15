'''Application factory for the API.

create_app is the only place a Flask application is constructed. The extensions
stay unbound at module level so api.models can import them from this package,
and the route blueprint is imported inside the factory so that import cannot
become circular.
'''

from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import os
from api.config import (Config, DevConfig, ProdConfig, TestConfig,
                        check_database_url)

# initialized without an app and bound by create_app, which is what lets
# api.models import them from here
db = SQLAlchemy()
ma = Marshmallow()


def create_app(config: type[Config] | None = None) -> Flask:
    '''Builds the application.

    A configuration class passed in always wins. Otherwise FLASK_ENV selects
    one: development for a host-side flask run, production settings for
    anything else. The test configuration is never selected here - the test
    fixtures pass it.
    '''
    if config is not None:
        config_class: type[Config] = config
    elif os.getenv('FLASK_ENV') == 'development':
        config_class = DevConfig
    else:
        config_class = ProdConfig

    app = Flask(__name__, static_folder='../frontend/dist',
                static_url_path='/')

    # applied before the extensions are bound so init_app's defaults and
    # deprecation check see the values and the first engine use finds the URI
    app.config.from_object(config_class)

    # the connection string is exercised here, where a misconfiguration is the
    # operator's to see; TestConfig is exempt, because its in-memory database
    # belongs to the test fixture and not to a deployment
    if not issubclass(config_class, TestConfig):
        check_database_url(app.config['SQLALCHEMY_DATABASE_URI'])

    db.init_app(app)
    ma.init_app(app)
    CORS(app)

    # the index rule belongs to the application rather than to the api
    # blueprint, because it serves the file the static folder above holds
    @app.route('/')
    def index() -> Response:
        return app.send_static_file('index.html')

    # Sets the two headers on every response, refused requests included, and
    # Cache-Control: no-store on the JSON API alone; no route, status or
    # payload is otherwise touched. A Date the response carries is dropped,
    # because the server that sends the response always writes one of its own
    # while Werkzeug's conditional send_file path stamps a second onto the
    # response object for the index document and the assets beside it - the
    # duplicate this removes, leaving exactly the server's Date on the wire.
    # Strict-Transport-Security is deliberately absent, because no TLS is
    # terminated for this application, and the Server header cannot be silenced
    # from here - Werkzeug's HTTP handler writes it before this response object
    # exists.
    @app.after_request
    def add_response_headers(response: Response) -> Response:
        '''The static index document keeps the Cache-Control header
        send_static_file gives it, and carries no Date of its own.
        '''
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        # Date belongs to the server that sends the response; send_file's
        # conditional path adds one too, so the response's own is removed here
        response.headers.pop('Date', None)
        return response

    # imported here rather than at module level: the blueprint decorates
    # against objects this module has to define first
    from api.routes import bp

    # no prefix argument, since the blueprint declares its own /api prefix and
    # a prefix passed here would replace it
    app.register_blueprint(bp)

    return app
