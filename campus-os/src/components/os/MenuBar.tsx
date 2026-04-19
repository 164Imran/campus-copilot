import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function MenuBar() {
  const navigate = useNavigate();
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
        <button
          type="button"
          className="menubar-button menubar-back"
          onClick={() => navigate('/')}
        >
          Bureau
        </button>
      </div>
      <div className="menubar-right">
        <span className="menubar-button">{dayLabel}</span>
        <span className="menubar-button">{timeLabel}</span>
      </div>
    </header>
  );
}
