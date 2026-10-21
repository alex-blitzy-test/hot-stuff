import type { KeyboardEvent } from 'react';
import styled from 'styled-components';

type HamburgerProps = {
  showNav: () => void;
};

const Hamburger = (props: HamburgerProps) => {
  const { showNav } = props;

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      showNav();
    }
  };

  return (
    <StHamburger
      onClick={showNav}
      onKeyDown={handleKeyDown}
      role='button'
      tabIndex={0}
      aria-label='Toggle navigation menu'
    >
      <svg viewBox='0 0 100 80' width='40' height='40' className='hamburger'>
        <rect x='15' y='15' rx='5' width='75' height='10'></rect>
        <rect x='15' y='35' rx='5' width='75' height='10'></rect>
        <rect x='15' y='55' rx='5' width='75' height='10'></rect>
      </svg>
    </StHamburger>
  );
};

const StHamburger = styled.div`
  :focus-visible {
    outline: 2px solid var(--purp);
    outline-offset: 2px;
  }

  /* Above the breakpoint the icon is hidden, so the wrapper paints nothing and
     must not stay in the tab order as an invisible focus stop. */
  @media only screen and (min-width: 800px) {
    display: none;
  }
`;

export default Hamburger;
