import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ChevronLeft, Loader2, Smartphone, X } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { STEPS } from "@/constants/studio";
import StepIdea from "@/studio/StepIdea";
import StepScript from "@/studio/StepScript";
import StepStyle from "@/studio/StepStyle";
import StepScenes from "@/studio/StepScenes";
import StepAudio from "@/studio/StepAudio";
import StepRender from "@/studio/StepRender";
import { useLocale } from "@/context/LocaleContext";
import StudioStepper from "@/components/StudioStepper";
import LivePreview, { ramStatus } from "@/components/LivePreview";
import { Confetti } from "@/components/fx";
import { ProjectCopyProvider } from "@/context/ProjectCopyContext";

const VIEWS = { 1: StepIdea, 2: StepScript, 3: StepStyle, 4: StepScenes, 5: StepAudio, 6: StepRender };

/* Storyboard strip: every scene as a tiny poster, click to jump to the scene editor */
function Filmstrip({ project, onOpen }) {
  const scenes = project.scenes || [];
  if (!scenes.length) return null;
  return (
    <div className="film" data-testid="studio-filmstrip">
      <span className="film-label">Storyboard</span>
      {scenes.map((s, i) => (
        <button key={s.id || i} type="button" className="film-item" onClick={onOpen} aria-label={`Open scene ${i + 1}`}>
          {s.image_path ? <img src={mediaUrl(s.image_path)} alt="" loading="lazy" /> : <span className="fx-shimmer" />}
        </button>
      ))}
    </div>
  );
}

export default function Studio() {
  const { id } = useParams();
  const { t, changeLocale } = useLocale();
  const [project, setProject] = useState(null);
  const [view, setView] = useState(1);
  const [hasEdits, setHasEdits] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [syncError, setSyncError] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [fire, setFire] = useState(0);
  const prevRender = useRef(null);
  const revision = useRef(0);
  const requestSequence = useRef(0);

  const canLeave = () => !hasEdits || window.confirm("Some changes on this step may not be saved. Leave this step?");
  const navigateStep = (next) => {
    if (next === view || !canLeave()) return;
    setHasEdits(false);
    setView(next);
  };

  const load = useCallback(async (jump) => {
    const startedAtRevision = revision.current;
    const request = ++requestSequence.current;
    try {
      const { data } = await api.get(`/projects/${id}`, { timeout: 15000 });
      if (request !== requestSequence.current || startedAtRevision !== revision.current) return;
      setProject(data);
      setLoadError("");
      setSyncError(false);
      if (jump) setView(VIEWS[data.step] ? data.step : 1);
    } catch (e) {
      if (request !== requestSequence.current || startedAtRevision !== revision.current) return;
      if (jump) setLoadError(errMsg(e));
      else setSyncError(true);
    }
  }, [id]);

  useEffect(() => { load(true); return () => { requestSequence.current += 1; }; }, [load]);
  useEffect(() => { if (project?.language) changeLocale(project.language); }, [project?.language, changeLocale]);

  const busy = project && (project.scenes?.some((s) => s.status === "generating" || s.status === "queued") || project.render?.status === "rendering");
  const hasProject = Boolean(project);
  useEffect(() => {
    if (!hasProject) return undefined;
    let stopped = false;
    let inFlight = false;
    let timer;
    const poll = async () => {
      if (stopped || inFlight) return;
      inFlight = true;
      if (!document.hidden) await load(false);
      inFlight = false;
      if (!stopped) timer = setTimeout(poll, document.hidden || !busy ? 15000 : 3000);
    };
    const reconnect = () => { if (!document.hidden) { clearTimeout(timer); poll(); } };
    timer = setTimeout(poll, busy ? 3000 : 15000);
    window.addEventListener("online", reconnect);
    document.addEventListener("visibilitychange", reconnect);
    return () => {
      stopped = true; clearTimeout(timer);
      window.removeEventListener("online", reconnect);
      document.removeEventListener("visibilitychange", reconnect);
    };
  }, [busy, load, hasProject]);

  // Celebrate the moment a render finishes
  const renderStatus = project?.render?.status;
  useEffect(() => {
    if (prevRender.current === "rendering" && renderStatus === "done") {
      setFire((f) => f + 1);
      toast.success(t("Your video is ready! 🎉"));
    }
    prevRender.current = renderStatus;
  }, [renderStatus]);

  if (!project && loadError) return <div role="alert" className="py-16 space-y-4">
    <p>{loadError}</p>
    <button className="btn-primary" onClick={() => load(true)}> {t("Try again")} </button>
    <Link to="/dashboard" className="block underline"> {t("Back to my videos")} </Link>
  </div>;
  if (!project) return <div className="py-24 grid place-items-center"><Loader2 className="animate-spin text-rose-400" /></div>;

  const update = (p, next) => { revision.current += 1; setProject(p); setSyncError(false); setHasEdits(false); if (next) setView(next); };
  const View = VIEWS[view];
  const { state: ramState } = ramStatus(project, view);
  return (
    <div>

      <Confetti fire={fire} />
      {syncError && <p role="status" className="mb-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">{t("Connection interrupted. Reconnecting to your saved project…")}</p>}
      {view !== 6 && project.render?.status === "rendering" && <div role="status" aria-live="polite" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#c4d8c9] bg-[#f5f9f4] p-3 text-sm text-[#263b36]">
        <span>Rendering your video · {Math.round(Number(project.render.progress) || 0)}% · {project.render.message || "Preparing your video"}</span>
        <button type="button" onClick={() => navigateStep(6)} className="font-semibold underline">View progress</button>
      </div>}
      {view !== 6 && project.render?.status === "done" && project.render.video_path && <div role="status" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900">
        <span>Your video is ready to watch and download.</span>
        <button type="button" onClick={() => navigateStep(6)} className="font-semibold underline">Open video</button>
      </div>}
      <div className="flex items-center gap-3 text-sm text-[#7b7083] mb-4">
        <Link to="/dashboard" onClick={(e) => { if (!canLeave()) e.preventDefault(); }} data-testid="studio-back-link" className="flex items-center gap-1 hover:text-[#a23f58]"><ChevronLeft size={16} />{t("my_videos")}</Link>
        <span>/</span>
        <span className="text-[#4a3f58] font-semibold truncate indic" data-testid="studio-project-title">{project.script?.title || project.title}</span>
      </div>
      <StudioStepper view={view} maxStep={project.step} setView={navigateStep} ramState={ramState} />
      {view !== 4 && <Filmstrip project={project} onOpen={() => navigateStep(4)} />}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        {view > 1 ? <button data-testid="studio-previous-step" onClick={() => navigateStep(view - 1)} className="inline-flex items-center gap-2 rounded-full border border-[#ecd9d3] bg-white px-5 py-3 text-sm text-[#4a3f58] hover:bg-[#fdf1ee] transition-colors">
          <ChevronLeft size={18} />{t(`step_${view - 1}_label`)}
        </button> : <Link to="/dashboard" onClick={(e) => { if (!canLeave()) e.preventDefault(); }} className="inline-flex items-center gap-2 rounded-full border border-[#ecd9d3] bg-white px-5 py-3 text-sm text-[#4a3f58]"><ChevronLeft size={18} /> {t("Back to my videos")} </Link>}
        <span className="text-sm text-[#7b7083]" aria-live="polite">{hasEdits ? "Changes on this step" : `${t("step")} ${view} / ${STEPS.length}`}</span>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div key={`${id}-${view}`} className="min-w-0 rise" onChangeCapture={() => setHasEdits(true)}>
          <ProjectCopyProvider project={project} enabled={view === 2 || view === 4}>
            <View project={project} update={update} reload={() => load(false)} />
          </ProjectCopyProvider>
        </div>
        <aside className="hidden xl:block sticky top-6 self-start"><LivePreview project={project} view={view} /></aside>
      </div>

      <button type="button" onClick={() => setPreviewOpen(true)} data-testid="open-live-preview"
        className="xl:hidden fixed bottom-4 right-4 z-40 inline-flex items-center gap-2 rounded-full bg-[#922b46] px-5 py-3 text-sm font-bold text-white shadow-xl shadow-rose-300/50">
        <Smartphone size={16} /> {t("Live preview")} </button>
      {previewOpen && (
        <div className="xl:hidden fixed inset-0 z-50 grid place-items-end bg-[#8c5a6e]/30 backdrop-blur-sm" onClick={() => setPreviewOpen(false)}>
          <div className="w-full max-w-sm mx-auto p-4 rise" onClick={(e) => e.stopPropagation()}>
            <div className="relative"><button type="button" aria-label={t("Close preview")} onClick={() => setPreviewOpen(false)} className="absolute right-3 top-3 z-10 grid h-8 w-8 place-items-center rounded-full bg-white text-[#a23f58] shadow"><X size={16} /></button>
              <LivePreview project={project} view={view} /></div>
          </div>
        </div>
      )}
    </div>
  );
}
