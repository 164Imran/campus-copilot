import { CSSProperties, forwardRef } from 'react';
import { AppId, useOsStore } from '../../store/osStore';
import { ICON_MAP } from './iconMap';

interface AppIconProps {
  appId: AppId;
  style?: CSSProperties;
}

const AppIcon = forwardRef<HTMLButtonElement, AppIconProps>(function AppIcon(
  { appId, style },
  ref,
) {
  const openWindow = useOsStore((state) => state.openWindow);
  const app = ICON_MAP[appId];

  return (
    <button
      ref={ref}
      type="button"
      className="desktop-icon"
      style={style}
      onDoubleClick={() => openWindow(appId)}
      onClick={() => openWindow(appId)}
    >
      <span className="desktop-icon-badge">
        <img src={app.iconUrl} alt={app.label} className="desktop-icon-image" />
      </span>
      <span className="desktop-icon-label">{app.label}</span>
    </button>
  );
});

export default AppIcon;
