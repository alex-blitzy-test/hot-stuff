'''Tests for the suite's own client compatibility shim.

`CompatFlaskClient` in `tests/conftest.py` copies Flask 2.0.1's
`FlaskClient.open` so the retired `as_tuple` keyword is consumed instead of
being forwarded to the pinned Werkzeug client, which no longer declares it.
Every request the suite itself makes takes the plain ``client.get(<path>)``
shape and reaches only the builder path of that copy, so this module drives the
rest of its surface directly: the single-argument `EnvironBuilder`,
environ-dict and `Request` branches with the `environ_base` merge each
performs, the `buffered` and `follow_redirects` keywords, the `as_tuple=True`
return and the `flask._preserve_context` marker. A defect in any of them fails
here rather than staying silent.
'''

import pytest
from flask import redirect
from flask.testing import EnvironBuilder
from werkzeug.wrappers import Request as BaseRequest

# an endpoint that answers 200, so every branch below is judged by a real reply
PROBE_PATH = '/api/analysis/tempo'

# the two entries `FlaskClient.__init__` puts in `environ_base`, which every
# branch of the shim has to merge into the environment it builds
REMOTE_ADDR = '127.0.0.1'
USER_AGENT_PREFIX = 'werkzeug/'


def _environ(app, path=PROBE_PATH):
    '''A complete WSGI environment for `path`, built by the application.'''
    return EnvironBuilder(app, path).get_environ()


def test_open_accepts_an_environ_builder(app, client):
    '''The single-argument builder branch merges both environments.'''
    builder = EnvironBuilder(app, PROBE_PATH,
                             environ_base={'HTTP_X_PROBE': 'builder'})

    response = client.open(builder)

    assert response.status_code == 200
    assert response.get_json()['feature'] == 'tempo'
    # the builder's own base survives the merge with the client's
    assert response.request.environ['HTTP_X_PROBE'] == 'builder'
    assert response.request.environ['REMOTE_ADDR'] == REMOTE_ADDR
    assert response.request.environ['HTTP_USER_AGENT'].startswith(
        USER_AGENT_PREFIX)
    # the caller's builder is copied, not mutated
    assert builder.environ_base == {'HTTP_X_PROBE': 'builder'}


def test_open_accepts_an_environ_dict(app, client):
    '''The single-argument environ-dict branch merges the client's base.'''
    response = client.open(_environ(app))

    assert response.status_code == 200
    assert response.get_json()['feature'] == 'tempo'
    assert response.request.environ['REMOTE_ADDR'] == REMOTE_ADDR
    assert response.request.environ['HTTP_USER_AGENT'].startswith(
        USER_AGENT_PREFIX)


def test_open_accepts_a_request_object(app, client):
    '''The single-argument `Request` branch copies the request it is given.'''
    request = BaseRequest(_environ(app))

    response = client.open(request)

    assert response.status_code == 200
    assert response.get_json()['feature'] == 'tempo'
    assert response.request.environ['REMOTE_ADDR'] == REMOTE_ADDR
    # the caller's request keeps its own environment: the merge lands on a copy
    assert 'REMOTE_ADDR' not in request.environ


def test_open_as_tuple_answers_the_environment_and_the_response(client):
    '''`as_tuple=True` answers the `(environ, response)` pair.'''
    environment, response = client.open(PROBE_PATH, as_tuple=True)

    assert response.status_code == 200
    assert response.get_json()['feature'] == 'tempo'
    assert environment['PATH_INFO'] == PROBE_PATH
    # the environment answered is the request the response was produced from
    assert environment is response.request.environ


def test_open_buffers_the_response(client):
    '''`buffered=True` reaches Werkzeug's client and is drained into a list.'''
    buffered = client.open(PROBE_PATH, buffered=True)
    unbuffered = client.open(PROBE_PATH)

    # both types are read before either body is touched, because reading a body
    # drains any iterator into a list as well: the keyword is what has to make
    # the difference here, not the read. Unbuffered, Werkzeug hands the
    # application's iterator back instead of a list.
    assert isinstance(buffered.response, list)
    assert not isinstance(unbuffered.response, list)

    assert buffered.status_code == 200
    assert buffered.get_json()['feature'] == 'tempo'


def test_open_preserves_the_request_context_of_a_with_block(client):
    '''The `flask._preserve_context` marker follows the client's own state.'''
    with client:
        preserved = client.open(PROBE_PATH)
    plain = client.open(PROBE_PATH)

    assert preserved.request.environ['flask._preserve_context'] is True
    assert plain.request.environ['flask._preserve_context'] is False


@pytest.fixture
def redirecting_app(app):
    '''The seeded application with one test-local redirect.

    The application's own redirect, `GET /api/`, answers with a *relative*
    Location, which a browser resolves against `/api/` but Werkzeug's client
    resolves against the script root, so following it lands outside the rule.
    This route answers with the absolute target the keyword has to follow.
    '''
    app.add_url_rule('/api/probe-redirect', 'probe_redirect',
                     lambda: redirect(PROBE_PATH))
    return app


def test_open_follows_redirects(redirecting_app, client):
    '''`follow_redirects=True` reaches Werkzeug's client and follows.'''
    unfollowed = client.get('/api/probe-redirect')
    followed = client.get('/api/probe-redirect', follow_redirects=True)

    assert unfollowed.status_code == 302
    assert followed.status_code == 200
    assert len(followed.history) == 1
    assert followed.history[0].status_code == 302
    assert followed.get_json()['feature'] == 'tempo'
