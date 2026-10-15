import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Menu, Check } from "lucide-react";
import { Logo } from "@/components/AppShell";
import PhoneShort from "@/components/PhoneShort";
import { STYLES, LANGUAGES } from "@/constants/studio";
import "./PhaseZero.css";

export default function Landing() {
  const [paused, setPaused] = useState(false);
  return <div className="phase-landing">
    <header className="phase-nav phase-wrap"><Link to="/" aria-label="Home"><Logo light /></Link>
      <nav aria-label="Main navigation"><a href="#how">How it works</a><a href="#styles">Story styles</a><Link to="/login" data-testid="landing-login-link">Sign in</Link></nav>
      <details className="phase-mobile-menu"><summary aria-label="Open menu"><Menu /></summary><nav><a href="#how">How it works</a><a href="#styles">Story styles</a><Link to="/login">Sign in</Link></nav></details>
      <Link to="/register" className="btn-primary" data-testid="landing-get-started-btn">Create a video</Link>
    </header>
    <main>
      <section className="phase-wrap phase-hero">
        <div><span className="phase-eyebrow">Your story. Your language.</span><h1>A little idea.<br />A story worth<br /><em>sharing.</em></h1>
          <p>Turn your idea into a narrated video with beautiful pictures, captions and a voice that fits. Review the story at every step.</p>
          <Link to="/register" className="btn-primary" data-testid="hero-cta-btn">Make your first video <ArrowRight size={18} /></Link>
          <a href="#how" className="phase-text-link">See how it works</a>
          <div className="phase-assurance"><span><Check size={15} /> Edit before you export</span><span><Check size={15} /> Made for your phone</span></div>
        </div>
        <div className="phase-phone"><span className="phase-phone-label">A story from the studio</span><PhoneShort /><span className="phase-phone-note">Illustrative demo · your story is created from your idea</span></div>
      </section>
      <section id="styles" className="phase-styles" aria-labelledby="styles-title">
        <div className="phase-wrap phase-section-heading"><div><span className="phase-eyebrow">Find your look</span><h2 id="styles-title">Six styles. Your imagination.</h2></div><button className="btn-secondary" onClick={() => setPaused(!paused)} aria-pressed={paused}>{paused ? "Play gallery" : "Pause gallery"}</button></div>
        <div className={`phase-gallery ${paused ? "paused" : ""}`}><div className="phase-track">{[...STYLES, ...STYLES].map((style, i) => <figure key={i} aria-hidden={i >= STYLES.length}><img src={`/styles/${style.id}.jpg`} alt={i < STYLES.length ? style.label : ""} loading="lazy" width="200" height="250" /><figcaption>{style.label}</figcaption></figure>)}</div></div>
      </section>
      <section id="how" className="phase-wrap phase-how"><span className="phase-eyebrow">Simple from the start</span><h2>Tell it. Shape it. Share it.</h2><div className="phase-steps">
        {[['01', 'Tell us your idea', 'Choose a language and describe what your story should say.'], ['02', 'Make it yours', 'Read the story, check each picture and listen to the voice.'], ['03', 'Save your video', 'Get a video with captions, plus a title and post details.']].map(([n,title,copy]) => <article key={n}><span>{n}</span><h3>{title}</h3><p>{copy}</p></article>)}
      </div><div className="phase-languages" aria-label="Creation languages">{LANGUAGES.map(l => <span lang={l.id} key={l.id}>{l.native}</span>)}</div></section>
      <section className="phase-wrap phase-start"><div><h2>Your next story starts here.</h2><p>Private beta. Help shape the studio with your feedback.</p></div><Link to="/register" className="btn-primary" data-testid="footer-cta-btn">Start creating <ArrowRight size={18} /></Link></section>
    </main><footer className="phase-wrap phase-footer"><Logo light /><span>Made for Indian storytellers</span><Link to="/login">Sign in</Link></footer>
  </div>;
}
