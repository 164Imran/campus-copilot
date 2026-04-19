import { ReactElement } from 'react';
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

export default function Desktop() {
  const windows = useOsStore((state) => state.windows);

  return (
    <main className="desktop">
      <div className="desktop-background" />
      <MenuBar />

      <section className="desktop-icons">
        <AppIcon appId="copilot" />
        <AppIcon appId="calendar" />
        <AppIcon appId="courses" />
        <AppIcon appId="voice" />
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
