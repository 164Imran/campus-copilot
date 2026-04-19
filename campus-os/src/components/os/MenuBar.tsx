import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

type MenuBarProps = {
  /** Lock screen: static “Desktop” label to match mac-login-portal menubar */
  landing?: boolean;
};

export default function MenuBar({ landing = false }: MenuBarProps) {
  const navigate = useNavigate();
  const [timeLabel, setTimeLabel] = useState('');
  const [dayLabel, setDayLabel] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeLabel(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
      setDayLabel(
        now.toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
        })
      );
    };
    update();
    const intervalId = setInterval(update, 1000);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <header className="menubar glass-panel">
      <div className="menubar-left menubar-brand">
        <img src="/tum-logo-blue.jpeg" alt="TUM logo" className="menubar-tum-logo" />
        <span className="menubar-active-app">TUM OS</span>
        {landing ? (
          <span className="menubar-button menubar-landing-context">Desktop</span>
        ) : (
          <button
            type="button"
            className="menubar-button menubar-back"
            onClick={() => navigate('/')}
          >
            Lock
          </button>
        )}
      </div>
      <div className="menubar-right">
        <span className="menubar-button">{dayLabel}</span>
        <span className="menubar-button">{timeLabel}</span>
      </div>
    </header>
  );
}
