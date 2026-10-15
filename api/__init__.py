'''Application factory for the API.

create_app is the only place a Flask application is constructed. The extensions
stay unbound at module level so api.models can import them from this package,
and the route blueprint is imported inside the factory so that import cannot
become circular. The two after-request hooks registered here are the only place
a response is modified: the hardening headers every answer carries, and the
gzip representation a client that offers gzip receives in place of the raw one.
'''

from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import gzip
import os
from typing import Any
from api.config import (Config, DevConfig, ProdConfig, TestConfig,
                        check_database_url)

# initialized without an app and bound by create_app, which is what lets
# api.models import them from here
db = SQLAlchemy()
ma = Marshmallow()

# the two codings that mean gzip on the wire, plus the wildcard a client uses
# to accept whatever coding the server offers
_GZIP_CODINGS = ('gzip', 'x-gzip')

# media types whose payload is text, so a byte-level repetition is expected and
# deflate reliably shrinks them; anything else - images, fonts, the favicon -
# is already compressed in its own format and is served exactly as it is
_COMPRESSIBLE_MEDIA_TYPES = frozenset((
    'application/javascript',
    'application/x-javascript',
    'application/ecmascript',
    'application/json',
    'application/xml',
    'application/xhtml+xml',
    'image/svg+xml',
))

# below this body size the gzip header and trailer can leave the answer longer
# than the bytes it carries, so the representation is left as it is
_MIN_COMPRESSIBLE_SIZE = 512

# the level the served bundle's own figures come from: it takes the entry
# bundle from 1,213,938 bytes to 293,329, and a fixed mtime keeps the bytes of
# one body identical on every run
_GZIP_LEVEL = 6


def _accepted_encodings(accept_encoding: str | None) -> dict[str, float]:
    '''The codings an Accept-Encoding header names, with their q-values.

    A header that is absent names no coding - a client that says nothing about
    encodings has agreed to none - and a coding named without a q-value is
    accepted. A q-value that cannot be read as a number refuses its coding,
    which keeps a malformed header from being read as an acceptance.
    '''
    if not accept_encoding:
        return {}
    accepted: dict[str, float] = {}
    for entry in accept_encoding.split(','):
        coding, _, parameters = entry.partition(';')
        coding = coding.strip().lower()
        if not coding:
            continue
        quality = 1.0
        for parameter in parameters.split(';'):
            name, _, value = parameter.partition('=')
            if name.strip().lower() == 'q':
                try:
                    quality = float(value.strip())
                except ValueError:
                    quality = 0.0
        accepted[coding] = quality
    return accepted


def _accepts_gzip(accept_encoding: str | None) -> bool:
    '''Whether an Accept-Encoding header allows a gzip representation.

    A coding the header names decides the answer itself, so ``gzip;q=0``
    refuses even where the wildcard would allow it and ``x-gzip`` stands for
    ``gzip``; a named coding or the wildcard with a positive q-value accepts.
    '''
    accepted = _accepted_encodings(accept_encoding)
    for coding in _GZIP_CODINGS:
        if coding in accepted:
            return accepted[coding] > 0
    return accepted.get('*', 0.0) > 0


def _is_compressible(media_type: str | None) -> bool:
    '''Whether a representation of this media type is worth gzipping.'''
    if not media_type:
        return False
    media_type = media_type.lower()
    if media_type.startswith('text/'):
        return True
    if media_type in _COMPRESSIBLE_MEDIA_TYPES:
        return True
    # a structured suffix says the payload is a text document in a JSON or an
    # XML envelope whatever its top-level type is
    return media_type.endswith('+json') or media_type.endswith('+xml')


def _replace_body(response: Response, stream: Any, payload: bytes) -> None:
    '''Hands the response the bytes already read from its own body stream.

    ``set_data`` swaps the body for the payload but leaves the response in
    direct-passthrough mode, and the stream Werkzeug's ``send_file`` wrapped -
    the file object whose descriptor this response owns - is dropped rather
    than closed. Both are undone here, so that descriptor is released with the
    answer instead of whenever the collector next happens to run.
    '''
    response.set_data(payload)
    response.direct_passthrough = False
    close = getattr(stream, 'close', None)
    if close is not None:
        close()


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
    # operator's to see: a value this process cannot use at all stops
    # construction, while a store that cannot be reached is only reported, so a
    # deployment whose database is not up yet still serves the static
    # interface; TestConfig is exempt, because its in-memory database belongs
    # to the test fixture and not to a deployment
    if not issubclass(config_class, TestConfig):
        unreachable = check_database_url(app.config['SQLALCHEMY_DATABASE_URI'])
        if unreachable is not None:
            app.logger.warning(unreachable)

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

    # Gives a client that offers gzip the representation it asked for, which is
    # the same body deflated and framed with Content-Encoding rather than a
    # change to anything the route answered with. Werkzeug serves static files
    # and JSON bodies uncompressed, and neither the pinned dependency set nor
    # the deployment carries a compression layer, so the negotiation is here.
    @app.after_request
    def compress_response(response: Response) -> Response:
        '''Gzips a compressible body for a client that offered gzip.

        Only a complete, uncoded 200 is compressed: a 304 and a 206 answer
        exactly as they do today, because a revalidated asset's bytes are
        already in the client's cache and a ranged read's Content-Length is
        part of the answer. The bytes read here go back unchanged whenever
        compression would not make them shorter.
        '''
        if not _is_compressible(response.mimetype):
            return response
        # the representation follows from this request header alone, so a
        # shared cache must not answer another client with the one sent here
        response.vary.add('Accept-Encoding')
        if (response.status_code != 200
                or 'Content-Encoding' in response.headers
                or 'Range' in request.headers
                or not _accepts_gzip(request.headers.get('Accept-Encoding'))):
            return response
        stream = response.response
        body = b''.join(response.iter_encoded())
        compressed = (gzip.compress(body, compresslevel=_GZIP_LEVEL, mtime=0)
                      if len(body) >= _MIN_COMPRESSIBLE_SIZE else None)
        if compressed is None or len(compressed) >= len(body):
            _replace_body(response, stream, body)
            return response
        _replace_body(response, stream, compressed)
        response.headers['Content-Encoding'] = 'gzip'
        return response

    # imported here rather than at module level: the blueprint decorates
    # against objects this module has to define first
    from api.routes import bp

    # no prefix argument, since the blueprint declares its own /api prefix and
    # a prefix passed here would replace it
    app.register_blueprint(bp)

    return app
