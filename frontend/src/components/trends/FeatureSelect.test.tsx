import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FeatureSelect from './FeatureSelect';

describe('FeatureSelect', () => {
  it('submits the selected feature to submitFunc exactly once', async () => {
    const user = userEvent.setup();
    const submitFunc = vi.fn();
    render(<FeatureSelect submitFunc={submitFunc} />);

    // A value that is not the first option, so the submitted argument can only
    // come from the user's selection rather than from a default.
    await user.selectOptions(screen.getByRole('combobox'), 'energy');
    await user.click(screen.getByRole('button', { name: 'Go' }));

    expect(submitFunc).toHaveBeenCalledTimes(1);
    expect(submitFunc).toHaveBeenCalledWith('energy');
  });

  it('does not submit while no feature has been selected', async () => {
    const user = userEvent.setup();
    const submitFunc = vi.fn();
    render(<FeatureSelect submitFunc={submitFunc} />);

    await user.click(screen.getByRole('button', { name: 'Go' }));

    expect(submitFunc).not.toHaveBeenCalled();
  });
});
