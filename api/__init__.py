'''Application factory for the API.

create_app is the only place a Flask application is constructed. The extensions
stay unbound at module level so api.models can import them from this package,
and the route blueprint is imported inside the factory so that import cannot
become circular.
'''

from flask import Flask, Response
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

    # imported here rather than at module level: the blueprint decorates
    # against objects this module has to define first
    from api.routes import bp

    # no prefix argument, since the blueprint declares its own /api prefix and
    # a prefix passed here would replace it
    app.register_blueprint(bp)

    return app
