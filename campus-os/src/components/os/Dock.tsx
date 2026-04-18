import { CSSProperties, MouseEvent, useRef, useState } from 'react';
import { AppId, useOsStore } from '../../store/osStore';
import { ICON_MAP } from './iconMap';

const APPS: { appId: AppId; label: string; iconUrl: string }[] = [
  { appId: 'copilot', label: 'Copilot', iconUrl: ICON_MAP.copilot.iconUrl },
  { appId: 'calendar', label: 'Calendar', iconUrl: ICON_MAP.calendar.iconUrl },
  { appId: 'courses', label: 'Courses', iconUrl: ICON_MAP.courses.iconUrl },
  { appId: 'voice', label: 'Voice', iconUrl: ICON_MAP.voice.iconUrl },
];

export default function Dock() {
  const openWindow = useOsStore((state) => state.openWindow);
  const [cursorX, setCursorX] = useState<number | null>(null);
  const itemRefs = useRef<Partial<Record<AppId, HTMLButtonElement | null>>>({});

  const onDockMove = (event: MouseEvent<HTMLElement>) => {
    setCursorX(event.clientX);
  };

  const getItemStyle = (appId: AppId): CSSProperties => {
    if (cursorX === null) return {};
    const element = itemRefs.current[appId];
    if (!element) return {};

    const rect = element.getBoundingClientRect();
    const itemCenter = rect.left + rect.width / 2;
    const distance = Math.abs(cursorX - itemCenter);
    const influence = Math.max(0, 1 - distance / 140);
    const scale = 1 + influence * 0.42;
    const translateY = -influence * 12;

    return {
      transform: `translateY(${translateY}px) scale(${scale})`,
      zIndex: Math.round(scale * 10),
    };
  };

  return (
    <div className="dock-wrapper">
      <nav
        className="dock glass-panel"
        aria-label="Application dock"
        onMouseMove={onDockMove}
        onMouseLeave={() => setCursorX(null)}
      >
        {APPS.map((app) => (
          <button
            key={app.appId}
            type="button"
            className="dock-item"
            onClick={() => openWindow(app.appId)}
            ref={(element) => {
              itemRefs.current[app.appId] = element;
            }}
            style={getItemStyle(app.appId)}
          >
            <img src={app.iconUrl} alt={app.label} className="dock-icon-image" />
            <span className="dock-tooltip">{app.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
