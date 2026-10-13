import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ChevronLeft, Check, Loader2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { STEPS } from "@/constants/studio";
import StepIdea from "@/studio/StepIdea";
import StepScript from "@/studio/StepScript";
import StepStyle from "@/studio/StepStyle";
import StepScenes from "@/studio/StepScenes";
import StepAudio from "@/studio/StepAudio";
import StepRender from "@/studio/StepRender";
import { useLocale } from "@/context/LocaleContext";

const VIEWS = { 1: StepIdea, 2: StepScript, 3: StepStyle, 4: StepScenes, 5: StepAudio, 6: StepRender };

function Stepper({ view, maxStep, setView }) {
  const { t } = useLocale();
  return (
    <ol className="flex items-center gap-1 overflow-x-auto pb-1" data-testid="studio-stepper">
      {STEPS.map((s, i) => {
        const allowed = s.n <= maxStep;
        const active = s.n === view;
        const label = t(`step_${s.n}_label`) || s.label;
        return (
          <li key={s.n} className="flex items-center gap-1 shrink-0">
            <button data-testid={`stepper-step-${s.n}`} disabled={!allowed} onClick={() => setView(s.n)}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold transition-colors ${active ? "bg-rose-200 text-[#312532] shadow-lg shadow-rose-900/20" : allowed ? "text-slate-200 hover:bg-white/10" : "text-slate-400"}`}>
              <span className={`h-5 w-5 rounded-full grid place-items-center text-[11px] ${active ? "bg-[#A33D52] text-white" : s.n < maxStep ? "bg-[#A33D52] text-white" : "bg-[#65546B] text-slate-200"}`}>
                {s.n < maxStep && !active ? <Check size={12} /> : s.n}
              </span>
              {label}
            </button>
            {i < STEPS.length - 1 && <span className="w-4 h-px bg-[#65546B]" />}
          </li>
        );
      })}
    </ol>
  );
}

export default function Studio() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [view, setView] = useState(1);
  const [hasEdits, setHasEdits] = useState(false);
  const [loadError, setLoadError] = useState("");

  const canLeave = () => !hasEdits || window.confirm("Some changes on this step may not be saved. Leave this step?");
  const navigateStep = (next) => {
    if (next === view || !canLeave()) return;
    setHasEdits(false);
    setView(next);
  };

  const load = useCallback(async (jump) => {
    try {
      const { data } = await api.get(`/projects/${id}`);
      setProject(data);
      setLoadError("");
      if (jump) setView(VIEWS[data.step] ? data.step : 1);
    } catch (e) {
      if (jump) setLoadError(errMsg(e));
    }
  }, [id]);

  useEffect(() => { load(true); }, [load]);

  const busy = project && (project.scenes?.some((s) => s.status === "generating" || s.status === "queued") || project.render?.status === "rendering");
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => load(false), 3000);
    return () => clearInterval(t);
  }, [busy, load]);

  if (!project && loadError) return <div role="alert" className="py-16 space-y-4">
    <p>{loadError}</p>
    <button className="btn-primary" onClick={() => load(true)}>Try again</button>
    <Link to="/dashboard" className="block underline">Back to my videos</Link>
  </div>;
  if (!project) return <div className="py-24 grid place-items-center"><Loader2 className="animate-spin text-violet-400" /></div>;

  const update = (p, next) => { setProject(p); setHasEdits(false); if (next) setView(next); };
  const View = VIEWS[view];
  return (
    <div>
      <div className="flex items-center gap-3 text-sm text-slate-300 mb-4">
        <Link to="/dashboard" onClick={(e) => { if (!canLeave()) e.preventDefault(); }} data-testid="studio-back-link" className="flex items-center gap-1 hover:text-white"><ChevronLeft size={16} />My videos</Link>
        <span>/</span>
        <span className="text-white font-semibold truncate indic" data-testid="studio-project-title">{project.script?.title || project.title}</span>
      </div>
      <Stepper view={view} maxStep={project.step} setView={navigateStep} />
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        {view > 1 ? <button data-testid="studio-previous-step" onClick={() => navigateStep(view - 1)} className="inline-flex items-center gap-2 rounded-full border border-slate-600 px-5 py-3 text-sm text-white hover:bg-white/10">
          <ChevronLeft size={18} />Back to {STEPS[view - 2].label}
        </button> : <Link to="/dashboard" onClick={(e) => { if (!canLeave()) e.preventDefault(); }} className="inline-flex items-center gap-2 rounded-full border border-slate-600 px-5 py-3 text-sm text-white"><ChevronLeft size={18} />Back to my videos</Link>}
        <span className="text-sm text-slate-300" aria-live="polite">{hasEdits ? "Changes on this step" : `Step ${view} of ${STEPS.length}`}</span>
      </div>
      <div className="mt-6" key={`${id}-${view}`} onChangeCapture={() => setHasEdits(true)}>
        <View project={project} update={update} reload={() => load(false)} />
      </div>
    </div>
  );
}
