import { useEffect, useState } from 'react';

export default function MenuBar() {
  const [timeLabel, setTimeLabel] = useState('');
  const [dayLabel, setDayLabel] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeLabel(now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }));
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
      </div>
      <div className="menubar-right">
        <span className="menubar-button">{dayLabel}</span>
        <span className="menubar-button">{timeLabel}</span>
        <span className="menubar-button">Control Center</span>
        <span className="menubar-button">100%</span>
      </div>
    </header>
  );
}
