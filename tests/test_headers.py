'''Tests for the response headers ``create_app`` sets on every answer.

``create_app`` registers an ``after_request`` hook that adds the application's
own headers to whatever a route answered with: ``X-Content-Type-Options`` and
``X-Frame-Options`` on every response, and ``Cache-Control: no-store`` on the
JSON API alone, so the API's answers are never cached while the static index
document keeps the policy Flask gives it. No other module in this suite reads a
header, so without this one the hook could be dropped, narrowed to one route or
widened to the static document and every test would still pass.

Each test drives the real request path through the ``client`` fixture. The hook
runs on the response the route itself produced rather than on a fabricated one,
so these assertions cover the headers a live request answers with - including
the analysis route's 400, which shows the hook reaching a rejected request too.
'''


def test_api_response_carries_the_hardening_headers(client):
    response = client.get('/api/week/2021-11-13')

    assert response.status_code == 200
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Cache-Control'] == 'no-store'


def test_api_error_response_carries_the_hardening_headers(client):
    '''The hook covers a rejected request as well as a successful one.'''
    response = client.get('/api/analysis/not_a_feature')

    assert response.status_code == 400
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Cache-Control'] == 'no-store'


def test_static_index_keeps_its_own_cache_policy(client):
    '''The static document is not given the API's cache directive.

    It is served by ``send_static_file``, whose own ``no-cache`` must survive:
    widening the API's ``no-store`` to every path would silently replace the
    freshness policy of the built SPA, which is what this assertion pins.
    ``frontend/dist/index.html`` is a precondition here exactly as it is in
    ``test_index.py``, so ``npm run build`` has to have run.
    '''
    response = client.get('/')

    assert response.status_code == 200
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Cache-Control'] == 'no-cache'
