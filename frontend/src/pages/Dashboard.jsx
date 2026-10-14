import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Film, Trash2, Clock, Sparkles, ArrowRight, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useNewProject } from "@/components/AppShell";
import { STYLES } from "@/constants/studio";
import { useLocale } from "@/context/LocaleContext";
import { CursorGlow, Magnetic, RamAvatar, reducedMotion, usePointerVars } from "@/components/fx";
import "./Dashboard.css";

const IDEAS = [
  { en: "The diya that never went out", te: "ఆరిపోని దీపం" },
  { en: "A talking cow teaches honesty", te: "నిజం చెప్పే ఆవు" },
  { en: "The little sparrow and the big storm", te: "చిన్న పిచ్చుక, పెద్ద తుఫాను" },
  { en: "Why we light lamps in Karthika Masam", te: "కార్తీక మాసంలో దీపాలు ఎందుకు?" },
  { en: "The clever crow who solved a drought", te: "తెలివైన కాకి" },
  { en: "A grandmother's magic pot", te: "అమ్మమ్మ మాయ కుండ" },
  { en: "The farmer and the golden seed", te: "రైతు, బంగారు విత్తనం" },
  { en: "A boy who returned a lost letter", te: "పోయిన ఉత్తరం" },
];

/* 3D tilt toward the cursor + glare */
function useTilt(max = 8) {
  const ref = useRef(null);
  const onPointerMove = (e) => {
    const el = ref.current;
    if (!el || reducedMotion() || e.pointerType === "touch") return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    el.style.setProperty("--rx", `${((0.5 - py) * max * 2).toFixed(2)}deg`);
    el.style.setProperty("--ry", `${((px - 0.5) * max * 2).toFixed(2)}deg`);
    el.style.setProperty("--gx", `${(px * 100).toFixed(1)}%`);
    el.style.setProperty("--gy", `${(py * 100).toFixed(1)}%`);
    el.classList.add("is-tilting");
  };
  const reset = () => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
    el.classList.remove("is-tilting");
  };
  return { ref, onPointerMove, reset };
}

/* 9:16 poster. Hover (or focus) plays a story-style preview of the project's scenes. */
function PosterCard({ p, onDelete, index }) {
  const { t } = useLocale();
  const nav = useNavigate();
  const tilt = useTilt(8);
  const slides = (p.scenes || []).filter((s) => s.image_path).map((s) => mediaUrl(s.image_path));
  const [i, setI] = useState(0);
  const [play, setPlay] = useState(false);
  const done = p.render?.status === "done";

  useEffect(() => {
    if (!play || slides.length < 2) { setI(0); return undefined; }
    const id = setInterval(() => setI((v) => (v + 1) % slides.length), 1100);
    return () => clearInterval(id);
  }, [play, slides.length]);

  // Shared-element transition: the poster morphs into the studio's live preview
  const open = (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0 || !document.startViewTransition || reducedMotion()) return;
    e.preventDefault();
    tilt.ref.current.style.viewTransitionName = `proj-${p.id}`;
    document.startViewTransition(() => { flushSync(() => nav(`/studio/${p.id}`)); });
  };

  return (
    <div className="dash-slot dash-rise" style={{ "--i": index }}>
      <div ref={tilt.ref} className="poster" data-testid={`project-card-${p.id}`}
        onPointerMove={tilt.onPointerMove}
        onPointerEnter={() => setPlay(true)}
        onPointerLeave={() => { tilt.reset(); setPlay(false); }}
        onFocus={() => setPlay(true)} onBlur={() => setPlay(false)}>
        <span className="dash-glare" aria-hidden="true" />
        {slides.length ? slides.map((src, k) => <img key={src} src={src} alt="" className={`poster-img ${k === i ? "on" : ""} ${play && k === i ? "fx-kb" : ""}`} loading="lazy" />)
          : <img src={`/styles/${p.style || "storybook"}.jpg`} alt="" className="poster-img on poster-empty" />}
        <div className="poster-shade" />
        {play && slides.length > 1 && (
          <div className="poster-bars" aria-hidden="true">{slides.map((_, k) => <span key={k}><i className={k < i ? "full" : k === i ? "run" : ""} /></span>)}</div>
        )}
        <span className={`dash-badge ${done ? "dash-badge-done" : ""}`}>
          {done ? t("videos_ready") : `${t("step")} ${p.step} · ${t(`step_${p.step}_label`)}`}
        </span>
        <div className="poster-info">
          <div className="poster-title indic">{p.script?.title || p.title}</div>
          <div className="poster-meta"><span className="uppercase font-mono">{p.language}</span>·<span>{STYLES.find((s) => s.id === p.style)?.label || "—"}</span></div>
          <div className="poster-meta"><Clock size={11} />{new Date(p.updated_at).toLocaleDateString()}</div>
        </div>
        <Link to={`/studio/${p.id}`} onClick={open} className="poster-link" aria-label={`Open ${p.script?.title || p.title}`} />
        <button data-testid={`delete-project-${p.id}`} aria-label="Delete project" onClick={() => onDelete(p.id)} className="poster-delete"><Trash2 size={14} /></button>
      </div>
    </div>
  );
}

function ResumeCard({ p, index }) {
  const { t } = useLocale();
  const thumb = p.scenes?.find((s) => s.image_path)?.image_path;
  const pct = Math.round(((p.step || 1) / 6) * 100);
  return (
    <div className="duo-card duo-resume dash-rise" style={{ "--i": index }} data-testid="resume-card">
      <div className="duo-thumb">{thumb ? <img src={mediaUrl(thumb)} alt="" /> : <img src={`/styles/${p.style || "storybook"}.jpg`} alt="" className="poster-empty" />}</div>
      <div className="min-w-0 flex-1">
        <div className="duo-kicker">Continue where you left off</div>
        <div className="duo-title indic truncate">{p.script?.title || p.title}</div>
        <div className="mt-1 text-xs text-[#7b7083]">{t("step")} {p.step} · {t(`step_${p.step}_label`)}</div>
        <div className="lp-bar mt-3"><i style={{ width: `${pct}%` }} /></div>
        <div className="mt-4"><Magnetic strength={0.25}><Link to={`/studio/${p.id}`} className="dash-cta dash-cta-sm">Continue <ArrowRight size={15} /></Link></Magnetic></div>
      </div>
    </div>
  );
}

function IdeaCard({ index }) {
  const newProject = useNewProject();
  const [k, setK] = useState(() => Math.floor(Date.now() / 864e5) % IDEAS.length);
  const idea = IDEAS[k];
  const festive = [9, 10].includes(new Date().getMonth());
  const use = async () => {
    try { await navigator.clipboard?.writeText(`${idea.en} — ${idea.te}`); toast.success("Idea copied — paste it into Step 1"); } catch { /* clipboard blocked */ }
    newProject();
  };
  return (
    <div className="duo-card duo-idea dash-rise" style={{ "--i": index }} data-testid="idea-card">
      <RamAvatar state="thinking" size={46} />
      <div className="min-w-0 flex-1">
        <div className="duo-kicker">{festive ? "Festival season · Diwali & Karthika Masam" : "Ram AI's idea of the day"}</div>
        <div key={k} className="duo-title fx-morph">{idea.en}</div>
        <div key={`t${k}`} className="indic text-sm text-[#7b7083] fx-morph">{idea.te}</div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Magnetic strength={0.25}><button type="button" onClick={use} className="dash-cta dash-cta-sm"><Sparkles size={15} /> Use this idea</button></Magnetic>
          <button type="button" onClick={() => setK((v) => (v + 1) % IDEAS.length)} className="dash-ghost"><RefreshCw size={14} /> Another</button>
        </div>
      </div>
    </div>
  );
}

function Stat({ k, v, label, i }) {
  const tilt = useTilt(10);
  return (
    <div className="dash-slot dash-rise" style={{ "--i": i }}>
      <div ref={tilt.ref} onPointerMove={tilt.onPointerMove} onPointerLeave={tilt.reset} className="dash-stat">
        <span className="dash-glare" aria-hidden="true" />
        <div className="text-xs text-[#7b7083]">{label}</div>
        <div className="text-xl font-bold capitalize text-[#4a3f58]" data-testid={`stat-${k.replace("_", "-")}`}>{v}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const { t } = useLocale();
  const [items, setItems] = useState(null);
  const [loadError, setLoadError] = useState("");
  const newProject = useNewProject();
  const heroRef = useRef(null);
  usePointerVars(heroRef);
  const load = () => api.get("/projects")
    .then((r) => { setItems(r.data); setLoadError(""); })
    .catch((e) => setLoadError(errMsg(e)));
  useEffect(() => { load(); }, []);
  const del = async (id) => {
    if (!window.confirm("Delete this project?")) return;
    await api.delete(`/projects/${id}`); load();
  };
  const ready = items?.filter((p) => p.render?.status === "done").length || 0;
  const resume = items?.length ? ([...items].filter((p) => p.render?.status !== "done").sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))[0] || items[0]) : null;
  const stats = [["projects", items?.length ?? "–"], ["videos_ready", ready], ["plan", user?.plan]];

  return (
    <div className="dash-page">
      <CursorGlow />
      <div ref={heroRef} className="dash-hero dash-rise" style={{ "--i": 0 }}>
        <span className="dash-orb dash-orb-1" aria-hidden="true" />
        <span className="dash-orb dash-orb-2" aria-hidden="true" />
        <span className="dash-orb dash-orb-3" aria-hidden="true" />
        <div className="dash-hero-text">
          <p className="text-sm font-semibold text-[#a23f58] flex items-center gap-1.5"><Sparkles size={14} />{t("dashboard_greeting")}, {user?.name?.split(" ")[0]}</p>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-[#4a3f58]">{t("my_videos")}</h1>
          <p className="mt-1 text-sm text-[#7b6a73]">{t("create_video")}</p>
        </div>
        <Magnetic><button data-testid="dashboard-new-video-btn" onClick={newProject} className="dash-cta"><Plus size={16} /> {t("create_video")}</button></Magnetic>
      </div>

      <div className={`dash-duo mt-5 ${resume ? "" : "dash-duo-one"}`}>
        {resume && <ResumeCard p={resume} index={1} />}
        <IdeaCard index={2} />
      </div>

      <div className="mt-5 grid grid-cols-3 max-w-xl gap-2 sm:gap-3 dash-persp">
        {stats.map(([k, v], i) => <Stat key={k} k={k} v={v} label={t(k)} i={i + 3} />)}
      </div>

      {loadError && <div role="alert" className="mt-6 rounded-xl bg-rose-100 p-4 text-sm text-rose-800">
        {loadError} <button onClick={load} className="ml-2 font-semibold underline">Try again</button>
      </div>}

      {items && items.length === 0 && (
        <div className="dash-empty dash-rise" style={{ "--i": 5 }} data-testid="empty-projects">
          <div className="dash-empty-icon"><Film size={34} /></div>
          <p className="mt-4 font-semibold text-[#4a3f58]">{t("no_videos")}</p>
          <p className="text-sm text-[#7b7083]">{t("create_video")}</p>
          <button onClick={newProject} data-testid="empty-new-video-btn" className="dash-cta mt-5">{t("create_video")}</button>
        </div>
      )}

      {items && items.length > 0 && <h2 className="mt-9 text-lg font-extrabold tracking-tight text-[#4a3f58]">All your videos <span className="text-sm font-semibold text-[#9a8a95]">· hover a poster to preview</span></h2>}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-5 dash-persp">
        {items?.map((p, i) => <PosterCard key={p.id} p={p} onDelete={del} index={i + 5} />)}
      </div>
    </div>
  );
}