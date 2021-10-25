import { Breakpoint } from '@material-ui/core/styles/createBreakpoints';
import React from 'react';
import { WindowLayout, WindowManagerProps, WindowProps } from 'react-components';
import * as RmfModels from 'rmf-models';
import { BehaviorSubject, Observable } from 'rxjs';
import { v4 as uuidv4 } from 'uuid';

export type ManagedWindowProps = Omit<WindowProps, 'title' | 'children'>;
export type ManagedWindow = React.ComponentType<ManagedWindowProps>;

declare namespace WindowClass {
  type BaseLayout = Omit<WindowLayout, 'i'>;
  type ResponsiveBaseLayouts = {
    [k in keyof Required<WindowManagerProps>['layouts']]: WindowClass.BaseLayout;
  };
}

export class WindowClass {
  name: string;
  Component: ManagedWindow;
  baseLayout: WindowClass.BaseLayout;
  responsiveBaseLayouts: WindowClass.ResponsiveBaseLayouts;

  constructor(
    name: string,
    Component: ManagedWindow,
    baseLayout: WindowClass.BaseLayout,
    responsiveBaseLayouts: WindowClass.ResponsiveBaseLayouts = {},
  ) {
    this.name = name;
    this.Component = Component;
    this.baseLayout = baseLayout;
    this.responsiveBaseLayouts = responsiveBaseLayouts;
  }

  createLayout(breakpoint: Breakpoint, layout?: Partial<WindowLayout>): WindowLayout {
    const base = this.responsiveBaseLayouts[breakpoint] || this.baseLayout;
    return {
      i: uuidv4(),
      ...base,
      ...layout,
    };
  }
}

export function getWindowSettings<SettingsType>(windowKey: string): SettingsType | undefined {
  return (window.localStorage.getItem(`window.${windowKey}`) as unknown) as SettingsType;
}

export function saveWindowSettings(windowKey: string, settings: unknown): void {
  window.localStorage.setItem(`window.${windowKey}`, JSON.stringify(settings));
}

export class WindowBus {
  taskSelected: Observable<RmfModels.TaskSummary | null>;

  constructor() {
    this.taskSelected = new BehaviorSubject(null);
  }
}

export const WindowBusContext = React.createContext(new WindowBus());

export const allWindows: Record<string, WindowClass> = {};
