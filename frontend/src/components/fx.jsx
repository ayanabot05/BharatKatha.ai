import { useEffect, useMemo, useRef, useState } from "react";
import "./world.css";

export const reducedMotion = () => typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
export const coarsePointer = () => typeof window !== "undefined" && !!window.matchMedia?.("(pointer: coarse)").matches;
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

/* Soft glow that follows the cursor (desktop only) */
export function CursorGlow() {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion() || coarsePointer()) return undefined;
    let tx = window.innerWidth / 2, ty = window.innerHeight / 3, x = tx, y = ty, raf;
    const move = (e) => { tx = e.clientX; ty = e.clientY; el.style.opacity = 1; };
    const leave = () => { el.style.opacity = 0; };
    const tick = () => {
      x += (tx - x) * 0.12; y += (ty - y) * 0.12;
      el.style.setProperty("--gx", `${x.toFixed(1)}px`);
      el.style.setProperty("--gy", `${y.toFixed(1)}px`);
      raf = requestAnimationFrame(tick);
    };
    window.addEventListener("pointermove", move);
    document.addEventListener("pointerleave", leave);
    raf = requestAnimationFrame(tick);
    return () => { window.removeEventListener("pointermove", move); document.removeEventListener("pointerleave", leave); cancelAnimationFrame(raf); };
  }, []);
  return <div ref={ref} className="fx-glow" aria-hidden="true" />;
}

/* Sets --mx / --my (-1..1, eased) on an element from the cursor position; children can use them for parallax */
export function usePointerVars(ref) {
  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion() || coarsePointer()) return undefined;
    let tx = 0, ty = 0, cx = 0, cy = 0, raf;
    const move = (e) => {
      const r = el.getBoundingClientRect();
      tx = clamp((e.clientX - (r.left + r.width / 2)) / (r.width / 2), -1, 1);
      ty = clamp((e.clientY - (r.top + r.height / 2)) / (r.height / 2), -1, 1);
    };
    const leave = () => { tx = 0; ty = 0; };
    const tick = () => {
      if (!document.hidden) {
        cx += (tx - cx) * 0.07; cy += (ty - cy) * 0.07;
        el.style.setProperty("--mx", cx.toFixed(3));
        el.style.setProperty("--my", cy.toFixed(3));
      }
      raf = requestAnimationFrame(tick);
    };
    window.addEventListener("pointermove", move);
    document.addEventListener("pointerleave", leave);
    raf = requestAnimationFrame(tick);
    return () => { window.removeEventListener("pointermove", move); document.removeEventListener("pointerleave", leave); cancelAnimationFrame(raf); };
  }, [ref]);
}

/* Button that leans toward the cursor */
export function Magnetic({ children, strength = 0.35, className = "" }) {
  const ref = useRef(null);
  const move = (e) => {
    if (reducedMotion() || e.pointerType === "touch") return;
    const r = ref.current.getBoundingClientRect();
    ref.current.style.transform = `translate(${((e.clientX - (r.left + r.width / 2)) * strength).toFixed(1)}px,${((e.clientY - (r.top + r.height / 2)) * strength).toFixed(1)}px)`;
  };
  const leave = () => { if (ref.current) ref.current.style.transform = ""; };
  return <span ref={ref} className={`fx-magnetic ${className}`} onPointerMove={move} onPointerLeave={leave}>{children}</span>;
}

/* Ram AI — states: idle | thinking | writing | painting */
export function RamAvatar({ state = "idle", size = 40 }) {
  return (
    <span className={`ram ram-${state}`} style={{ width: size, height: size }} role="img" aria-label={`Ram AI is ${state}`}>
      <span className="ram-ring" />
      <span className="ram-face"><i className="ram-eye" /><i className="ram-eye" /><b className="ram-mouth" /></span>
    </span>
  );
}

/* Generated images arrive blurred and sharpen as they load */
export function BlurReveal({ src, alt = "", className = "", ...rest }) {
  const [ok, setOk] = useState(false);
  return <img src={src} alt={alt} onLoad={() => setOk(true)} className={`fx-blur ${ok ? "is-sharp" : ""} ${className}`} {...rest} />;
}

const splitGraphemes = (text) => {
  if (typeof Intl !== "undefined" && Intl.Segmenter) return Array.from(new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text), (s) => s.segment);
  return Array.from(text);
};

/* Text that types itself in (safe for Telugu / Hindi clusters) */
export function StreamText({ text = "", speed = 28, onDone }) {
  const chars = useMemo(() => splitGraphemes(text), [text]);
  const [n, setN] = useState(0);
  useEffect(() => {
    if (reducedMotion()) { setN(chars.length); return undefined; }
    setN(0);
    const id = setInterval(() => setN((v) => {
      if (v >= chars.length) { clearInterval(id); onDone?.(); return v; }
      return v + 1;
    }), speed);
    return () => clearInterval(id);
  }, [chars, speed, onDone]); 
  return <span>{chars.slice(0, n).join("")}{n < chars.length && <i className="fx-caret" />}</span>;
}

/* Rotates through words with a blur-in morph. words: [{ text, lang }] */
export function WordMorph({ words, interval = 2200, className = "" }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (words.length < 2 || reducedMotion()) return undefined;
    const id = setInterval(() => setI((v) => (v + 1) % words.length), interval);
    return () => clearInterval(id);
  }, [words, interval]);
  const w = words[i % words.length];
  if (!w) return null;
  return <span key={i} lang={w.lang} className={`fx-morph ${className}`}>{w.text}</span>;
}

/* Celebration — bump `fire` (a number) to launch */
const COLORS = ["#e8929f", "#f6c28b", "#a9d6b4", "#a9c6ee", "#cdb1ec", "#f7a8a0"];
export function Confetti({ fire = 0 }) {
  const [bits, setBits] = useState([]);
  useEffect(() => {
    if (!fire || reducedMotion()) return undefined;
    setBits(Array.from({ length: 80 }, (_, i) => ({
      id: `${fire}-${i}`, x: `${Math.random() * 100}%`, dx: `${(Math.random() - 0.5) * 240}px`,
      rot: `${Math.random() * 900 - 450}deg`, delay: `${(Math.random() * 0.35).toFixed(2)}s`,
      d: `${(2.4 + Math.random() * 1.8).toFixed(2)}s`, w: `${6 + Math.random() * 6}px`, c: COLORS[i % COLORS.length],
    })));
    const id = setTimeout(() => setBits([]), 5000);
    return () => clearTimeout(id);
  }, [fire]);
  if (!bits.length) return null;
  return (
    <div className="fx-confetti" aria-hidden="true">
      {bits.map((b) => <i key={b.id} className="fx-bit" style={{ "--x": b.x, "--dx": b.dx, "--rot": b.rot, "--delay": b.delay, "--d": b.d, "--w": b.w, "--c": b.c }} />)}
    </div>
  );
}