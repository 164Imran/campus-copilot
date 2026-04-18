import { AppId, useOsStore } from '../../store/osStore';
import { ICON_MAP } from './iconMap';

interface AppIconProps {
  appId: AppId;
}

export default function AppIcon({ appId }: AppIconProps) {
  const openWindow = useOsStore((state) => state.openWindow);
  const app = ICON_MAP[appId];

  return (
    <button type="button" className="desktop-icon" onDoubleClick={() => openWindow(appId)} onClick={() => openWindow(appId)}>
      <span className="desktop-icon-badge">
        <img src={app.iconUrl} alt={app.label} className="desktop-icon-image" />
      </span>
      <span className="desktop-icon-label">{app.label}</span>
    </button>
  );
}
