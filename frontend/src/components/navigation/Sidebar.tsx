import type { MouseEvent } from 'react';
import styled from 'styled-components';
import Tab from './Tab';
import SmallTab from './SmallTab';

type SidebarProps = {
  handleClick: (e: MouseEvent<HTMLDivElement>) => void;
  activeTab: number;
  nav?: boolean;
  openNav?: () => void;
  className?: string;
};

const Sidebar = (props: SidebarProps) => {
  const { handleClick, activeTab, className } = props;
  return (
    <div className={className}>
      <div className='titleContainer sidebarHeader'>
        <div className='titleContent'>Hot Stuff</div>
      </div>
      <div className='tabContainer'>
        <div>
          <Tab onClick={handleClick} activeTab={activeTab === 0} id='0'>
            Tracks
          </Tab>
          <Tab onClick={handleClick} activeTab={activeTab === 1} id='1'>
            Trends
          </Tab>
          <Tab onClick={handleClick} activeTab={activeTab === 2} id='2'>
            Artists
          </Tab>
        </div>
        <div className='lowerTabs'>
          <SmallTab onClick={handleClick} activeTab={activeTab === 3} id='3'>
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

  /* The closed rail is hidden by opacity alone, which does not take it out of
     hit testing: at z-index 2 its fixed 35vw by full-height box stays the
     topmost target over the panel's own controls. Pointer input therefore
     follows the same nav signal the opacity does, and the breakpoint below,
     where the rail is permanently visible, restores it. */
  ${(props) => (props.nav ? 'opacity: 1;' : 'opacity: 0; pointer-events: none;')};

  @media only screen and (min-width: 800px) {
    opacity: 1;
    pointer-events: auto;
    width: 15vw;
  }
`;

export default StSidebar;
