import { useState, useEffect } from 'react';
import type { AnalysisResponse } from '../../types/api';
import type { FeatureDescription } from '../../types/features';
import { getAnalysis, ApiError } from '../../api/client';
import FeatureSelect from './FeatureSelect';
import Line from './LineChart';
import Hamburger from '../navigation/Hamburger';
import featuresJson from './features.json';

const features: FeatureDescription[] = featuresJson;

interface TrendsSectionProps {
  showNav: () => void;
}

const TrendsSection = (props: TrendsSectionProps) => {
  const { showNav } = props;
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getData = async (input: string) => {
    setIsLoaded(false);
    setError(null);

    try {
      const result = await getAnalysis(input);
      setData(result);
      setIsLoaded(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        setIsLoaded(true);
      } else {
        /* A request that carried no response (an unreachable backend) is
           rethrown unwrapped rather than shown as a banner: this panel keeps
           the loading marker and lets the rejection reach the console, which
           is what it has always done. */
        throw err;
      }
    }
  };

  useEffect(() => {
    getData('tempo');
  }, []);

  return (
    <div className='section'>
      <div className='topBar'>
        <FeatureSelect submitFunc={getData} initValue='tempo' />
        <Hamburger showNav={showNav} />
      </div>
      {error && <h1 className='error'>{error}</h1>}
      {!isLoaded && <h1 className='loading'>. . .</h1>}
      <div>
        <Line data={data?.data} />
      </div>
      <div className='audioFeatures scroll'>
        <h4>
          Audio Features (
          <a
            target='_blank'
            rel='noopener noreferrer'
            href='https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject'
          >
            Source
          </a>
          )
        </h4>
        <div>
          {features.map((feature, i) => {
            return (
              <p key={i} className='featureDescription'>
                <b>{feature.title}: </b>
                {feature.desctiption}
              </p>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TrendsSection;
