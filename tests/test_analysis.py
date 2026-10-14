'''Tests for the GET /api/analysis/<feature> endpoint.

The seeded yearly averages cover six consecutive chart years, the shortest span
whose five-year rolling window produces a value at all, so the endpoint answers
with exactly the 2019 and 2020 rows: the year's own mean and the mean over the
window that ends there.

The route projects one column of YearlyAvg, chosen by the feature path segment,
and it now rejects a segment outside its allow-list with 400 rather than letting
`getattr` resolve an arbitrary attribute of the model class. Both halves are
pinned here: the eight allow-listed features and their payload, and the 400 that
replaced the previous AttributeError-driven 500.
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
    assert all(set(row) == {'year', 'value', 'rolling'} for row in body['data'])
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
    assert all(set(row) == {'year', 'value', 'rolling'} for row in body['data'])


def test_unknown_feature_is_rejected_with_400(client):
    response = client.get('/api/analysis/not_a_feature')

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Unknown feature: not_a_feature'}


@pytest.mark.parametrize('feature', ['query', '__tablename__'])
def test_model_attributes_are_not_accepted_as_features(client, feature):
    '''Names that used to resolve through getattr on the model class.'''
    response = client.get(f'/api/analysis/{feature}')

    assert response.status_code == 400
    body = response.get_json()
    assert 'error' in body
    assert feature in body['error']
