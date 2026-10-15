'''Tests for the redirect that GET /api/ answers with.

/api/ answers with a redirect whose Location is the bare relative path
``week/<chart week>``. Relative is the point: a browser resolves that path
against ``/api/``, so the caller keeps talking to the origin that served the
request. The week itself is read through get_query_week rather than written
into the test, because the redirect aims at whichever chart Saturday the clock
stands nearest when the request runs.
'''

from datetime import datetime

from api.funcs import get_query_week


def test_api_root_redirects_to_the_current_chart_week(client):
    # the helper is read on both sides of the request: it flips its answer at
    # Wednesday 10:00 local time, so a run straddling that instant has the
    # handler answer from one side of the flip while the test computes from the
    # other. Keeping both values is what stops the boundary failing the test.
    week_before_request = get_query_week(None)
    response = client.get('/api/')
    week_after_request = get_query_week(None)

    assert response.status_code == 302

    location = response.headers['Location']
    assert location in {f'week/{week_before_request}',
                        f'week/{week_after_request}'}

    # relative, not absolute: a leading slash or a scheme would send the caller
    # out of /api/ instead of resolving the target against it
    assert not location.startswith('/')
    assert 'http' not in location

    # the target is a chart Saturday, which get_query_week returns for every
    # weekday by bucketing it onto the Saturday closing or opening its week
    assert datetime.strptime(
        location.removeprefix('week/'), '%Y-%m-%d').weekday() == 5
