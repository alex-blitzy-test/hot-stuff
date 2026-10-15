'''Tests for the gzip representation ``create_app`` negotiates.

``create_app`` registers an ``after_request`` hook that answers a client
offering gzip with the same body deflated and framed with
``Content-Encoding: gzip``, and marks every answer whose media type it could
compress with ``Vary: Accept-Encoding``. Without this module nothing in the
suite would notice the negotiation being dropped, widened to a status it must
leave alone, or made to lose the bytes of the representation it replaces: the
test client sends no ``Accept-Encoding`` header of its own, so every other
module sees exactly the identity bytes it saw before.

Each test drives the real request path through the ``client`` fixture, and the
assets under test are resolved from the built ``index.html`` rather than by
naming the content hashes the last build happened to emit. Werkzeug's test
client does not decode ``Content-Encoding``, so a compressed body is gunzipped
here with the standard library.

``frontend/dist`` is a precondition of this module exactly as it is of
``test_index.py``: ``npm run build`` has to have run, and without it the asset
lookup raises rather than skipping.
'''

import gzip
import os
import re

import pytest

# The body size below which the gzip header and trailer are not worth paying,
# which is the limit the negotiation itself applies: a body under it is served
# as it is even to a client that offered gzip.
SMALL_BODY_LIMIT = 512


def _built_index(app):
    '''The markup of the built document the server hands to a browser.'''
    with open(os.path.join(app.static_folder, 'index.html'),
              encoding='utf-8') as handle:
        return handle.read()


def _entry_bundle(app):
    '''The URL of the served entry bundle and the file behind it.

    The bundle is the module script the built index.html loads, resolved from
    the document rather than by naming the build hash it carries, so the test
    follows the asset a first visit actually pays for. The lazily imported
    export chunks the panels pull in are larger still and are not this file.
    '''
    script = re.search(r'<script[^>]*\bsrc="([^"]+)"', _built_index(app))
    if script is None:
        raise AssertionError('the built index.html names no script to load')
    url = script.group(1)
    return url, os.path.join(app.static_folder, url.lstrip('/'))


def _stylesheet(app):
    '''The URL of the served stylesheet and the file behind it.

    The built document also links a webfont stylesheet on a third-party origin;
    the one the server itself holds is the same-origin link, so only a path the
    static folder can serve is taken.
    '''
    tags = re.findall(r'<link[^>]*>', _built_index(app))
    matched = [re.search(r'href="(/[^"]+)"', tag) for tag in tags
               if 'rel="stylesheet"' in tag]
    href = next((href for href in matched if href is not None), None)
    if href is None:
        raise AssertionError('the built index.html links no served stylesheet')
    url = href.group(1)
    return url, os.path.join(app.static_folder, url.lstrip('/'))


def _get(client, url, **kwargs):
    '''A request whose file-backed body the client closes for itself.

    The test client hands a served file straight back: a response that is not
    buffered holds the file open until the collector runs, which surfaces as a
    ResourceWarning. Buffering it lets the client close the file instead.
    '''
    return client.get(url, buffered=True, **kwargs)


def _on_disk(path):
    '''The bytes of a built asset, read the way the server reads them.'''
    with open(path, 'rb') as handle:
        return handle.read()


def test_built_asset_is_gzipped_and_gunzips_to_the_file(client, app):
    url, path = _entry_bundle(app)
    on_disk = _on_disk(path)

    response = _get(client, url, headers={'Accept-Encoding': 'gzip'})

    assert response.status_code == 200
    assert response.headers['Content-Encoding'] == 'gzip'
    # the compressed body is what crosses the wire, so the length declared is
    # the compressed one and matches the body the client received
    assert int(response.headers['Content-Length']) == len(response.data)
    assert len(response.data) < len(on_disk)
    # the representation is the file, deflated: not a rewriting of it
    assert gzip.decompress(response.data) == on_disk
    # the representation depends on the request header that chose it
    assert 'Accept-Encoding' in response.headers['Vary']


def test_built_stylesheet_is_gzipped_and_gunzips_to_the_file(client, app):
    url, path = _stylesheet(app)
    on_disk = _on_disk(path)

    response = _get(client, url, headers={'Accept-Encoding': 'gzip'})

    assert response.status_code == 200
    assert response.headers['Content-Encoding'] == 'gzip'
    assert int(response.headers['Content-Length']) == len(response.data)
    assert len(response.data) < len(on_disk)
    assert gzip.decompress(response.data) == on_disk
    assert 'Accept-Encoding' in response.headers['Vary']


def test_built_asset_is_untouched_without_accept_encoding(client, app):
    url, path = _entry_bundle(app)
    on_disk = _on_disk(path)

    response = _get(client, url)

    assert response.status_code == 200
    assert 'Content-Encoding' not in response.headers
    assert response.headers['Content-Length'] == str(len(on_disk))
    assert response.data == on_disk
    # a client that agrees to no encoding still gets an answer marked as one
    # that varies with the header, which is what a shared cache needs
    assert 'Accept-Encoding' in response.headers['Vary']


@pytest.mark.parametrize('accept_encoding', ['gzip;q=0', 'gzip;q=0, *'])
def test_gzip_refused_on_request_is_not_served(client, app, accept_encoding):
    url, path = _entry_bundle(app)
    on_disk = _on_disk(path)

    response = _get(client, url, headers={'Accept-Encoding': accept_encoding})

    assert response.status_code == 200
    # a refusal the header states outright wins over the wildcard beside it
    assert 'Content-Encoding' not in response.headers
    assert response.data == on_disk


@pytest.mark.parametrize('accept_encoding',
                         ['x-gzip', '*', 'deflate, gzip;q=0.5'])
def test_gzip_is_served_under_the_other_accepted_spellings(client, app,
                                                           accept_encoding):
    url, path = _entry_bundle(app)
    on_disk = _on_disk(path)

    response = _get(client, url, headers={'Accept-Encoding': accept_encoding})

    # the older name for the format, the wildcard, and a positive q-value
    # beside a coding that was not asked for all accept the same body
    assert response.headers['Content-Encoding'] == 'gzip'
    assert gzip.decompress(response.data) == on_disk


def test_json_api_response_is_gzipped_and_identical_after_gunzip(client):
    identity = _get(client, '/api/week/2021-11-13')

    response = _get(client, '/api/week/2021-11-13',
                    headers={'Accept-Encoding': 'gzip'})

    assert response.status_code == 200
    # the case this covers: a compressible 200 whose body is over the limit
    assert len(identity.data) >= SMALL_BODY_LIMIT
    assert response.headers['Content-Encoding'] == 'gzip'
    assert int(response.headers['Content-Length']) == len(response.data)
    # the payload is unchanged, which is what keeps the endpoint's contract
    assert gzip.decompress(response.data) == identity.data
    # and it keeps the cache directive the hardening hook gives the JSON API
    assert response.headers['Cache-Control'] == 'no-store'


def test_small_json_body_is_left_uncompressed_but_varies(client):
    identity = _get(client, '/api/analysis/tempo')

    response = _get(client, '/api/analysis/tempo',
                    headers={'Accept-Encoding': 'gzip'})

    # the case this covers: a compressible 200 whose body is under the limit
    assert len(identity.data) < SMALL_BODY_LIMIT
    assert response.status_code == 200
    assert 'Content-Encoding' not in response.headers
    assert response.data == identity.data
    assert 'Accept-Encoding' in response.headers['Vary']


def test_ranged_request_is_left_ranged_and_uncompressed(client, app):
    url, path = _entry_bundle(app)
    on_disk = _on_disk(path)

    response = _get(client, url, headers={'Accept-Encoding': 'gzip',
                                          'Range': 'bytes=0-99'})

    # a range read is answered from the identity bytes the range was measured
    # against, so its length and body are the ones the range asked for
    assert response.status_code == 206
    assert 'Content-Encoding' not in response.headers
    assert response.headers['Content-Length'] == '100'
    assert response.data == on_disk[:100]


def test_head_reports_the_compressed_answer_it_would_send(client, app):
    url, _ = _entry_bundle(app)

    get = _get(client, url, headers={'Accept-Encoding': 'gzip'})
    response = client.head(url, headers={'Accept-Encoding': 'gzip'},
                           buffered=True)

    assert response.status_code == 200
    # what the GET answers with, headlined by a body that is not sent
    assert response.headers['Content-Encoding'] == 'gzip'
    assert response.headers['Content-Length'] == get.headers['Content-Length']
    assert response.data == b''
    assert 'Accept-Encoding' in response.headers['Vary']
