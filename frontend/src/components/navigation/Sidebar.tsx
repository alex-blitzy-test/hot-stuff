import type { KeyboardEvent, MouseEvent } from 'react';
import styled from 'styled-components';
import Tab from './Tab';
import SmallTab from './SmallTab';

type SidebarProps = {
  handleClick: (
    e: MouseEvent<HTMLDivElement> | KeyboardEvent<HTMLDivElement>
  ) => void;
  activeTab: number;
  nav?: boolean;
  openNav?: () => void;
  className?: string;
};

const Sidebar = (props: SidebarProps) => {
  const { handleClick, activeTab, className } = props;

  // A keyboard activation of a tab goes through the same handler the mouse
  // uses, so both devices take the identical path into the tab state.
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick(e);
    }
  };

  return (
    <div className={className}>
      <div className='titleContainer sidebarHeader'>
        <div className='titleContent'>Hot Stuff</div>
      </div>
      <div className='tabContainer'>
        <div role='tablist' aria-label='Charts'>
          <Tab
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            role='tab'
            tabIndex={0}
            aria-selected={activeTab === 0}
            activeTab={activeTab === 0}
            id='0'
          >
            Tracks
          </Tab>
          <Tab
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            role='tab'
            tabIndex={0}
            aria-selected={activeTab === 1}
            activeTab={activeTab === 1}
            id='1'
          >
            Trends
          </Tab>
          <Tab
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            role='tab'
            tabIndex={0}
            aria-selected={activeTab === 2}
            activeTab={activeTab === 2}
            id='2'
          >
            Artists
          </Tab>
        </div>
        <div className='lowerTabs' role='tablist' aria-label='Application'>
          <SmallTab
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            role='tab'
            tabIndex={0}
            aria-selected={activeTab === 3}
            activeTab={activeTab === 3}
            id='3'
          >
            About
          </SmallTab>
        </div>
      </div>
    </div>
  );
};

const StSidebar = styled(Sidebar)<{ nav?: boolean }>`
  position: fixed;
  height: calc(100vh - 25px);
  width: 35vw;
  left: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--dark-2);
  z-index: 2;
  transition: opacity 0.5s;

  /* The closed rail is hidden by opacity alone, which leaves it interactable:
     its fixed 35vw by full-height box stays the topmost target over the panel's
     own controls, and its focusable tabs would still be reachable by Tab while
     invisible. Pointer input therefore follows the same nav signal the opacity
     does, and visibility takes the closed rail out of the tab order; the
     breakpoint below, where the rail is permanently visible, restores both. */
  ${(props) =>
    props.nav
      ? 'opacity: 1; visibility: visible;'
      : 'opacity: 0; pointer-events: none; visibility: hidden; transition: opacity 0.5s, visibility 0s linear 0.5s;'};

  @media only screen and (min-width: 800px) {
    opacity: 1;
    pointer-events: auto;
    visibility: visible;
    width: 15vw;
  }
`;

export default StSidebar;
