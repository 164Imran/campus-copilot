import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import MenuBar from '../components/os/MenuBar';
import './LandingPage.css';

const TAGLINES = [
  'Sign in to pick up where you left off.',
  'Your courses, calendar, and campus — in one place.',
  'Plan deadlines, book study rooms, ask the copilot.',
  'Built for life at TUM.',
];

/** Shutter intro: lid closed → split reveal → main UI (Casper-style). */
const CURTAIN_HOLD_MS = 3200;
const CURTAIN_OPEN_MS = 1200;

export default function LandingPage() {
  const navigate = useNavigate();
  const [time, setTime] = useState(() => new Date());
  const [taglineIndex, setTaglineIndex] = useState(0);
  const [curtain, setCurtain] = useState<'closed' | 'opening' | 'open'>('closed');

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const reduce =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
    if (reduce) {
      setCurtain('open');
      return;
    }
    const hold = setTimeout(() => setCurtain('opening'), CURTAIN_HOLD_MS);
    return () => clearTimeout(hold);
  }, []);

  useEffect(() => {
    if (curtain !== 'opening') return;
    const done = setTimeout(() => setCurtain('open'), CURTAIN_OPEN_MS);
    return () => clearTimeout(done);
  }, [curtain]);

  useEffect(() => {
    if (curtain !== 'open') return;
    const id = setInterval(() => {
      setTaglineIndex((i) => (i + 1) % TAGLINES.length);
    }, 4000);
    return () => clearInterval(id);
  }, [curtain]);

  const longDate = time.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  const handleLogin = () => {
    navigate('/desktop');
  };

  const showCurtain = curtain !== 'open';

  return (
    <main className="landing" aria-busy={showCurtain}>
      {showCurtain && (
        <div
          className={`landing-curtain${curtain === 'opening' ? ' landing-curtain--opening' : ''}`}
          aria-hidden
        >
          <div className="landing-curtain__panel landing-curtain__panel--top" />
          <div className="landing-curtain__panel landing-curtain__panel--bottom" />
          <div className="landing-curtain__brand">
            <p className="landing-curtain__wordmark">TUM&nbsp;OS</p>
            <div className="landing-curtain__loader" aria-hidden>
              <span className="landing-curtain__arc" />
            </div>
          </div>
        </div>
      )}

      <div className="landing__content" aria-hidden={showCurtain}>
        <div className="desktop-background landing__wallpaper" aria-hidden />
        <div className="landing__vignette" aria-hidden />

        <MenuBar landing />

        <section className="landing__hero">
          <p className="landing__date">{longDate}</p>
          <h1 className="landing__title">
            <span className="landing__title-line">Welcome to TUM&nbsp;OS.</span>
            <span className="landing__tagline">
              <em key={taglineIndex} className="landing__title-em">
                {TAGLINES[taglineIndex]}
              </em>
            </span>
          </h1>
        </section>

        <section className="landing__card" aria-labelledby="landing-user-label">
          <div className="landing__avatar" aria-hidden>
            <span className="landing__avatar-initials">TS</span>
          </div>
          <p id="landing-user-label" className="landing__user-name">
            TUM Student
          </p>

          <button type="button" className="landing__login-btn" onClick={handleLogin}>
            Login
          </button>

          <button type="button" className="landing__switch">
            Switch User
          </button>
        </section>

        <button type="button" className="landing__power glass-panel" aria-label="Power">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M12 2v10M18.364 5.636a9 9 0 1 1-12.728 0"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </main>
  );
}
