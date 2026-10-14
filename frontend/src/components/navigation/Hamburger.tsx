type HamburgerProps = {
  showNav: () => void;
};

const Hamburger = (props: HamburgerProps) => {
  const { showNav } = props;
  return (
    <div onClick={showNav}>
      <svg viewBox='0 0 100 80' width='40' height='40' className='hamburger'>
        <rect x='15' y='15' rx='5' width='75' height='10'></rect>
        <rect x='15' y='35' rx='5' width='75' height='10'></rect>
        <rect x='15' y='55' rx='5' width='75' height='10'></rect>
      </svg>
    </div>
  );
};

export default Hamburger;
