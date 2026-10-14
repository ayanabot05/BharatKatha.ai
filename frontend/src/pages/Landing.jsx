import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronLeft, ChevronRight, Lightbulb, Mic, Captions, Film, Play, Pencil, Sparkles, Check, BookOpen, Crown, Music, TreePine, Flame, Landmark } from "lucide-react";
import { Logo } from "@/components/AppShell";
import PhoneShort, { SHOWCASE } from "@/components/PhoneShort";
import { CursorGlow, Magnetic, RamAvatar, StreamText, BlurReveal, WordMorph, usePointerVars, reducedMotion, clamp } from "@/components/fx";
import { STYLES, LANGUAGES } from "@/constants/studio";
import "./Landing.css";
import "./LandingWorld.css";

const FLOW = [
  { icon: Lightbulb, title: "Find your idea", text: "Start with your own story or explore fresh regional ideas." },
  { icon: Pencil, title: "Make it yours", text: "Review the script, choose a look, and edit each scene." },
  { icon: Mic, title: "Give it a voice", text: "Add narration in your language or record your own voice." },
  { icon: Captions, title: "Finish and share", text: "Add captions, a cover and post details, then export your video." },
];

const TINTS = ["#fbdcdc", "#fde9d2", "#dcefdf", "#dde9f8", "#eadcf5", "#fbe3cf"];
const STEP = 360 / 6;

const WORLDS = [
  { icon: BookOpen, title: "Moral stories", hint: "Gentle lessons with heart", c: "#fbdcdc" },
  { icon: Crown, title: "Mythology & epics", hint: "Gods, heroes and legends", c: "#fde9d2" },
  { icon: Music, title: "Kids' rhymes", hint: "Songs little ones repeat", c: "#dde9f8" },
  { icon: TreePine, title: "Folk tales", hint: "Village stories, retold", c: "#dcefdf" },
  { icon: Flame, title: "Festival stories", hint: "Diwali, Karthika Masam & more", c: "#fbe3cf" },
  { icon: Landmark, title: "History heroes", hint: "People who shaped us", c: "#eadcf5" },
];

/* ---------- Scroll reveal ---------- */
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll(".landing-page .reveal");
    if (reducedMotion() || !("IntersectionObserver" in window)) { els.forEach((el) => el.classList.add("in")); return undefined; }
    const io = new IntersectionObserver((entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.15 });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

/* ---------- 3D style ring (cursor scrubs it, tints the section) ---------- */
function StyleCarousel({ onActive }) {
  const stageRef = useRef(null);
  const ringRef = useRef(null);
  const faceRefs = useRef([]);
  const s = useRef({ angle: 0, vel: 0, target: null, tx: 0, ty: 0, cx: 0, cy: 0, hover: false, drag: false, lastX: 0, active: 0 });
  const [active, setActive] = useState(0);
  useEffect(() => { onActive?.(active); }, [active, onActive]);

  useEffect(() => {
    const st = s.current;
    const calm = reducedMotion();
    let raf;
    const tick = () => {
      if (!document.hidden) {
        if (st.target !== null) {
          st.angle += (st.target - st.angle) * 0.1;
          if (Math.abs(st.target - st.angle) < 0.05) { st.angle = st.target; st.target = null; }
          st.vel = 0;
        } else {
          st.angle += st.vel + (calm || st.drag ? 0 : st.hover ? -0.05 : -0.14);
          st.vel *= 0.93;
        }
        st.cx += (st.tx - st.cx) * 0.08;
        st.cy += (st.ty - st.cy) * 0.08;
        const ring = ringRef.current;
        if (ring) ring.style.transform = `rotateX(${(-7 + st.cy * -8).toFixed(2)}deg) rotateY(${(st.angle + st.cx * 6).toFixed(2)}deg)`;
        faceRefs.current.forEach((f, i) => {
          if (!f) return;
          const front = Math.max(0, Math.cos(((i * STEP + st.angle) * Math.PI) / 180));
          f.style.opacity = (0.35 + 0.65 * front).toFixed(3);
          f.style.filter = `saturate(${(0.7 + 0.3 * front).toFixed(2)})`;
          f.style.zIndex = Math.round(front * 10);
        });
        const idx = ((Math.round(-st.angle / STEP) % 6) + 6) % 6;
        if (idx !== st.active) { st.active = idx; setActive(idx); }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const onMove = (e) => {
    const st = s.current;
    const r = stageRef.current.getBoundingClientRect();
    st.tx = clamp(((e.clientX - r.left) / r.width) * 2 - 1, -1, 1);
    st.ty = clamp(((e.clientY - r.top) / r.height) * 2 - 1, -1, 1);
    const dx = e.clientX - st.lastX;
    st.lastX = e.clientX;
    if (e.pointerType === "touch" && !st.drag) return;
    st.target = null;
    st.vel = clamp(st.vel + dx * 0.045, -7, 7);
  };
  const snapTo = (i) => {
    const st = s.current;
    const base = Math.round(-st.angle / STEP);
    let diff = ((i - base) % 6 + 6) % 6;
    if (diff > 3) diff -= 6;
    st.target = -(base + diff) * STEP;
  };
  const move = (d) => { const st = s.current; st.target = Math.round(st.angle / STEP) * STEP - d * STEP; };

  return (
    <div ref={stageRef} className="landing-stage landing-style-stage" aria-label="Interactive 3D gallery of six video styles. Move your cursor to spin it."
      onPointerEnter={(e) => { s.current.hover = true; s.current.lastX = e.clientX; }}
      onPointerLeave={() => { const st = s.current; st.hover = false; st.drag = false; st.tx = 0; st.ty = 0; }}
      onPointerDown={(e) => { s.current.drag = true; s.current.lastX = e.clientX; }}
      onPointerUp={() => { s.current.drag = false; }}
      onPointerCancel={() => { s.current.drag = false; }}
      onPointerMove={onMove}>
      <div className="landing-stage-glow" />
      <div className="landing-orbit landing-orbit-one" aria-hidden="true" />
      <div className="landing-orbit landing-orbit-two" aria-hidden="true" />
      <div className="landing-carousel-perspective">
        <div className="landing-carousel" ref={ringRef}>
          {STYLES.map((style, index) => (
            <button type="button" key={style.id} ref={(el) => { faceRefs.current[index] = el; }} onClick={() => snapTo(index)}
              className="landing-carousel-face" style={{ transform: `rotateY(${index * STEP}deg) translateZ(var(--carousel-depth))` }}
              aria-label={`Show ${style.label} style`} aria-current={index === active}>
              <span className="landing-carousel-image"><img src={`/styles/${style.id}.jpg`} alt="" draggable="false" /><span className="landing-carousel-shine" /></span>
              <span className="landing-carousel-caption"><span>STYLE {String(index + 1).padStart(2, "0")}</span><strong>{style.label}</strong><span>{style.hint}</span></span>
            </button>
          ))}
        </div>
      </div>
      <div className="landing-stage-label"><Sparkles size={15} /> Move your cursor to explore</div>
      <div className="landing-carousel-controls">
        <button type="button" onClick={() => move(-1)} aria-label="Previous video style"><ChevronLeft size={19} /></button>
        <div aria-live="polite"><strong>{STYLES[active].label}</strong><span>{active + 1} / {STYLES.length}</span></div>
        <button type="button" onClick={() => move(1)} aria-label="Next video style"><ChevronRight size={19} /></button>
      </div>
    </div>
  );
}

/* ---------- Hero phone: inherits --mx/--my from the hero section ---------- */
function HeroVisual() {
  return (
    <div className="landing-demo-wrap">
      <div className="landing-demo-orbit" aria-hidden="true" />
      <div className="landing-demo-tilt">
        <span className="landing-chip landing-chip-a" aria-hidden="true"><i><Check size={13} /> Script ready</i></span>
        <span className="landing-chip landing-chip-b indic" aria-hidden="true"><i>తెలుగు · हिन्दी · தமிழ்</i></span>
        <span className="landing-chip landing-chip-c" aria-hidden="true"><i><Mic size={13} /> Voice added</i></span>
        <PhoneShort className="landing-demo-phone" />
      </div>
    </div>
  );
}

/* ---------- Live demo: an idea becomes a video, on loop ---------- */
const IDEA = "మాట్లాడే ఆవు – నిజాయితీ పాఠం";
const STAGES = ["Idea", "Script", "Scenes", "Voice", "Video"];
const RAM = ["thinking", "writing", "painting", "idle", "idle"];
const RAM_TEXT = ["Reading your idea…", "Writing the script…", "Painting every scene…", "Recording the narration…", "Your video is ready"];

function LiveDemo() {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  const [stage, setStage] = useState(0);
  const [n, setN] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) { setInView(true); return undefined; }
    const io = new IntersectionObserver(([e]) => setInView(e.isIntersecting), { threshold: 0.3 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!inView) return undefined;
    if (reducedMotion()) { setStage(4); setN(SHOWCASE.length); return undefined; }
    let tid;
    if (stage === 0) tid = setTimeout(() => { setStage(1); setN(0); }, 2800);
    else if (stage === 1) tid = n < SHOWCASE.length ? setTimeout(() => setN(n + 1), 650) : setTimeout(() => { setStage(2); setN(0); }, 800);
    else if (stage === 2) tid = n < SHOWCASE.length ? setTimeout(() => setN(n + 1), 700) : setTimeout(() => { setStage(3); setN(0); }, 800);
    else if (stage === 3) tid = setTimeout(() => { setStage(4); setN(0); }, 2200);
    else tid = setTimeout(() => { setStage(0); setN(0); }, 7500);
    return () => clearTimeout(tid);
  }, [inView, stage, n]);

  return (
    <section className="landing-live-section" ref={ref} aria-labelledby="landing-live-title">
      <div className="landing-shell landing-live">
        <div className="landing-live-left">
          <div className="reveal">
            <span className="landing-kicker">Watch it happen</span>
            <h2 id="landing-live-title">An idea becomes a video.</h2>
            <p>One line from you. Ram AI writes, paints, speaks and captions — and you stay in charge of every step.</p>
          </div>
          <div className="landing-live-board reveal" style={{ "--d": "100ms" }}>
            <div className="live-head">
              <RamAvatar state={RAM[stage]} size={42} />
              <div><strong>Ram AI</strong><span aria-live="polite">{RAM_TEXT[stage]}</span></div>
            </div>
            <ol className="live-stages">{STAGES.map((s, i) => <li key={s} className={i === stage ? "on" : i < stage ? "done" : ""}>{i < stage ? <Check size={12} /> : i + 1}<span>{s}</span></li>)}</ol>
            <div className="live-idea indic">{stage === 0 ? <StreamText text={IDEA} speed={85} /> : IDEA}</div>
            {stage >= 1 && <ul className="live-script indic">{SHOWCASE.slice(0, stage === 1 ? n : SHOWCASE.length).map((s) => <li key={s.cap}>{s.cap}</li>)}</ul>}
            {stage >= 2 && <div className="live-tiles">{SHOWCASE.map((s, i) => <div className="live-tile" key={s.img}>{stage > 2 || i < n ? <BlurReveal src={s.img} /> : <span className="fx-shimmer" />}</div>)}</div>}
            {stage >= 3 && <div className="live-wave" aria-hidden="true">{Array.from({ length: 28 }, (_, i) => <i key={i} style={{ "--k": `${(i * 53) % 100}`, animationDelay: `${(i % 7) * 90}ms` }} />)}</div>}
          </div>
        </div>
        <div className={`landing-live-phone ${stage === 4 ? "on" : ""}`}>
          <div className="landing-live-halo" aria-hidden="true" />
          <PhoneShort key={stage === 4 ? "play" : "wait"} />
          <div className="landing-live-ready"><Check size={14} /> Ready to share</div>
        </div>
      </div>
    </section>
  );
}

/* ---------- Worlds & wall ---------- */
function Worlds() {
  return (
    <section className="landing-section landing-worlds"><div className="landing-shell">
      <div className="landing-section-intro reveal"><div><span className="landing-kicker">Start from a world</span><h2>Whatever you tell, there is a world for it.</h2></div><p>Pick the kind of story you love. Your idea, your language, your rules.</p></div>
      <div className="landing-world-grid">
        {WORLDS.map(({ icon: Icon, title, hint, c }, i) => (
          <Link to="/register" key={title} className="landing-world reveal" style={{ "--c": c, "--d": `${(i % 3) * 90}ms` }}>
            <span className="landing-world-icon"><Icon size={24} /></span>
            <strong>{title}</strong><span>{hint}</span>
            <ArrowRight size={18} className="landing-world-arrow" />
          </Link>
        ))}
      </div>
    </div></section>
  );
}

const WALL = [...STYLES.map((s) => ({ img: `/styles/${s.id}.jpg`, label: s.label })), ...SHOWCASE.map((s, i) => ({ img: s.img, label: `Scene ${i + 1}` }))];
function Wall() {
  const row = (items, cls) => (
    <div className={`wall-row ${cls}`}><div className="wall-track">
      {[...items, ...items].map((w, i) => <figure key={i} aria-hidden={i >= items.length}><img src={w.img} alt={i < items.length ? w.label : ""} loading="lazy" /><figcaption>{w.label}</figcaption></figure>)}
    </div></div>
  );
  return (
    <section className="landing-wall"><div className="landing-shell reveal"><span className="landing-kicker">Scenes from the studio</span><h2>A whole world of looks.</h2></div>
      <div className="wall-stage">{row(WALL, "")}{row([...WALL].reverse(), "rev")}</div>
    </section>
  );
}

export default function Landing() {
  useReveal();
  const heroRef = useRef(null);
  usePointerVars(heroRef);
  const [tint, setTint] = useState(0);
  const morphWords = useMemo(() => LANGUAGES.filter((l) => l.id !== "en").map((l) => ({ text: l.native, lang: l.id })), []);
  return (
    <div className="landing-page">
      <CursorGlow />
      <header className="landing-header"><div className="landing-shell landing-nav">
        <Logo light />
        <nav className="landing-nav-links" aria-label="Main navigation"><a href="#styles">Styles</a><a href="#how">How it works</a><a href="#languages">Languages</a></nav>
        <div className="landing-nav-actions"><Link to="/login" data-testid="landing-login-link" className="landing-text-link">Sign in</Link><Link to="/register" data-testid="landing-get-started-btn" className="landing-button landing-button-small">Start creating <ArrowRight size={16} /></Link></div>
      </div></header>

      <main>
        <section className="landing-hero" ref={heroRef}>
          <div className="landing-blob landing-blob-1" aria-hidden="true" /><div className="landing-blob landing-blob-2" aria-hidden="true" />
          {[["12%", "22%", "0s"], ["46%", "12%", "1.2s"], ["88%", "30%", "2.1s"], ["62%", "64%", "0.6s"], ["6%", "70%", "1.7s"]].map(([l, t, d]) => <span key={l} className="landing-spark" style={{ left: l, top: t, animationDelay: d }} aria-hidden="true" />)}
          <div className="landing-hills" aria-hidden="true">
            {[["hill-1", "M0,110 C200,40 420,150 700,90 C980,30 1200,140 1440,70 L1440,220 L0,220Z"], ["hill-2", "M0,100 C260,150 520,40 800,100 C1060,150 1260,60 1440,110 L1440,220 L0,220Z"], ["hill-3", "M0,130 C240,70 500,160 760,120 C1020,80 1240,150 1440,100 L1440,220 L0,220Z"]].map(([c, d]) => (
              <svg key={c} className={`hill ${c}`} viewBox="0 0 1440 220" preserveAspectRatio="none"><path d={d} /></svg>
            ))}
          </div>
          <div className="landing-shell landing-hero-grid">
            <div className="landing-hero-copy">
              <div className="landing-eyebrow rise-in"><span className="landing-eyebrow-dot" /> A video studio for your stories</div>
              <h1 className="rise-in d1">Every story<br />deserves to be <em>seen.</em></h1>
              <p className="landing-morph rise-in d1">Your story, in <WordMorph words={morphWords} className="indic" /></p>
              <p className="landing-lede rise-in d2">Tell Ram AI your idea in your language. Shape the script, choose your characters, edit the scenes and make a short video that feels like yours.</p>
              <div className="landing-hero-actions rise-in d3">
                <Magnetic><Link to="/register" data-testid="hero-cta-btn" className="landing-button">Make your first video <ArrowRight size={19} /></Link></Magnetic>
                <Magnetic><a href="#live" className="landing-outline-button"><Play size={16} /> Watch it happen</a></Magnetic>
              </div>
              <div className="landing-hero-proof rise-in d4"><div><strong>6</strong><span>story styles</span></div><div><strong>10</strong><span>Indian languages</span></div><div><strong>9:16</strong><span>short video format</span></div></div>
            </div>
            <HeroVisual />
          </div>
        </section>

        <div id="live"><LiveDemo /></div>

        <section className="landing-example" aria-labelledby="landing-example-title"><div className="landing-shell landing-example-grid">
          <div className="landing-example-copy reveal">
            <span className="landing-kicker">See how a story takes shape</span>
            <h2 id="landing-example-title">Your idea stays at the centre.</h2>
            <p>Tell us what must happen. Read the script and check every scene before you make the final video.</p>
          </div>
          <ol className="landing-example-steps">
            <li className="reveal"><span>01</span><div><strong>Your idea</strong><p>“A child finds a lost letter and returns it.”</p></div></li>
            <li className="reveal" style={{ "--d": "90ms" }}><span>02</span><div><strong>Your story</strong><p>Check that finding, returning and the ending are all in the script.</p></div></li>
            <li className="reveal" style={{ "--d": "180ms" }}><span>03</span><div><strong>Your video</strong><p>Approve each picture, choose a voice and export.</p></div></li>
          </ol>
        </div></section>

        <section id="languages" className="landing-language-band"><div className="landing-shell landing-language-inner">
          <div className="reveal"><span className="landing-kicker">Speak naturally</span><h2>Your language belongs here.</h2></div>
          <div className="landing-languages reveal" style={{ "--d": "100ms" }} aria-label="Supported creation languages">{LANGUAGES.filter((l) => l.id !== "en").map((l) => <span key={l.id} lang={l.id} className="indic">{l.native}</span>)}</div>
        </div></section>

        <section id="styles" className="landing-section landing-styles-section" style={{ "--tint": TINTS[tint] }}><div className="landing-shell">
          <div className="landing-section-intro reveal"><div><span className="landing-kicker">Choose a world</span><h2>One idea. Six ways to tell it.</h2></div><p>From a familiar face to a painted tale, pick the visual mood that fits your story.</p></div>
          <div className="reveal" style={{ "--d": "120ms" }}><StyleCarousel onActive={setTint} /></div>
        </div></section>

        <Worlds />
        <Wall />

        <section id="how" className="landing-section landing-how-section"><div className="landing-shell landing-how-grid">
          <div className="landing-how-intro reveal"><span className="landing-kicker">From thought to video</span><h2>Make it one step at a time.</h2><p>You can go back, change your mind and keep shaping the video before you export it.</p><Link to="/register" className="landing-inline-link">Open the studio <ArrowRight size={17} /></Link></div>
          <div className="landing-flow">{FLOW.map(({ icon: Icon, title, text }, index) => <div className="landing-flow-step reveal" style={{ "--d": `${index * 90}ms` }} key={title}><span className="landing-flow-number">0{index + 1}</span><span className="landing-flow-icon"><Icon size={21} /></span><div><h3>{title}</h3><p>{text}</p></div></div>)}</div>
        </div></section>

        <section className="landing-closing"><div className="landing-shell landing-closing-inner"><div className="reveal"><Film size={28} /><h2>The next great story<br />could start with yours.</h2><p>Start small. Create in your own voice. Keep improving with every video.</p></div><Magnetic><Link to="/register" data-testid="footer-cta-btn" className="landing-button landing-button-light">Create a story <ArrowRight size={18} /></Link></Magnetic></div></section>
      </main>
      <footer className="landing-footer"><div className="landing-shell"><Logo light /><span>Made in India for Indian storytellers</span><span>© VidBharat</span></div></footer>
    </div>
  );
}