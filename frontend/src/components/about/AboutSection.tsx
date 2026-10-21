import Hamburger from '../navigation/Hamburger';

type AboutSectionProps = {
  showNav: () => void;
};

const AboutSection = (props: AboutSectionProps) => {
  const { showNav } = props;
  return (
    <div className='section'>
      <div className='topBar aboutHeader'>
        <Hamburger showNav={showNav} />
      </div>
      <div className='aboutContent scroll'>
        <h2>The Billboard Hot 100</h2>
        <div className='aboutSection'>
          <p>
            The{' '}
            <a
              href='https://www.billboard.com/charts/hot-100'
              target='_blank'
              rel='noopener noreferrer'
            >
              Billboard Hot 100
            </a>{' '}
            is the music industry standard record chart in the United States for
            songs, published weekly by Billboard magazine. Chart rankings are
            based on sales (physical and digital), radio play, and online
            streaming in the United States.
          </p>
          <p>
            The first number one song of the Billboard Hot 100 was "Poor Little
            Fool" by Ricky Nelson, on August 4, 1958.{' '}
            <a
              href='https://en.wikipedia.org/wiki/Billboard_Hot_100'
              target='_blank'
              rel='noopener noreferrer'
            >
              Source
            </a>
          </p>
        </div>
        <div className='aboutSection'>
          <h2>API</h2>
          <p>The API is written in Python with the Flask framework.</p>
          <p>
            <b>Tracks: </b>There is a separate script, running weekly, which
            scrapes the Billboard site page and adds each song into the
            database.
          </p>
          <p>
            <b>Data: </b>The weekly script uses the{' '}
            <a
              href='https://spotipy.readthedocs.io/en/2.18.0/'
              target='_blank'
              rel='noopener noreferrer'
            >
              Spotipy
            </a>{' '}
            library to get{' '}
            <a
              href='https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject'
              target='_blank'
              rel='noopener noreferrer'
            >
              Spotify Audio Features
            </a>{' '}
            for each track, used for visualizations.
          </p>
          <p>
            <b>Endpoints:</b>
          </p>
          <ul>
            <li>
              /api/week/{'<week>'} : get songs ranked 0-100 for {'<week>'} in
              YYYY-MM-DD format
            </li>
            <li>
              /api/artist/{'<artist>'} : get all appeareances where the artist
              column contains {'<artist>'}
            </li>
            <li>
              /api/track/{'<spotify_id>'} : get all appeareances of track where
              the spotify_id column equals {'<spotify_id>'}
            </li>
            <li>
              /api/analysis/{'<feature>'} : get the annual average and 3 year
              rolling average for {'<feature>'}
            </li>
          </ul>
        </div>
        <div className='aboutSection'>
          <h2>Front End</h2>
          <p>The front end is written in Javascript with the React library.</p>
          <p>
            <b>Visualizations: </b>Visualizations are created using the{' '}
            <a
              href='https://www.amcharts.com/'
              target='_blank'
              rel='noopener noreferrer'
            >
              amCharts
            </a>{' '}
            library.
          </p>
        </div>
        <h3 className='sourceLink'>
          <a
            href='https://github.com/augardiner/hot-100'
            target='_blank'
            rel='noopener noreferrer'
          >
            Source Code
          </a>
        </h3>
      </div>
    </div>
  );
};

export default AboutSection;
