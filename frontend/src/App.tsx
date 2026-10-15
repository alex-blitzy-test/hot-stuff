import { useState } from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';
import TracksSection from './components/tracks/TracksSection';
import TrendsSection from './components/trends/TrendsSection';
import ArtistsSection from './components/artists/ArtistsSection';
import AboutSection from './components/about/AboutSection';
import Section from './components/navigation/Section';
import StSidebar from './components/navigation/Sidebar';
// import Sidebar from './components/navigation/Sidebar1';

function App() {
  const [nav, setNav] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const showNav = () => {
    setNav(!nav);
  };
  const handleClick = (
    e: MouseEvent<HTMLDivElement> | KeyboardEvent<HTMLDivElement>
  ) => {
    const index = parseInt(e.currentTarget.id, 0);
    if (index !== activeTab) {
      setActiveTab(index);
      setNav(false);
    }
  };
  return (
    <div className='app'>
      {/* sidebar */}
      <StSidebar
        handleClick={handleClick}
        activeTab={activeTab}
        openNav={showNav}
        nav={nav}
      />

      <div className='titleContainer mobileHeader'>
        <div className='titleContent'>Hot Stuff</div>
      </div>

      {/* content */}
      <div>
        <Section activeTab={activeTab === 0}>
          <TracksSection showNav={showNav} />
        </Section>
        <Section activeTab={activeTab === 1}>
          <TrendsSection showNav={showNav} />
        </Section>
        <Section activeTab={activeTab === 2}>
          <ArtistsSection showNav={showNav} />
        </Section>
        <Section activeTab={activeTab === 3}>
          <AboutSection showNav={showNav} />
        </Section>
      </div>

      {/* footer */}
      <div className='footer'>
        <span className='footerContainer'>
          {/* <a
            href='https://github.com/augardiner/hot-100'
            target='_blank'
            rel='noopener noreferrer'
            className='sourceLink'
          >
            Source Code
          </a> */}
          <p>AUG | 2021</p>
        </span>
      </div>
    </div>
  );
}

export default App;
