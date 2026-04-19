import { CSSProperties, MouseEvent, ReactElement, useRef, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import TUMCalendar from '../apps/TUMCalendar';
import TUMCopilot from '../apps/TUMCopilot';
import TUMCourses from '../apps/TUMCourses';
import TUMVoice from '../apps/TUMVoice';
import { AppId, useOsStore } from '../../store/osStore';
import AppIcon from './AppIcon';
import Dock from './Dock';
import MenuBar from './MenuBar';
import Window from './Window';

const APP_COMPONENTS: Record<AppId, ReactElement> = {
  copilot: <TUMCopilot />,
  calendar: <TUMCalendar />,
  courses: <TUMCourses />,
  voice: <TUMVoice />,
};

const SIDEBAR_APP_IDS: AppId[] = ['copilot', 'calendar', 'courses', 'voice'];

export default function Desktop() {
  const windows = useOsStore((state) => state.windows);
  const [cursorY, setCursorY] = useState<number | null>(null);
  const sidebarIconRefs = useRef<Partial<Record<AppId, HTMLButtonElement | null>>>({});

  const onSidebarIconsMove = (event: MouseEvent<HTMLElement>) => {
    setCursorY(event.clientY);
  };

  const getSidebarIconStyle = (appId: AppId): CSSProperties => {
    if (cursorY === null) return {};
    const element = sidebarIconRefs.current[appId];
    if (!element) return {};

    const rect = element.getBoundingClientRect();
    const itemCenterY = rect.top + rect.height / 2;
    const distance = Math.abs(cursorY - itemCenterY);
    const influence = Math.max(0, 1 - distance / 130);
    const scale = 1 + influence * 0.4;
    const translateX = -influence * 12;

    return {
      transform: `translateX(${translateX}px) scale(${scale})`,
      zIndex: Math.round(scale * 10),
    };
  };

  return (
    <main className="desktop">
      <div className="desktop-background" />
      <MenuBar />

      <section
        className="desktop-icons"
        onMouseMove={onSidebarIconsMove}
        onMouseLeave={() => setCursorY(null)}
      >
        {SIDEBAR_APP_IDS.map((appId) => (
          <AppIcon
            key={appId}
            ref={(el) => {
              sidebarIconRefs.current[appId] = el;
            }}
            appId={appId}
            style={getSidebarIconStyle(appId)}
          />
        ))}
      </section>

      <section className="window-layer">
        <AnimatePresence>
          {windows.map((windowItem) => (
            <Window key={windowItem.id} windowData={windowItem}>
              {APP_COMPONENTS[windowItem.appId]}
            </Window>
          ))}
        </AnimatePresence>
      </section>

      <Dock />
    </main>
  );
}
