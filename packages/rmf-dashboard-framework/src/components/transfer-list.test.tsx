import { fireEvent, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TransferList } from './transfer-list';

describe('TransferList', () => {
  let left: string[];
  let right: string[];

  beforeEach(() => {
    left = ['one', 'two'];
    right = ['three', 'four'];
  });

  it('renders left and right items', () => {
    const root = render(<TransferList leftItems={left} rightItems={right} />);
    left.forEach((i) => root.getByText(i));
    right.forEach((i) => root.getByText(i));
  });

  it('renders left and right titles', () => {
    const root = render(
      <TransferList leftItems={left} rightItems={right} leftTitle="left" rightTitle="right" />,
    );
    root.getByText('left');
    root.getByText('right');
  });

  it('transfers correct items', () => {
    const spy = vi.fn();
    const root = render(<TransferList leftItems={left} rightItems={right} onTransfer={spy} />);
    fireEvent.click(root.getByText('one'));
    fireEvent.click(root.getByLabelText('move selected right', { selector: 'button' }));
    expect(spy).toHaveBeenCalled();
    const newLeft: string[] = spy.mock.lastCall![0];
    const newRight: string[] = spy.mock.lastCall![1];
    expect(newLeft).toHaveLength(1);
    expect(newLeft).not.toContain('one');
    expect(newRight).toHaveLength(3);
    expect(newRight).toContain('one');
  });
});
