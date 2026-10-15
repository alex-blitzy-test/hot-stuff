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
from api.config import Config, DevConfig, ProdConfig

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
    db.init_app(app)
    ma.init_app(app)
    CORS(app)

    # the index rule belongs to the application rather than to the api
    # blueprint, because it serves the file the static folder above holds
    @app.route('/')
    def index() -> Response:
        return app.send_static_file('index.html')

    # additive response hardening, sitting beside the rule it covers: the two
    # headers below are set on every response and change no route, status,
    # payload or extension behaviour. Strict-Transport-Security is deliberately
    # absent, because no TLS is terminated for this application, and the Server
    # header cannot be silenced from here - Werkzeug's HTTP handler writes it
    # before this response object exists.
    @app.after_request
    def add_response_headers(response: Response) -> Response:
        '''Adds the response headers this application owns.

        Both headers are set on every response; the cache directive applies to
        the JSON API only, so the static index document keeps the Cache-Control
        header send_static_file already gives it.
        '''
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    # imported here rather than at module level: the blueprint decorates
    # against objects this module has to define first
    from api.routes import bp

    # no prefix argument, since the blueprint declares its own /api prefix and
    # a prefix passed here would replace it
    app.register_blueprint(bp)

    return app
