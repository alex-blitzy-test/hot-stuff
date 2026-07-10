from api import db, ma


class Tracks(db.Model):
    """ORM model for a single Billboard Hot 100 chart entry (one song-week).

    Each row records one song's placement on the Billboard Hot 100 for a
    single chart week, together with that track's Spotify audio-feature
    values. Rows are populated by an external, out-of-repository weekly
    scraper and Spotipy enrichment pipeline (Source: README.md), not by this
    application.

    Attributes:
        id (int): Integer primary key; unique row identifier.
            (Source: api/models.py:L5)
        week (date): The Saturday chart week this entry belongs to.
            (Source: api/models.py:L6)
        rank (int): The song's Hot 100 position for that chart week
            (1 = top). (Source: api/models.py:L7)
        track (str): Song title. (Source: api/models.py:L8)
        artist (str): Performing artist name. (Source: api/models.py:L9)
        spotify_id (str): Spotify track identifier used for audio-feature
            lookups. (Source: api/models.py:L10)
        tempo (float): Audio feature - estimated tempo in BPM.
            (Source: api/models.py:L11)
        energy (float): Audio feature - perceptual energy/intensity.
            (Source: api/models.py:L12)
        danceability (float): Audio feature - danceability measure.
            (Source: api/models.py:L13)
        valence (float): Audio feature - musical positiveness.
            (Source: api/models.py:L14)
        liveness (float): Audio feature - live-audience presence.
            (Source: api/models.py:L15)
        speechiness (float): Audio feature - spoken-word presence.
            (Source: api/models.py:L16)
        acousticness (float): Audio feature - acoustic confidence.
            (Source: api/models.py:L17)
        instrumentalness (float): Audio feature - vocal-absence likelihood.
            (Source: api/models.py:L18)
        loudness (float): Audio feature - overall loudness in decibels (dB).
            (Source: api/models.py:L19)

    Note:
        Known, deliberately-unchanged behavior: ``Tracks.__init__``
        (Source: api/models.py:L21-L37) does NOT accept a ``spotify_id``
        parameter even though ``spotify_id`` is a declared column
        (Source: api/models.py:L10). Instances created via this constructor
        will therefore not have ``spotify_id`` set by the constructor; the
        value can still be assigned directly or populated when the ORM loads
        a row. Documented for awareness and left unchanged per the
        documentation-only scope (AAP 0.8.2).
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

    # NOTE (documented, intentionally unchanged - AAP 0.8.2): this constructor
    # does NOT accept a ``spotify_id`` argument even though ``spotify_id`` is a
    # declared column above. See the class docstring; populate ``spotify_id``
    # via attribute assignment or ORM loading, not through ``__init__``.
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

    Serializes all 15 fields of a :class:`Tracks` row, in the exact order
    declared in ``Meta.fields`` (Source: api/models.py:L42-L45):
    ``id``, ``week``, ``rank``, ``track``, ``artist``, ``spotify_id``,
    ``energy``, ``danceability``, ``valence``, ``liveness``, ``speechiness``,
    ``acousticness``, ``instrumentalness``, ``loudness``, ``tempo``.

    Note:
        This schema INCLUDES ``spotify_id`` in its serialized output, in
        contrast with ``Tracks.__init__``, which does not accept or populate
        it (Source: api/models.py:L21-L37). A ``spotify_id`` assigned
        directly or loaded by the ORM is therefore still exposed by this
        schema's JSON output.
    """
    class Meta:
        fields = ('id', 'week', 'rank', 'track', 'artist', 'spotify_id',
                  'energy', 'danceability', 'valence', 'liveness',
                  'speechiness', 'acousticness', 'instrumentalness',
                  'loudness', 'tempo')


class YearlyAvg(db.Model):
    """ORM model for per-year average audio-feature values.

    Holds one aggregated row per year containing the mean of each Spotify
    audio feature across that year's charting tracks. This table backs the
    ``/api/analysis/<feature>`` endpoint's yearly series and its rolling
    average computation (Source: api/routes.py, api/funcs.py).

    Attributes:
        index (int): Integer primary key; unique row identifier.
            (Source: api/models.py:L49)
        year (str): The calendar year the averages apply to.
            (Source: api/models.py:L50)
        energy (float): Audio feature - mean energy for the year.
            (Source: api/models.py:L51)
        danceability (float): Audio feature - mean danceability for the year.
            (Source: api/models.py:L52)
        valence (float): Audio feature - mean valence for the year.
            (Source: api/models.py:L53)
        liveness (float): Audio feature - mean liveness for the year.
            (Source: api/models.py:L54)
        speechiness (float): Audio feature - mean speechiness for the year.
            (Source: api/models.py:L55)
        acousticness (float): Audio feature - mean acousticness for the year.
            (Source: api/models.py:L56)
        instrumentalness (float): Audio feature - mean instrumentalness.
            (Source: api/models.py:L57)
        tempo (float): Audio feature - mean tempo for the year.
            (Source: api/models.py:L58)
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

    Serializes 9 fields, in the exact order declared in ``Meta.fields``
    (Source: api/models.py:L63-L64): ``year``, ``energy``, ``valence``,
    ``liveness``, ``speechiness``, ``acousticness``, ``danceability``,
    ``instrumentalness``, ``tempo``.

    Note:
        This schema EXCLUDES the ``index`` primary key
        (Source: api/models.py:L49) from its serialized JSON output.
    """
    class Meta:
        fields = ('year', 'energy', 'valence', 'liveness', 'speechiness', \
            'acousticness', 'danceability', 'instrumentalness', 'tempo')
