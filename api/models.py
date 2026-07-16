from api import db, ma


class Tracks(db.Model):
    """ORM model for a single Billboard Hot 100 chart entry (one song-week).

    Each row represents one song at one chart week together with the Spotify
    audio feature values for that track. This table backs the
    ``/api/track/<spotify_id>``, ``/api/week/<week>`` and
    ``/api/artist/<artist>`` endpoints. (Source: api/models.py:L4-L87)

    Attributes:
        id (Integer): Primary key; unique row identifier.
            (Source: api/models.py:L52)
        week (Date): The Saturday chart week this entry belongs to.
            (Source: api/models.py:L53)
        rank (Integer): The song's Hot 100 position for that chart week
            (1 = top). (Source: api/models.py:L54)
        track (String): Song title. (Source: api/models.py:L55)
        artist (String): Performing artist name. (Source: api/models.py:L56)
        spotify_id (String): Spotify track identifier used for audio feature
            lookups. (Source: api/models.py:L57)
        tempo (Float): Spotify audio feature (tempo).
            (Source: api/models.py:L58)
        energy (Float): Spotify audio feature (energy).
            (Source: api/models.py:L59)
        danceability (Float): Spotify audio feature (danceability).
            (Source: api/models.py:L60)
        valence (Float): Spotify audio feature (valence).
            (Source: api/models.py:L61)
        liveness (Float): Spotify audio feature (liveness).
            (Source: api/models.py:L62)
        speechiness (Float): Spotify audio feature (speechiness).
            (Source: api/models.py:L63)
        acousticness (Float): Spotify audio feature (acousticness).
            (Source: api/models.py:L64)
        instrumentalness (Float): Spotify audio feature (instrumentalness).
            (Source: api/models.py:L65)
        loudness (Float): Spotify audio feature (loudness).
            (Source: api/models.py:L66)

    Note:
        Known, deliberately-unchanged behavior: ``Tracks.__init__`` does NOT
        accept a ``spotify_id`` parameter even though ``spotify_id`` is a
        declared column (Source: api/models.py:L57, L71-L87). Instances built
        via this constructor will therefore not have ``spotify_id`` populated
        by the constructor; the value can still be set afterwards via
        attribute assignment or when SQLAlchemy loads an existing row. This
        quirk is documented for awareness and intentionally left as-is (the
        constructor signature is not changed).
    """
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.Date)
    rank = db.Column(db.Integer)
    track = db.Column(db.String)
    artist = db.Column(db.String)
    spotify_id = db.Column(db.String)
    tempo = db.Column(db.Float)
    energy = db.Column(db.Float)
    danceability = db.Column(db.Float)
    valence = db.Column(db.Float)
    liveness = db.Column(db.Float)
    speechiness = db.Column(db.Float)
    acousticness = db.Column(db.Float)
    instrumentalness = db.Column(db.Float)
    loudness = db.Column(db.Float)

    # NOTE: __init__ deliberately omits the ``spotify_id`` parameter even
    # though spotify_id is a declared column above; documented, not fixed
    # (see the class Note above; Source: api/models.py:L57, L71-L87).
    def __init__(self, id, week, rank, track, artist, tempo, energy,
                 danceability, valence, liveness, speechiness, acousticness,
                 instrumentalness, loudness):
        self.id = id
        self.week = week
        self.rank = rank
        self.track = track
        self.artist = artist
        self.tempo = tempo
        self.energy = energy
        self.danceability = danceability
        self.valence = valence
        self.liveness = liveness
        self.speechiness = speechiness
        self.acousticness = acousticness
        self.instrumentalness = instrumentalness
        self.loudness = loudness


class TrackSchema(ma.Schema):
    """Marshmallow schema serializing a Tracks record to JSON.

    Declares all 15 fields of :class:`Tracks` via ``Meta.fields``. In
    ``Meta.fields`` declaration order the fields are ``id``, ``week``,
    ``rank``, ``track``, ``artist``, ``spotify_id``, ``energy``,
    ``danceability``, ``valence``, ``liveness``, ``speechiness``,
    ``acousticness``, ``instrumentalness``, ``loudness``, ``tempo``.
    Serialized JSON key order is not guaranteed to match this declaration
    order: ``Meta.ordered`` is not set (so marshmallow ``dump()`` key order is
    unstable across processes) and Flask's ``jsonify`` sorts keys
    alphabetically by default (``JSON_SORT_KEYS=True``); clients therefore
    access fields by name, not by position.
    (Source: api/models.py:L112-L116)

    Note:
        This schema INCLUDES ``spotify_id`` in its serialized output, in
        contrast with ``Tracks.__init__``, which does not set it
        (Source: api/models.py:L57, L71-L87). The serialized JSON therefore
        exposes ``spotify_id`` even though the constructor never populates it
        (it is populated by ORM loading or later assignment).
    """
    class Meta:
        fields = ('id', 'week', 'rank', 'track', 'artist', 'spotify_id',
                  'energy', 'danceability', 'valence', 'liveness',
                  'speechiness', 'acousticness', 'instrumentalness',
                  'loudness', 'tempo')


class YearlyAvg(db.Model):
    """ORM model for per-year average audio-feature values.

    Each row holds the mean of every tracked Spotify audio feature across a
    given year. This table backs the ``/api/analysis/<feature>`` endpoint's
    yearly series and its rolling average computation.
    (Source: api/models.py:L119-L158)

    Attributes:
        index (Integer): Primary key; unique row identifier.
            (Source: api/models.py:L149)
        year (String): The calendar year the averages describe.
            (Source: api/models.py:L150)
        energy (Float): Per-year mean of the energy audio feature.
            (Source: api/models.py:L151)
        danceability (Float): Per-year mean of the danceability audio
            feature. (Source: api/models.py:L152)
        valence (Float): Per-year mean of the valence audio feature.
            (Source: api/models.py:L153)
        liveness (Float): Per-year mean of the liveness audio feature.
            (Source: api/models.py:L154)
        speechiness (Float): Per-year mean of the speechiness audio feature.
            (Source: api/models.py:L155)
        acousticness (Float): Per-year mean of the acousticness audio
            feature. (Source: api/models.py:L156)
        instrumentalness (Float): Per-year mean of the instrumentalness
            audio feature. (Source: api/models.py:L157)
        tempo (Float): Per-year mean of the tempo audio feature.
            (Source: api/models.py:L158)
    """
    index = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String)
    energy = db.Column(db.Float)
    danceability = db.Column(db.Float)
    valence = db.Column(db.Float)
    liveness = db.Column(db.Float)
    speechiness = db.Column(db.Float)
    acousticness = db.Column(db.Float)
    instrumentalness = db.Column(db.Float)
    tempo = db.Column(db.Float)


class YearlyAvgSchema(ma.Schema):
    """Marshmallow schema serializing a YearlyAvg record to JSON.

    Declares 9 fields via ``Meta.fields``. In ``Meta.fields`` declaration
    order the fields are ``year``, ``energy``, ``valence``, ``liveness``,
    ``speechiness``, ``acousticness``, ``danceability``, ``instrumentalness``,
    ``tempo``. Serialized JSON key order is not guaranteed to match this
    declaration order: ``Meta.ordered`` is not set (so marshmallow ``dump()``
    key order is unstable across processes) and Flask's ``jsonify`` sorts keys
    alphabetically by default (``JSON_SORT_KEYS=True``); clients therefore
    access fields by name, not by position.
    (Source: api/models.py:L179-L181)

    Note:
        This schema EXCLUDES the ``index`` primary key from its serialized
        output; only the ``year`` label and the eight audio-feature averages
        are exposed. (Source: api/models.py:L149, L179-L181)
    """
    class Meta:
        fields = ('year', 'energy', 'valence', 'liveness', 'speechiness', \
            'acousticness', 'danceability', 'instrumentalness', 'tempo')
