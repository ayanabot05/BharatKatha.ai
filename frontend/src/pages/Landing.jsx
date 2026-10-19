import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Menu, Check } from "lucide-react";
import { Logo } from "@/components/AppShell";
import PhoneShort from "@/components/PhoneShort";
import Pricing from "@/components/Pricing";
import MotionSoon from "@/components/MotionSoon";
import { STYLES, LANGUAGES } from "@/constants/studio";
import { Aurora, Coverflow3D, FilmFloor, Float3D, Parallax3D, Reveal3D, RevealIn, Stage3D, Tilt3D } from "@/components/fx3d";
import { useSeo } from "@/lib/seo";
import { trackVisit } from "@/lib/analytics";
import "./PhaseZero.css";

export default function Landing() {
  const [paused, setPaused] = useState(false);
  // One visit per browser session, recorded first-party on our own server.
  useEffect(() => { trackVisit("/"); }, []);
  useSeo({
    title: "BharatKatha — Turn your idea into a narrated video in your language",
    description: "BharatKatha is a storytelling studio for Indian creators. Turn a one-line idea into a narrated video with AI illustrations, captions and a voice — 11 Indian languages, AI narration in 10.",
    path: "/",
  });
  return <div className="phase-landing fx3d-root">
    <Aurora />
    <header className="phase-nav phase-wrap"><Link to="/" aria-label="Home"><Logo light /></Link>
      <nav aria-label="Main navigation"><a href="#how">How it works</a><a href="#styles">Story styles</a><a href="#pricing">Pricing</a><Link to="/login" data-testid="landing-login-link">Sign in</Link></nav>
      <details className="phase-mobile-menu"><summary aria-label="Open menu"><Menu /></summary><nav><a href="#how">How it works</a><a href="#styles">Story styles</a><a href="#pricing">Pricing</a><Link to="/login">Sign in</Link></nav></details>
      <Link to="/register" className="btn-primary fx3d-shine" data-testid="landing-get-started-btn">Create a video</Link>
    </header>
    <main>
      <section className="phase-wrap phase-hero fx3d-hero">
        <FilmFloor />
        <div>
          <RevealIn><span className="phase-eyebrow">Your story. Your language.</span></RevealIn>
          <RevealIn delay={0.06} y={32} rotate={9}><h1>A little idea.<br />A story worth<br /><em>sharing.</em></h1></RevealIn>
          <RevealIn delay={0.12}><p>Turn your idea into a narrated video with beautiful pictures, captions and a voice that fits. Review the story at every step.</p></RevealIn>
          <RevealIn delay={0.18}>
            <Link to="/register" className="btn-primary fx3d-shine" data-testid="hero-cta-btn">Make your first video <ArrowRight size={18} /></Link>
            <a href="#how" className="phase-text-link">See how it works</a>
          </RevealIn>
          <RevealIn delay={0.24}><div className="phase-assurance"><span><Check size={15} /> Edit before you export</span><span><Check size={15} /> Made for your phone</span></div></RevealIn>
        </div>
        <div className="phase-phone">
          <span className="phase-phone-label">A story from the studio</span>
          <Stage3D className="fx3d-hero-stage">
            <Float3D y={14} rotate={1.4} tiltY={13} duration={7}>
              <Tilt3D max={13} className="fx3d-hero-tilt">
                <Parallax3D depth={12} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <span className="fx3d-hero-orb fx3d-hero-orb--a" aria-hidden />
                  <PhoneShort />
                  <span className="fx3d-chip fx3d-chip--lang" aria-hidden>తెలుగు · 11 languages</span>
                  <span className="fx3d-chip fx3d-chip--styles" aria-hidden>6 story styles</span>
                </Parallax3D>
              </Tilt3D>
            </Float3D>
          </Stage3D>
          <span className="phase-phone-note">Illustrative demo · your story is created from your idea</span>
        </div>
      </section>
      <section id="styles" className="phase-styles" aria-labelledby="styles-title">
        <div className="phase-wrap phase-section-heading"><Reveal3D><div><span className="phase-eyebrow">Find your look</span><h2 id="styles-title">Six styles. Your imagination.</h2></div></Reveal3D><button className="btn-secondary" onClick={() => setPaused(!paused)} aria-pressed={paused}>{paused ? "Play gallery" : "Pause gallery"}</button></div>
        <div className="phase-wrap"><Coverflow3D items={STYLES} paused={paused} /></div>
      </section>
      <section id="how" className="phase-wrap phase-how"><Reveal3D><span className="phase-eyebrow">Simple from the start</span><h2>Tell it. Shape it. Share it.</h2></Reveal3D><div className="phase-steps">
        {[['01', 'Tell us your idea', 'Choose a language and describe what your story should say.'], ['02', 'Make it yours', 'Read the story, check each picture and listen to the voice.'], ['03', 'Save your video', 'Get a video with captions, plus a title and post details.']].map(([n, title, copy], i) => <Reveal3D key={n} delay={i * 0.08}><Tilt3D max={9} glare={false} className="fx3d-step"><article><span>{n}</span><h3>{title}</h3><p>{copy}</p></article></Tilt3D></Reveal3D>)}
      </div><div className="phase-languages" aria-label="Creation languages">{LANGUAGES.map(l => <span lang={l.id} key={l.id}>{l.native}</span>)}</div></section>
      <MotionSoon />
      <section id="pricing" className="phase-wrap" style={{ paddingBlock: "56px" }} aria-labelledby="pricing-title"><Reveal3D><Pricing /></Reveal3D></section>
      <section className="phase-wrap phase-start"><Reveal3D><div><h2>Your next story starts here.</h2><p>Private beta. Help shape the studio with your feedback.</p></div></Reveal3D><Reveal3D delay={0.08}><Link to="/register" className="btn-primary fx3d-shine" data-testid="footer-cta-btn">Start creating <ArrowRight size={18} /></Link></Reveal3D></section>
    </main><footer className="phase-wrap phase-footer"><Logo light /><span>Made for Indian storytellers</span><Link to="/login">Sign in</Link></footer>
  </div>;
}
