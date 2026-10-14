import { useState, useEffect } from 'react';
import DatePicker from './DatePicker';
import Radar from './RadarChart';
import Hamburger from '../navigation/Hamburger';
import { getWeek, ApiError } from '../../api/client';
import { WeekResponse } from '../../types/api';

type TracksSectionProps = { showNav: () => void };

const TracksSection = (props: TracksSectionProps) => {
  const { showNav } = props;
  const [data, setData] = useState<WeekResponse | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getData = async (input: string) => {
    setIsLoaded(false);
    setError(null);

    try {
      const response = await getWeek(input);
      setData(response);
      setIsLoaded(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setIsLoaded(true);
        setError(err.message);
        return;
      }
      // A failure that carried no HTTP response (an unreachable backend) is rethrown rather than
      // shown: this panel has always stayed on the loading marker and left the rejection for the
      // console in that case, so no banner is raised and no error text is invented here.
      throw err;
    }
  };

  useEffect(() => {
    // getData(new Date().toISOString().slice(0, 10));
    getData('2021-11-13');
  }, []);

  return (
    <div className='section'>
      <div className='topBar'>
        <DatePicker
          submitFunc={getData}
          // initValue={new Date().toISOString().slice(0, 10)}
          initValue='2021-11-13'
        />
        <Hamburger showNav={showNav} />
      </div>
      <div>
        <Radar data={data?.averages} />
      </div>
      <div className='scroll'>
        {error && <h1 className='error'>{error}</h1>}
        {!isLoaded && <h1 className='loading'>. . .</h1>}
        {isLoaded &&
          !error &&
          data?.songs.map((item, i) => {
            return (
              <div className='trackRow' key={i}>
                <h1 className='rowEl rank'>{item.rank}</h1>
                <span className='trackData'>
                  <h4 className='rowEl artist'>{item.artist}</h4>
                  <h5 className='rowEl track'>{item.track}</h5>
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
};

export default TracksSection;
