import { create } from 'zustand';

export type AppId = 'copilot' | 'calendar' | 'courses' | 'voice';

export interface WindowState {
  id: string;
  appId: AppId;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
  isMaximized?: boolean;
  prevDims?: { x: number; y: number; width: number; height: number };
}

interface AppWindowConfig {
  appId: AppId;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

const APP_CONFIGS: Record<AppId, AppWindowConfig> = {
  copilot: { appId: 'copilot', title: 'TUM Copilot', x: 140, y: 70, width: 760, height: 560 },
  calendar: { appId: 'calendar', title: 'TUM Calendar', x: 190, y: 90, width: 920, height: 610 },
  courses: { appId: 'courses', title: 'TUM Courses', x: 230, y: 110, width: 980, height: 620 },
  voice: { appId: 'voice', title: 'TUM Voice', x: 320, y: 130, width: 560, height: 460 },
};

interface OsStore {
  windows: WindowState[];
  activeWindowId: string | null;
  openWindow: (appId: AppId) => void;
  closeWindow: (windowId: string) => void;
  focusWindow: (windowId: string) => void;
  moveWindow: (windowId: string, x: number, y: number) => void;
  updateWindow: (windowId: string, updates: Partial<WindowState>) => void;
  toggleMaximize: (windowId: string) => void;
}

const getTopZ = (windows: WindowState[]) => windows.reduce((top, w) => Math.max(top, w.zIndex), 0);

export const useOsStore = create<OsStore>((set, get) => ({
  windows: [],
  activeWindowId: null,
  openWindow: (appId) => {
    const state = get();
    const existing = state.windows.find((windowItem) => windowItem.appId === appId);
    const nextZ = getTopZ(state.windows) + 1;

    if (existing) {
      set({
        activeWindowId: existing.id,
        windows: state.windows.map((windowItem) =>
          windowItem.id === existing.id ? { ...windowItem, zIndex: nextZ } : windowItem
        ),
      });
      return;
    }

    const config = APP_CONFIGS[appId];
    const id = `${appId}-${Date.now()}`;
    set({
      activeWindowId: id,
      windows: [...state.windows, { ...config, id, zIndex: nextZ }],
    });
  },
  closeWindow: (windowId) => {
    const remaining = get().windows.filter((windowItem) => windowItem.id !== windowId);
    const topWindow = remaining.sort((a, b) => b.zIndex - a.zIndex)[0];
    set({
      windows: remaining,
      activeWindowId: topWindow?.id ?? null,
    });
  },
  focusWindow: (windowId) => {
    const state = get();
    const nextZ = getTopZ(state.windows) + 1;
    set({
      activeWindowId: windowId,
      windows: state.windows.map((windowItem) =>
        windowItem.id === windowId ? { ...windowItem, zIndex: nextZ } : windowItem
      ),
    });
  },
  moveWindow: (windowId, x, y) => {
    set({
      windows: get().windows.map((w) => (w.id === windowId ? { ...w, x, y, isMaximized: false } : w)),
    });
  },
  updateWindow: (windowId, updates) => {
    set({
      windows: get().windows.map((w) => (w.id === windowId ? { ...w, ...updates } : w)),
    });
  },
  toggleMaximize: (windowId) => {
    const state = get();
    const MARGIN = 12;
    const MENU_BAR_HEIGHT = 36;
    const DOCK_HEIGHT = 84;

    set({
      windows: state.windows.map((w) => {
        if (w.id !== windowId) return w;
        if (w.isMaximized) {
          return { ...w, ...w.prevDims, isMaximized: false };
        }
        return {
          ...w,
          isMaximized: true,
          prevDims: { x: w.x, y: w.y, width: w.width, height: w.height },
          x: MARGIN,
          y: MENU_BAR_HEIGHT + MARGIN,
          width: window.innerWidth - (MARGIN * 2),
          height: window.innerHeight - MENU_BAR_HEIGHT - DOCK_HEIGHT - (MARGIN * 2),
        };
      }),
    });
  },
}));
