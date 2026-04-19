import './LandingPage.css';

const osSrc = `${process.env.PUBLIC_URL ?? ''}/os`;

export default function LandingPage() {
  return (
    <div className="landing-page">
      <div className="landing-page__frame">
        <img
          className="landing-page__img"
          src={`${process.env.PUBLIC_URL ?? ''}/imageStatic.png`}
          alt="Bureau — l’OS s’affiche sur l’écran du Mac"
          width={1920}
          height={1080}
          decoding="async"
        />
        <div className="landing-page__screen">
          <iframe
            className="landing-page__os-frame"
            src={osSrc}
            title="Campus OS"
          />
        </div>
      </div>
    </div>
  );
}
