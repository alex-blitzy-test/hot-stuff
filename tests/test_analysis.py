'''Tests for the GET /api/analysis/<feature> endpoint.

The seeded yearly averages cover six consecutive chart years, the shortest span
whose five-year rolling window produces a value at all, so the endpoint answers
with exactly the 2019 and 2020 rows: the year's own mean and the mean over the
window that ends there.

The route projects one column of YearlyAvg, chosen by the feature path
segment, and answers 400 for a segment outside its allow-list; both halves
are pinned here: the eight allow-listed features and their payload, and the
refusal.

The order those rows arrive in is a third premise, and it comes from storage
rather than from the query: the route projects them through an unordered
`with_entities` call, so they come back in rowid order, and this table's rowid
is its `index` primary key. The fixture declares `index` and `year` ascending
together, so it is that correspondence, not the order the fixture inserted the
six rows in, that makes the premise hold, and `get_rolling_avg` rolls the rows
in the order it receives them. The assertions below are therefore an
`index`-order assumption as well as a rolling-window one, and a renumbered
`index` would move the years and the rolling values they expect. The route must
not gain an `ORDER BY` to make that premise explicit: its payload and its row
order are frozen, so the dependency is recorded here instead of being enforced
in SQL.
'''

import pytest

# Exactly the columns the route may project: every YearlyAvg column except the
# row key and the year label.
RECOGNISED_FEATURES = (
    'acousticness',
    'danceability',
    'energy',
    'instrumentalness',
    'liveness',
    'speechiness',
    'tempo',
    'valence',
)

# The names the route refuses. Both halves of the derivation above are pinned
# here: the three model class attributes that are not columns at all - `query`,
# `__tablename__` and `metadata` - and the two real columns the derivation
# subtracts on purpose, `index` (the row key) and `year` (the label the route
# projects for itself).
REFUSED_FEATURES = (
    'query',
    '__tablename__',
    'metadata',
    'index',
    'year',
)

# The two years the window covers, in the order the endpoint returns them.
YEARS = ['2019', '2020']

# The seeded means and the rolling means they produce, per feature. Comparing
# two features is what proves the requested column is the one aggregated: a
# payload that always rolled `energy` would satisfy the shape and fail `tempo`.
EXPECTED_POINTS = {
    'energy': [(0.5, 0.3), (0.6, 0.4)],
    'tempo': [(140.0, 120.0), (150.0, 130.0)],
}


@pytest.mark.parametrize('feature', sorted(EXPECTED_POINTS))
def test_analysis_returns_the_means_of_the_requested_feature(client, feature):
    response = client.get(f'/api/analysis/{feature}')

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {'feature', 'data'}
    # the path segment is echoed verbatim, not re-cased
    assert body['feature'] == feature
    assert [row['year'] for row in body['data']] == YEARS
    assert all(
        set(row) == {'year', 'value', 'rolling'}
        for row in body['data']
    )
    values, rollings = zip(*EXPECTED_POINTS[feature])
    assert [row['value'] for row in body['data']] == pytest.approx(values)
    assert [row['rolling'] for row in body['data']] == pytest.approx(rollings)


@pytest.mark.parametrize('feature', RECOGNISED_FEATURES)
def test_every_recognised_feature_is_accepted(client, feature):
    response = client.get(f'/api/analysis/{feature}')

    assert response.status_code == 200
    body = response.get_json()
    assert body['feature'] == feature
    assert [row['year'] for row in body['data']] == YEARS
    assert all(
        set(row) == {'year', 'value', 'rolling'}
        for row in body['data']
    )


def test_unknown_feature_is_rejected_with_400(client):
    response = client.get('/api/analysis/not_a_feature')

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Unknown feature: not_a_feature'}


@pytest.mark.parametrize('feature', REFUSED_FEATURES)
def test_model_attributes_are_not_accepted_as_features(client, feature):
    '''Names the allow-list refuses: non-column model attributes and the two
    columns it subtracts.'''
    response = client.get(f'/api/analysis/{feature}')

    assert response.status_code == 400
    body = response.get_json()
    assert 'error' in body
    assert feature in body['error']
