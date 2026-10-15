import { useState } from 'react';

type DatePickerProps = {
  initValue: string;
  submitFunc: (value: string) => void;
};

const DatePicker = (props: DatePickerProps) => {
  const { initValue, submitFunc } = props;
  const [inputValue, setInputValue] = useState(initValue);
  // const today = new Date().toISOString().slice(0, 10);
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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
      <input
        className='inputField'
        type='date'
        value={inputValue}
        onChange={handleChange}
        min='1958-07-27'
        max='2021-11-13'
      />
      <input className='inputBtn' type='submit' value='Go' />
    </form>
  );
};

export default DatePicker;
