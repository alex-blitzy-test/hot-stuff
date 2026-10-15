import { useState } from 'react';

interface FeatureSelectProps {
  submitFunc: (value: string) => void;
  /* Declared but unread: the parent's call site passes initValue, and the panel's
     initial feature is the parent's to choose, so the prop stays in the call
     surface without seeding the selection. */
  initValue?: string;
}

const FeatureSelect = (props: FeatureSelectProps) => {
  const { submitFunc } = props;
  const [inputValue, setInputValue] = useState<string>();
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setInputValue(value);
  };
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (inputValue) {
      submitFunc(inputValue);
    }
  };
  return (
    <form onSubmit={handleSubmit}>
      <select name='feature' className='inputField' onChange={handleChange}>
        <option value='tempo'>Tempo</option>
        <option value='energy'>Energy</option>
        <option value='danceability'>Danceability</option>
        <option value='instrumentalness'>Instrumentalness</option>
        <option value='liveness'>Liveness</option>
        <option value='speechiness'>Speechiness</option>
        <option value='acousticness'>Acousticness</option>
      </select>
      <input className='inputBtn' type='submit' value='Go' />
    </form>
  );
};

export default FeatureSelect;
