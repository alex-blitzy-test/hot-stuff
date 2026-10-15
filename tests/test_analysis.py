'''Tests for the GET /api/analysis/<feature> endpoint.

The seeded yearly averages cover six consecutive chart years, the shortest span
whose five-year rolling window produces a value at all, so the endpoint answers
with exactly the 2019 and 2020 rows: the year's own mean and the mean over the
window that ends there.

The route projects one column of YearlyAvg, chosen by the feature path
segment, and answers 400 for a segment outside its allow-list; both halves
are pinned here: the eight allow-listed features and their payload, and the
refusal.

The order those rows arrive in is a third premise, and it now comes from the
query rather than from storage: the route projects them through a
`with_entities` call ordered by `year`, so the rows reach `get_rolling_avg` in
year order and the five-year window follows the year sequence instead of the
order the rows physically occupy. `get_rolling_avg` rolls the rows in the order
it receives them and drops the positions that carry no window value, so which
years the endpoint answers is a function of the years themselves: the fifth
year of the series is the first to carry a rolling value, so a row appended
with an earlier year than the fixture's - and physically last in the table -
opens the window rather than closing it, staying out of the payload while the
years that follow it keep the rolling values that belong to them. The
assertions below are therefore a year-order premise as well as a rolling-window
one: they follow the `year` labels the fixture declares, and no longer the
`index` values it assigns them.
'''

import pytest

from api import db
from api.models import YearlyAvg

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

# A seventh row, chronologically first and appended last: its year position
# opens the series while the physical position it is given closes it, and the
# two disagree by construction.
EARLIER_ROW = {
    'index': 9005, 'year': '2014', 'energy': 0.05, 'danceability': 0.2,
    'valence': 0.3, 'liveness': 0.4, 'speechiness': 0.5,
    'acousticness': 0.6, 'instrumentalness': 0.05, 'tempo': 90.0,
}

# The series the year ordering answers once that row is in the table: 2018 is
# the fifth year, so it is the first to carry a rolling value, taken over
# 2014's mean and the four seeded years that follow it, and 2014 itself is
# absent because the window leaves the position it holds unvalued.
EARLIER_YEARS = ['2018', '2019', '2020']

EARLIER_POINTS = [(0.4, 0.21), (0.5, 0.3), (0.6, 0.4)]


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


def test_a_row_out_of_year_position_is_answered_in_year_order(app, client):
    '''A row whose physical position is not its year position leaves the years
    the window covers to the years themselves.'''
    db.session.add(YearlyAvg(**EARLIER_ROW))
    db.session.commit()
    # the premise of the case: unordered, the projection returns the appended
    # row last, so its row position and its year position genuinely disagree
    physicalYears = [row[0] for row in YearlyAvg.query.with_entities(
        YearlyAvg.year)]
    assert physicalYears[-1] == EARLIER_ROW['year']

    response = client.get('/api/analysis/energy')

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {'feature', 'data'}
    assert [row['year'] for row in body['data']] == EARLIER_YEARS
    values, rollings = zip(*EARLIER_POINTS)
    assert [row['value'] for row in body['data']] == pytest.approx(values)
    assert [row['rolling'] for row in body['data']] == pytest.approx(rollings)
