import { AppId } from '../../store/osStore';

export const ICON_MAP: Record<AppId, { label: string; iconUrl: string }> = {
  copilot: {
    label: 'TUM Copilot',
    iconUrl: '/icons/macos-light-folders/copilot.png',
  },
  calendar: {
    label: 'TUM Calendar',
    iconUrl: '/icons/macos-light-folders/calendar.png',
  },
  courses: {
    label: 'TUM Courses',
    iconUrl: '/icons/macos-light-folders/courses.png',
  },
  voice: {
    label: 'TUM Voice',
    iconUrl: '/icons/macos-light-folders/voice.png',
  },
};
