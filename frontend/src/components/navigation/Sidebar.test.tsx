import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import type { KeyboardEvent, MouseEvent } from 'react';
import StSidebar from './Sidebar';
import Hamburger from './Hamburger';

type TabEvent = MouseEvent<HTMLDivElement> | KeyboardEvent<HTMLDivElement>;

type SeenCall = { id: string; prevented: boolean };

// The handler reads the clicked tab's id from currentTarget while the event is
// still dispatching, so the test records it from inside the mock before React
// clears currentTarget once the dispatch has finished.
const recordCalls = () => {
  const seen: SeenCall[] = [];
  const handler = vi.fn((e: TabEvent) => {
    seen.push({ id: e.currentTarget.id, prevented: e.defaultPrevented });
  });
  return { handler, seen };
};

const TAB_NAMES = ['Tracks', 'Trends', 'Artists', 'About'];

describe('Sidebar', () => {
  it.each(TAB_NAMES.map((name, index) => ({ name, index })))(
    'exposes $name as a focusable tab, selected only when it is the active one',
    ({ name, index }) => {
      render(<StSidebar handleClick={vi.fn()} activeTab={1} nav />);

      expect(screen.getAllByRole('tab')).toHaveLength(TAB_NAMES.length);

      const tab = screen.getByRole('tab', { name });
      expect(tab.tabIndex).toBe(0);
      expect(tab).toHaveAttribute(
        'aria-selected',
        index === 1 ? 'true' : 'false'
      );
    }
  );

  it('takes the closed rail out of the accessibility tree', () => {
    render(<StSidebar handleClick={vi.fn()} activeTab={0} />);

    expect(screen.queryAllByRole('tab')).toHaveLength(0);
    expect(screen.queryAllByRole('tab', { hidden: true })).toHaveLength(
      TAB_NAMES.length
    );
  });

  it.each([{ key: 'Enter' }, { key: ' ' }])(
    'activates the Trends tab with the $key key through the same handler as a click',
    ({ key }) => {
      const { handler, seen } = recordCalls();
      render(<StSidebar handleClick={handler} activeTab={0} nav />);

      fireEvent.keyDown(screen.getByRole('tab', { name: 'Trends' }), { key });

      expect(handler).toHaveBeenCalledTimes(1);
      expect(seen).toEqual([{ id: '1', prevented: true }]);
    }
  );

  it('still routes a mouse click on a tab through the same handler', () => {
    const { handler, seen } = recordCalls();
    render(<StSidebar handleClick={handler} activeTab={0} nav />);

    fireEvent.click(screen.getByRole('tab', { name: 'Artists' }));

    expect(handler).toHaveBeenCalledTimes(1);
    expect(seen).toEqual([{ id: '2', prevented: false }]);
  });
});

describe('Hamburger', () => {
  it('is exposed as a focusable button with an accessible name', () => {
    render(<Hamburger showNav={vi.fn()} />);

    const button = screen.getByRole('button', {
      name: 'Toggle navigation menu',
    });
    expect(button.tabIndex).toBe(0);
  });

  it.each([
    { activation: 'Enter key', key: 'Enter' },
    { activation: 'Space key', key: ' ' },
    { activation: 'click', key: null },
  ])('opens the navigation menu with a $activation', ({ key }) => {
    const showNav = vi.fn();
    render(<Hamburger showNav={showNav} />);

    const button = screen.getByRole('button', {
      name: 'Toggle navigation menu',
    });
    if (key === null) {
      fireEvent.click(button);
    } else {
      fireEvent.keyDown(button, { key });
    }

    expect(showNav).toHaveBeenCalledTimes(1);
  });
});
