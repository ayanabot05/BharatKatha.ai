import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronLeft, ChevronRight, Lightbulb, Mic, Captions, Film, Play, Pencil, Sparkles } from "lucide-react";
import { Logo } from "@/components/AppShell";
import PhoneShort from "@/components/PhoneShort";
import { STYLES, LANGUAGES } from "@/constants/studio";
import "./Landing.css";

const FLOW = [
  { icon: Lightbulb, title: "Find your idea", text: "Start with your own story or explore fresh regional ideas." },
  { icon: Pencil, title: "Make it yours", text: "Review the script, choose a look, and edit each scene." },
  { icon: Mic, title: "Give it a voice", text: "Add narration in your language or record your own voice." },
  { icon: Captions, title: "Finish and share", text: "Add captions, a cover and post details, then export your video." },
];

function StyleCarousel() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (paused || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    const timer = window.setInterval(() => setActive((current) => (current + 1) % STYLES.length), 4200);
    return () => window.clearInterval(timer);
  }, [paused]);
  const move = (direction) => setActive((current) => (current + direction + STYLES.length) % STYLES.length);
  return (
    <div className="landing-stage landing-style-stage" aria-label="Animated three-dimensional gallery of six video styles" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={() => setPaused(false)}>
      <div className="landing-stage-glow" />
      <div className="landing-orbit landing-orbit-one" aria-hidden="true" />
      <div className="landing-orbit landing-orbit-two" aria-hidden="true" />
      <div className="landing-carousel-perspective">
        <div className="landing-carousel" style={{ transform: `rotateX(-7deg) rotateY(${-active * 60}deg)` }}>
          {STYLES.map((style, index) => <div className="landing-carousel-face" style={{ transform: `rotateY(${index * 60}deg) translateZ(var(--carousel-depth))` }} key={style.id} aria-hidden={index !== active}>
            <div className="landing-carousel-image"><img src={`/styles/${style.id}.jpg`} alt={index === active ? `${style.label} video style preview` : ""} /></div>
            <div className="landing-carousel-caption"><span>SCENE {String(index + 1).padStart(2, "0")}</span><strong>{style.label}</strong><span>{style.hint}</span></div>
          </div>)}
        </div>
      </div>
      <div className="landing-stage-label"><Sparkles size={15} /> Choose your style</div>
      <div className="landing-carousel-controls"><button type="button" onClick={() => move(-1)} aria-label="Previous video style"><ChevronLeft size={19} /></button><div aria-live="polite"><strong>{STYLES[active].label}</strong><span>{active + 1} / {STYLES.length}</span></div><button type="button" onClick={() => move(1)} aria-label="Next video style"><ChevronRight size={19} /></button></div>
    </div>
  );
}

function HeroVisual() {
  return <div className="landing-demo-wrap"><div className="landing-demo-orbit" aria-hidden="true" /><PhoneShort className="landing-demo-phone" /></div>;
}

export default function Landing() {
  return (
    <div className="landing-page">
      <header className="landing-header"><div className="landing-shell landing-nav">
        <Logo light />
        <nav className="landing-nav-links" aria-label="Main navigation"><a href="#styles">Styles</a><a href="#how">How it works</a><a href="#languages">Languages</a></nav>
        <div className="landing-nav-actions"><Link to="/login" data-testid="landing-login-link" className="landing-text-link">Sign in</Link><Link to="/register" data-testid="landing-get-started-btn" className="landing-button landing-button-small">Start creating <ArrowRight size={16} /></Link></div>
      </div></header>

      <main>
        <section className="landing-hero"><div className="landing-shell landing-hero-grid">
          <div className="landing-hero-copy">
            <div className="landing-eyebrow"><span className="landing-eyebrow-dot" /> A video studio for your stories</div>
            <h1>Every story<br />deserves to be <em>seen.</em></h1>
            <p className="landing-lede">Tell Ram AI your idea in your language. Shape the script, choose your characters, edit the scenes and make a short video that feels like yours.</p>
            <div className="landing-hero-actions"><Link to="/register" data-testid="hero-cta-btn" className="landing-button">Make your first video <ArrowRight size={19} /></Link><a href="#how" className="landing-outline-button"><Play size={16} /> See how it works</a></div>
            <div className="landing-hero-proof"><div><strong>6</strong><span>story styles</span></div><div><strong>10</strong><span>Indian languages</span></div><div><strong>9:16</strong><span>short video format</span></div></div>
          </div>
          <HeroVisual />
        </div></section>

        <section id="languages" className="landing-language-band"><div className="landing-shell landing-language-inner">
          <div><span className="landing-kicker">Speak naturally</span><h2>Your language belongs here.</h2></div>
          <div className="landing-languages" aria-label="Supported creation languages">{LANGUAGES.filter((l) => l.id !== "en").map((l) => <span key={l.id} lang={l.id} className="indic">{l.native}</span>)}</div>
        </div></section>

        <section id="styles" className="landing-section landing-styles-section"><div className="landing-shell">
          <div className="landing-section-intro"><div><span className="landing-kicker">Choose a world</span><h2>One idea. Six ways to tell it.</h2></div><p>From a familiar face to a painted tale, pick the visual mood that fits your story.</p></div>
          <StyleCarousel />
        </div></section>

        <section id="how" className="landing-section landing-how-section"><div className="landing-shell landing-how-grid">
          <div className="landing-how-intro"><span className="landing-kicker">From thought to video</span><h2>Make it one step at a time.</h2><p>You can go back, change your mind and keep shaping the video before you export it.</p><Link to="/register" className="landing-inline-link">Open the studio <ArrowRight size={17} /></Link></div>
          <div className="landing-flow">{FLOW.map(({ icon: Icon, title, text }, index) => <div className="landing-flow-step" key={title}><span className="landing-flow-number">0{index + 1}</span><span className="landing-flow-icon"><Icon size={21} /></span><div><h3>{title}</h3><p>{text}</p></div></div>)}</div>
        </div></section>

        <section className="landing-closing"><div className="landing-shell landing-closing-inner"><div><Film size={28} /><h2>The next great story<br />could start with yours.</h2><p>Start small. Create in your own voice. Keep improving with every video.</p></div><Link to="/register" data-testid="footer-cta-btn" className="landing-button landing-button-light">Create a story <ArrowRight size={18} /></Link></div></section>
      </main>
      <footer className="landing-footer"><div className="landing-shell"><Logo light /><span>Made in India for Indian storytellers</span><span>© VidBharat</span></div></footer>
    </div>
  );
}
