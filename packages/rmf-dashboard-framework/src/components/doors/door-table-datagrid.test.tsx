import { render } from '@testing-library/react';
import { waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Door as RmfDoor } from 'rmf-models/ros/rmf_building_map_msgs/msg';
import { DoorMode as RmfDoorMode } from 'rmf-models/ros/rmf_door_msgs/msg';
import { describe, expect, it, vi } from 'vitest';

import { DoorDataGridTable, DoorTableData } from './door-table-datagrid';
import { makeDoorState } from './test-utils.test';

describe('DoorDataGridTable', () => {
  const mockDoors: DoorTableData[] = [
    {
      index: 1,
      doorName: 'L3_door2',
      levelName: 'L3',
      doorType: RmfDoor.DOOR_TYPE_SINGLE_SWING,
      doorState: makeDoorState({
        door_name: 'L3_door2',
        current_mode: { value: RmfDoorMode.MODE_MOVING },
      }),
    },
  ];

  it('renders doors data correctly', () => {
    const root = render(<DoorDataGridTable doors={mockDoors} />);
    const doorName = root.getByText('L3_door2');
    const levelName = root.getByText('L3');
    const doorType = root.getByText('Single Swing');
    const doorState = root.getByText('MOVING');

    expect(doorName).toBeTruthy();
    expect(levelName).toBeTruthy();
    expect(doorType).toBeTruthy();
    expect(doorState).toBeTruthy();
  });

  it('shows the correct number of rows', () => {
    const root = render(<DoorDataGridTable doors={mockDoors} />);
    const allRows = root.container.querySelectorAll('.MuiDataGrid-row').length;
    expect(allRows).toBe(1);
  });

  it('shows titles correctly', () => {
    const root = render(<DoorDataGridTable doors={mockDoors} />);
    expect(root.queryByText('Name')).toBeTruthy();
    expect(root.queryByText('Current Floor')).toBeTruthy();
    expect(root.queryByText('Type')).toBeTruthy();
    expect(root.queryByText('Door State')).toBeTruthy();
  });

  it('door clicks triggered', async () => {
    const onDoorClicked = vi.fn();
    const root = render(<DoorDataGridTable doors={mockDoors} onDoorClick={onDoorClicked} />);

    userEvent.click(root.getByText('Open'));
    await waitFor(() => expect(onDoorClicked).toHaveBeenCalledTimes(1));
    userEvent.click(root.getByText('Close'));
    await waitFor(() => expect(onDoorClicked).toHaveBeenCalledTimes(2));
  });
});
