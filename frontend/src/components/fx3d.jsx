/**
 * fx3d — a small, dependency-light 3D motion kit for the BharatKatha UI.
 *
 * Every component here:
 *   - animates only transform / opacity (GPU friendly, no layout thrash),
 *   - honours `prefers-reduced-motion` by rendering a static fallback,
 *   - keeps its own perspective context so 3D depth never leaks to siblings,
 *   - never introduces horizontal page overflow.
 *
 * All colour comes from the surrounding theme (cream / rose / marigold /
 * sage) — there is deliberately no black in this layer.
 */
import { useEffect, useRef, useState } from "react";
import {
  animate,
  motion,
  useInView,
  useMotionValue,
  useMotionValueEvent,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import "./fx3d.css";

const EASE = [0.22, 0.7, 0.2, 1];
const wrapIndex = (v, n) => ((v % n) + n) % n;

/** Wraps children in a fresh 3D perspective context. */
export function Stage3D({ children, className = "", perspective = 1200, origin = "50% 45%", style, ...rest }) {
  return (
    <div
      className={`fx3d-stage ${className}`}
      style={{ perspective, perspectiveOrigin: origin, ...style }}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Tilt3D — pointer-driven 3D rotation with a moving specular glare. */
export function Tilt3D({ children, className = "", max = 12, scale = 1.03, glare = true, style, ...rest }) {
  const reduce = useReducedMotion();
  const rx = useSpring(0, { stiffness: 170, damping: 16, mass: 0.5 });
  const ry = useSpring(0, { stiffness: 170, damping: 16, mass: 0.5 });
  const gx = useSpring(50, { stiffness: 130, damping: 20 });
  const gy = useSpring(50, { stiffness: 130, damping: 20 });
  const glareBg = useTransform(
    [gx, gy],
    ([x, y]) => `radial-gradient(320px circle at ${x}% ${y}%, rgba(255,255,255,.5), rgba(255,255,255,0) 62%)`
  );

  const onPointerMove = (e) => {
    if (reduce) return;
    const r = e.currentTarget.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    ry.set(px * max * 2);
    rx.set(-py * max * 2);
    gx.set((px + 0.5) * 100);
    gy.set((py + 0.5) * 100);
  };
  const reset = () => { rx.set(0); ry.set(0); gx.set(50); gy.set(50); };

  return (
    <motion.div
      className={`fx3d-tilt ${className}`}
      onPointerMove={onPointerMove}
      onPointerLeave={reset}
      onPointerCancel={reset}
      style={{ ...style, rotateX: reduce ? 0 : rx, rotateY: reduce ? 0 : ry, transformStyle: "preserve-3d" }}
      whileHover={reduce ? undefined : { scale }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}
      {...rest}
    >
      {children}
      {glare && !reduce ? <motion.span className="fx3d-glare" aria-hidden style={{ background: glareBg }} /> : null}
    </motion.div>
  );
}

/** Idle 3D float — a slow bob + subtle roll so hero art never sits dead still. */
export function Float3D({ children, className = "", y = 12, rotate = 2, tiltY = 0, duration = 7, delay = 0 }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      animate={{
        y: [0, -y, 0],
        rotateZ: [rotate, -rotate, rotate],
        ...(tiltY ? { rotateY: [tiltY, -tiltY, tiltY] } : {}),
      }}
      transition={{ duration, delay, repeat: Infinity, ease: "easeInOut" }}
      style={{ transformStyle: "preserve-3d" }}
    >
      {children}
    </motion.div>
  );
}

/** Scroll-triggered 3D entrance (rotate up into place, once). */
export function Reveal3D({ children, className = "", delay = 0, y = 26, rotate = 7 }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y, rotateX: rotate }}
      whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
      viewport={{ once: true, amount: 0.25 }}
      transition={{ duration: 0.7, delay, ease: EASE }}
      style={{ transformPerspective: 1000 }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Mount-based 3D entrance for ABOVE-THE-FOLD content.
 *
 * Deliberately does not use `whileInView`: hero copy must be visible even if
 * IntersectionObserver never fires (headless renderers, prerenderers, old
 * browsers, or a slow observer). It animates immediately on mount instead.
 */
export function RevealIn({ children, className = "", delay = 0, y = 24, rotate = 8 }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y, rotateX: rotate }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ duration: 0.75, delay, ease: EASE }}
      style={{ transformPerspective: 1000 }}
    >
      {children}
    </motion.div>
  );
}

/** Window-pointer parallax. `depth` = px of travel at the extremes. */export function Parallax3D({ children, className = "", depth = 20, style, ...rest }) {
  const reduce = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 80, damping: 20, mass: 0.6 });
  const sy = useSpring(y, { stiffness: 80, damping: 20, mass: 0.6 });
  const tx = useTransform(sx, (v) => v * depth);
  const ty = useTransform(sy, (v) => v * depth);

  useEffect(() => {
    if (reduce) return undefined;
    const onMove = (e) => {
      x.set((e.clientX / window.innerWidth - 0.5) * 2);
      y.set((e.clientY / window.innerHeight - 0.5) * 2);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [reduce, x, y]);

  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={`fx3d-layer ${className}`}
      style={{ ...style, x: tx, y: ty, transformStyle: "preserve-3d" }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/** Tap/click (and optional hover) 3D flip card. */
export function Flip3D({ front, back, className = "", height = 260, flipped, onFlip, duration = 0.8 }) {
  const reduce = useReducedMotion();
  const [internal, setInternal] = useState(false);
  const isControlled = flipped !== undefined;
  const open = isControlled ? flipped : internal;
  const toggle = () => {
    if (isControlled) onFlip?.(!open);
    else setInternal((v) => !v);
  };
  return (
    <div
      className={`fx3d-flip ${className}`}
      style={{ height }}
      role="button"
      tabIndex={0}
      aria-pressed={open}
      onClick={toggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle();
        }
      }}
    >
      <motion.div
        className="fx3d-flip-inner"
        style={{ transformStyle: "preserve-3d" }}
        animate={{ rotateY: open ? 180 : 0 }}
        transition={{ duration: reduce ? 0 : duration, ease: EASE }}
      >
        <div className="fx3d-face fx3d-face--front">{front}</div>
        <div className="fx3d-face fx3d-face--back">{back}</div>
      </motion.div>
    </div>
  );
}

/** Animated number that counts up when it enters the viewport. */
export function Counter({ value = 0, duration = 1.1, className = "" }) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(0);
  const [shown, setShown] = useState(0);
  useMotionValueEvent(mv, "change", (v) => setShown(Math.round(v)));
  useEffect(() => {
    if (reduce) { setShown(value); return undefined; }
    const controls = animate(mv, Number(value) || 0, { duration, ease: "easeOut" });
    return () => controls.stop();
  }, [value, duration, reduce, mv]);
  return <span className={className}>{shown}</span>;
}

/* One coverflow card. A component (not an inline map body) so the transform
   hooks are called at the top level of a component, per the rules of hooks. */
function CoverflowItem({ item, index, pos, n, step, active, onSelect, isDragging }) {
  const off = useTransform(pos, (p) => wrapIndex(index - p + n / 2, n) - n / 2);
  const x = useTransform(off, (d) => d * step);
  const z = useTransform(off, (d) => -Math.abs(d) * 150);
  const rotateY = useTransform(off, (d) => -d * 24);
  const scale = useTransform(off, (d) => Math.max(0.62, 1 - Math.abs(d) * 0.085));
  const opacity = useTransform(off, (d) => Math.min(1, Math.max(0, 1 - (Math.abs(d) - 1.6) * 1.1)));
  return (
    <motion.figure className="fx3d-cf-item" style={{ x, z, rotateY, scale, opacity }}>
      <button
        type="button"
        onClick={() => { if (!isDragging.current.active) onSelect(index); }}
        aria-label={`Show ${item.label} style`}
        aria-current={active ? "true" : undefined}
        tabIndex={active ? 0 : -1}
      >
        <span className="fx3d-cf-card">
          <img src={`/styles/${item.id}.jpg`} alt="" loading="lazy" width="200" height="250" draggable="false" />
          <figcaption>{item.label}</figcaption>
        </span>
      </button>
    </motion.figure>
  );
}

/**
 * Coverflow3D — an interactive 3D carousel.
 *
 * Interaction (all contained, never scrolls the page sideways):
 *   - drag with mouse or finger (with momentum + snap),
 *   - horizontal trackpad / wheel / shift+wheel,
 *   - left/right arrow buttons and ← / → keys,
 *   - auto-rotates when idle unless `paused`.
 */
export function Coverflow3D({ items, paused = false, interval = 3600, className = "", onActiveChange, label = "Story styles" }) {
  const reduce = useReducedMotion();
  const n = items.length;
  const trackRef = useRef(null);
  const wheelTimer = useRef(null);
  const [width, setWidth] = useState(1120);
  const inView = useInView(trackRef, { amount: 0.25 });

  const pos = useMotionValue(0);          // continuous index; frank motion value
  const posRef = useRef(0);
  const drag = useRef({ active: false, startX: 0, startPos: 0, lastX: 0, lastT: 0, v: 0 });
  const [active, setActive] = useState(0);
  const [grabbing, setGrabbing] = useState(false);

  useMotionValueEvent(pos, "change", (v) => {
    posRef.current = v;
    const i = wrapIndex(Math.round(v), n);
    setActive((prev) => (prev === i ? prev : i));
  });
  useEffect(() => { onActiveChange?.(active); }, [active, onActiveChange]);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return undefined;
    const measure = () => setWidth(el.getBoundingClientRect().width || 1120);
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const step = Math.max(74, Math.min(132, width * 0.2));
  const glide = (to, stiffness = 110) =>
    animate(pos, to, { type: "spring", stiffness, damping: 22, mass: 0.9 });

  const snapTo = (i) => {
    const cur = posRef.current;
    const delta = wrapIndex(i - cur, n);
    const base = Math.round(cur) + delta;
    glide(base);
  };
  const move = (d) => glide(Math.round(posRef.current) + d);
  const settle = () => {
    const v = drag.current.v;
    let target = Math.round(posRef.current);
    if (Math.abs(v) > 0.4) target = Math.round(posRef.current + Math.sign(v) * 1.15);
    glide(target, 90);
  };

  // idle auto-rotation
  useEffect(() => {
    if (paused || reduce || !inView || n < 2) return undefined;
    const t = setInterval(() => {
      if (document.hidden || drag.current.active) return;
      glide(Math.round(posRef.current) + 1);
    }, interval);
    return () => clearInterval(t);
  }, [paused, reduce, inView, interval, n]);

  const onPointerDown = (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    drag.current = { active: true, startX: e.clientX, startPos: posRef.current, lastX: e.clientX, lastT: performance.now(), v: 0 };
    setGrabbing(true);
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* ignore */ }
  };
  const onPointerMove = (e) => {
    const d = drag.current;
    if (!d.active) return;
    const now = performance.now();
    d.v = (e.clientX - d.lastX) / Math.max(1, now - d.lastT);
    d.lastX = e.clientX; d.lastT = now;
    pos.set(d.startPos - (e.clientX - d.startX) / step);
  };
  const endDrag = (e) => {
    if (!drag.current.active) return;
    drag.current.active = false;
    setGrabbing(false);
    try { e?.currentTarget?.releasePointerCapture?.(e.pointerId); } catch { /* ignore */ }
    settle();
  };
  const onWheel = (e) => {
    const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : 0;
    if (!d) return;                       // let vertical page scroll pass through
    e.preventDefault();
    pos.set(posRef.current + d / (step * 1.8));
    clearTimeout(wheelTimer.current);
    wheelTimer.current = setTimeout(settle, 150);
  };
  const onKeyDown = (e) => {
    if (e.key === "ArrowLeft") { e.preventDefault(); move(-1); }
    if (e.key === "ArrowRight") { e.preventDefault(); move(1); }
  };

  return (
    <div className={`fx3d-cf ${className}`}>
      <div
        className={`fx3d-cf-track ${grabbing ? "is-grabbing" : ""}`}
        ref={trackRef}
        role="group"
        aria-roledescription="carousel"
        aria-label={label}
        tabIndex={0}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={endDrag}
        onWheel={onWheel}
        onKeyDown={onKeyDown}
      >
        {items.map((it, i) => (
          <CoverflowItem
            key={it.id}
            item={it}
            index={i}
            pos={pos}
            n={n}
            step={step}
            active={i === active}
            onSelect={snapTo}
            isDragging={drag}
          />
        ))}
      </div>
      <div className="fx3d-cf-nav">
        <div className="fx3d-cf-dots">
          {items.map((it, i) => (
            <button
              key={it.id}
              type="button"
              className={`fx3d-cf-dot ${i === active ? "on" : ""}`}
              onClick={() => snapTo(i)}
              aria-label={it.label}
              aria-current={i === active ? "true" : undefined}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/** Decorative warm gradient haze. Purely presentational. */
export function Aurora({ className = "" }) {
  return (
    <div className={`fx3d-aurora ${className}`} aria-hidden>
      <i /><i /><i /><i />
    </div>
  );
}

/**
 * FilmFloor — a receding plane of story frames and reel sprocket holes that
 * slowly rolls past. Our on-concept stand-in for a generic perspective grid.
 * Decorative only: absolutely positioned, pointer-events none.
 */
export function FilmFloor({ className = "" }) {
  return (
    <div className={`fx3d-filmfloor ${className}`} aria-hidden>
      <i /><i />
    </div>
  );
}
