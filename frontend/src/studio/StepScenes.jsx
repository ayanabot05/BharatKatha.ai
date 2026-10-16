import { useEffect, useRef, useState } from "react";
import { Loader2, RefreshCw, Wand2, ArrowRight, AlertTriangle, ImageIcon, Trash2, Plus, Save, CheckCircle2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { StepHeader } from "@/components/StepHeader";
import { useLocale } from "@/context/LocaleContext";
import { useProjectCopy } from "@/context/ProjectCopyContext";

function SceneCard({ s, i, project, update, approveScene, approvingId, approveError, generationActive }) {
  const { t } = useLocale();
  const { display, pending } = useProjectCopy();
  const [instr, setInstr] = useState("");
  const [narration, setNarration] = useState(s.narration);
  const [visual, setVisual] = useState(s.visual);
  const [saving, setSaving] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const requestLock = useRef(false);
  useEffect(() => { setNarration(s.narration); }, [s.narration]);
  useEffect(() => { setVisual(s.visual); }, [s.visual]);
  const generating = s.status === "generating";
  const queued = s.status === "queued";
  const batchActive = requesting || generationActive || generating || queued;
  const run = async (instruction) => {
    if (requestLock.current || batchActive) return;
    requestLock.current = true;
    setRequesting(true);
    try {
      const { data } = await api.post(`/projects/${project.id}/scenes/${s.id}/regenerate`, { instruction: instruction || null });
      update(data); setInstr("");
      if (instruction) toast.success(t("Updating the picture. Review the script and later pictures again when it finishes."));
    } catch (e) {
      try {
        const { data } = await api.get(`/projects/${project.id}`);
        update(data);
        const current = data.scenes?.find((scene) => scene.id === s.id);
        if (["queued", "generating", "ready"].includes(current?.status)) {
          toast.info(t("Picture request received. Its status will update here."));
        } else toast.error(t(errMsg(e)));
      } catch (_) {
        toast.error(t("Could not confirm picture status. Reopen this project before trying again."));
      }
    }
    finally { requestLock.current = false; setRequesting(false); }
  };
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/projects/${project.id}/scenes/${s.id}`, { narration, visual });
      update(data);
      toast.success(t("Scene saved. Review the changed script again before generating or rendering."));
    } catch (e) { toast.error(t(errMsg(e))); } finally { setSaving(false); }
  };
  const remove = async () => {
    if (!window.confirm(t("Remove scene {number}?", { number: i + 1 }))) return;
    try { const { data } = await api.delete(`/projects/${project.id}/scenes/${s.id}`); update(data); }
    catch (e) { toast.error(t(errMsg(e))); }
  };
  return (
    <div className="grid grid-cols-[112px_minmax(0,1fr)] sm:grid-cols-[150px_minmax(0,1fr)] rounded-2xl border border-[#d6e2d7] bg-[#f5f9f4] overflow-hidden" data-testid={`scene-card-${i}`}>
      <div className="relative aspect-[9/16] self-start bg-white">
        {s.image_path && <img src={mediaUrl(s.image_path)} alt={`Scene ${i + 1}`} className={`w-full h-full object-cover ${generating ? "opacity-40" : ""}`} />}
        {generating && (
          <div className={`absolute inset-0 grid place-items-center ${s.image_path ? "" : "shimmer"}`}>
            <div className="flex flex-col items-center gap-2 text-[#61736d] text-xs font-semibold"><Loader2 className="animate-spin" /> {t("Painting scene…")} </div>
          </div>
        )}
        {queued && <div role="status" className="absolute inset-0 grid place-items-center bg-[#e7efe7]/90 text-center text-[#263b36] text-xs font-semibold p-3"> {t("Queued — waiting for the previous picture")} </div>}
        {!s.image_path && !batchActive && <div className="absolute inset-0 grid place-items-center text-[#587168]"><ImageIcon size={32} /></div>}
        {(s.status === "failed" || (s.status === "pending" && s.error)) && (
          <div className="absolute inset-x-2 top-2 rounded-lg bg-rose-600 text-white text-xs p-2 flex gap-1.5"><AlertTriangle size={14} className="shrink-0" />{s.status === "pending" ? t("Generation paused") : t("Image generation failed")}</div>
        )}
        <span className="absolute top-2 left-2 font-mono text-[10px] bg-[#e7efe7]/90 text-[#263b36] rounded px-1.5 py-0.5">{String(i + 1).padStart(2, "0")}</span>
        {s.versions?.length > 1 && <span className="absolute top-2 right-2 text-[10px] bg-[#e7efe7]/90 text-[#263b36] rounded px-1.5 py-0.5">v{s.versions.length}</span>}
      </div>
      <div className="min-w-0 p-3 sm:p-4 space-y-2">
        <div className="text-sm font-bold text-[#263b36]">{t("step_4_label")} {i + 1}</div>
        {s.continuity_needs_review && <p className="rounded-lg bg-amber-50 p-2 text-xs text-amber-800"> {t("An earlier scene changed. Approve earlier pictures first; this picture will be checked for consistency when you approve it.")} </p>}
        {(s.status === "failed" || (s.status === "pending" && s.error)) && <p role="alert" className="rounded-lg bg-rose-500/15 p-2 text-xs text-rose-800">{t(s.error || "The image could not be generated. Try again.")}</p>}
        {s.placeholder && <p role="status" className="rounded-lg bg-amber-500/15 p-2 text-xs text-amber-800"> {t("Preview placeholder — the image provider did not generate this scene. Regenerate when image access is available.")} </p>}
        {s.image_path && !s.placeholder && s.status === "ready" && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <a href={mediaUrl(s.image_path)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-teal-800 underline"><ExternalLink size={13} /> {t("Inspect full picture")} </a>
            {s.approved ? <span className="inline-flex items-center gap-1 text-xs text-emerald-800"><CheckCircle2 size={14} /> {t("Approved")} </span>
              : <button type="button" data-testid={`scene-approve-btn-${i}`} onClick={() => approveScene(s.id)} disabled={!!approvingId}
                  className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
                  {approvingId === s.id ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                  {approvingId === s.id ? t("Approving…") : t("approve_picture")}
                </button>}
          </div>
        )}
        {approveError?.id === s.id && <p role="alert" className="rounded-lg bg-rose-500/15 p-2 text-xs text-rose-800">{t("Approval failed")}: {t(approveError.message)}</p>}
        <p className="line-clamp-2 text-xs leading-5 text-[#35574c] indic">{s.narration}</p>
        <details className="group/edit rounded-xl border border-[#d6e2d7] bg-[#f5f9f4] p-2.5">
          <summary className="cursor-pointer text-xs font-semibold text-teal-800">{t("edit_scene")}</summary>
          <div className="mt-3 space-y-2">
        <label className="block text-xs text-[#61736d]">{t("narration")}
          <textarea value={narration} onChange={(e) => setNarration(e.target.value)} disabled={batchActive} rows={3}
            className="indic mt-1 w-full rounded-lg border border-[#d6e2d7] bg-white px-2.5 py-2 text-[#263b36]" />
        </label>
        <label className="block text-xs text-[#61736d]"> {t("What should appear")} <textarea value={display(visual)} onChange={(e) => setVisual(e.target.value)} disabled={batchActive || pending(visual)} rows={3}
            className="mt-1 w-full rounded-lg border border-[#d6e2d7] bg-white px-2.5 py-2 text-[#263b36]" />
        </label>
        <div className="flex gap-2">
          <button onClick={save} disabled={saving || batchActive || (!narration.trim() || !visual.trim()) || (narration === s.narration && visual === s.visual)}
            className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-[#316b55] px-2 py-2 text-xs text-white disabled:opacity-40"><Save size={13} /> {t("Save scene")} </button>
          <button onClick={remove} disabled={batchActive || project.scenes.length <= 1} title={t("Remove scene")}
            className="rounded-lg border border-rose-700/50 px-2.5 text-rose-800 disabled:opacity-40"><Trash2 size={14} /></button>
        </div>
        <div className="flex gap-1.5">
          <input data-testid={`scene-edit-input-${i}`} value={instr} onChange={(e) => setInstr(e.target.value)} disabled={batchActive || !s.image_path}
            placeholder={t("e.g. add a rat near the cat")} className="flex-1 min-w-0 text-xs rounded-lg border border-[#d6e2d7] px-2.5 py-2 focus:outline-none focus:border-violet-500" />
          <button data-testid={`scene-edit-btn-${i}`} disabled={!instr.trim() || batchActive} onClick={() => run(instr)} title={t("Apply edit")}
            className="rounded-lg bg-[#316b55] text-white px-2.5 disabled:opacity-40"><Wand2 size={14} /></button>
        </div>
        <button data-testid={`scene-regen-btn-${i}`} disabled={batchActive} onClick={() => run(null)}
          className="w-full text-xs font-semibold text-[#61736d] hover:text-[#263b36] flex items-center justify-center gap-1.5 py-1 disabled:opacity-40">
          {requesting ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} {requesting ? t("Starting generation…") : generating ? t("Generating…") : t("Regenerate")}
        </button>
          </div>
        </details>
      </div>
    </div>
  );
}

export default function StepScenes({ project, update }) {
  const { t } = useLocale();
  const scenes = project.scenes || [];
  const [adding, setAdding] = useState(false);
  const [newNarration, setNewNarration] = useState("");
  const [newVisual, setNewVisual] = useState("");
  const [busy, setBusy] = useState(false);
  const [approvingId, setApprovingId] = useState("");
  const [approveError, setApproveError] = useState(null);
  const approveScene = async (id) => {
    if (approvingId) return;
    setApprovingId(id);
    setApproveError(null);
    try {
      const { data } = await api.post(`/projects/${project.id}/scenes/${id}/approve`);
      update(data);
    } catch (e) {
      const message = errMsg(e);
      setApproveError({ id, message });
    } finally { setApprovingId(""); }
  };
  const ready = scenes.filter((s) => s.status === "ready" && s.image_path && !s.placeholder && s.approved).length;
  const allReady = scenes.length > 0 && ready === scenes.length;
  const canContinue = scenes.length > 0 && scenes.every((s) => s.narration?.trim() && s.visual?.trim());
  const unfinished = scenes.flatMap((s, i) => {
    if (s.status === "ready" && s.image_path && !s.placeholder && s.approved) return [];
    const reason = s.status === "generating" ? t("picture is generating")
      : s.status === "queued" ? t("picture is queued")
      : s.status === "failed" ? t("picture generation failed")
      : s.placeholder ? t("picture is a placeholder")
      : !s.image_path ? t("needs a picture")
      : !s.approved ? t("needs picture approval")
      : t("picture needs attention");
    return [`${t("Scene")} ${i + 1}: ${reason}`];
  });
  const needsPictures = scenes.some((s) => s.status === "failed" || s.status === "pending" || s.status === "queued" || s.placeholder || !s.image_path);
  const generating = scenes.some((s) => s.status === "generating" || s.status === "queued");
  const next = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/projects/${project.id}`, { step: Math.max(project.step, 5) });
      update(data, 5);
    } catch (e) { toast.error(t(errMsg(e))); } finally { setBusy(false); }
  };
  const add = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/projects/${project.id}/scenes`, { narration: newNarration, visual: newVisual });
      update(data); setNewNarration(""); setNewVisual(""); setAdding(false);
    } catch (e) { toast.error(t(errMsg(e))); } finally { setBusy(false); }
  };
  const generateAll = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/projects/${project.id}/scenes/generate`);
      update(data);
      toast.success(t("Generating missing pictures one scene at a time…"));
    } catch (e) {
      try {
        const { data } = await api.get(`/projects/${project.id}`);
        update(data);
        if (data.scenes?.some((scene) => scene.status === "queued" || scene.status === "generating")) {
          toast.info(t("Picture generation is running. Progress will update here."));
        } else toast.error(t(errMsg(e)));
      } catch (_) {
        toast.error(t("Could not confirm picture status. Reopen this project before trying again."));
      }
    } finally { setBusy(false); }
  };
  return (
    <section className="rounded-2xl border border-[#d6e2d7] bg-white shadow-xl shadow-[#c7d8ca]/30 p-4 sm:p-6">
      <StepHeader n={4} title="Scene editor" pill={`${ready}/${scenes.length} ${t("approved")}`}>
        <span className="text-sm"> {t("Inspect each story picture and approve it before rendering your video. You can record your voice while pictures are pending.")} </span>
      </StepHeader>
      {!project.approved && <div role="alert" className="mt-5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-900"> {t("This script changed after review. Re-run Ram AI review and approve it before generating pictures or rendering.")} <button onClick={() => update(project, 2)} className="ml-3 font-semibold underline"> {t("Go to script review")} </button>
      </div>}
      {needsPictures && <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
        <p className="text-sm text-amber-900">{generating ? t("Pictures are being generated one scene at a time. You can make the narration while they finish.") : t("Some scenes need real pictures. Sample or failed images cannot be exported.")}</p>
        <div className="flex flex-wrap gap-2">
          {generating && <button type="button" onClick={() => update(project, 5)} className="rounded-xl border border-amber-200/40 px-4 py-2 text-sm font-semibold text-amber-900">{t("continue_voice")}</button>}
          <button data-testid="generate-pictures-btn" onClick={generateAll} disabled={busy || generating || !project.approved} className="btn-primary px-4 py-2 text-sm disabled:opacity-40">{busy || generating ? t("Generating one at a time…") : t("generate_pictures")}</button>
        </div>
      </div>}
      <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-3">
        {scenes.map((s, i) => <SceneCard key={s.id} s={s} i={i} project={project} update={update}
          approveScene={approveScene} approvingId={approvingId} approveError={approveError} generationActive={generating} />)}
      </div>
      <button onClick={() => setAdding(!adding)} disabled={scenes.length >= 12 || generating}
        className="mt-5 inline-flex items-center gap-2 rounded-xl border border-violet-500/50 px-4 py-2 text-sm text-violet-800 disabled:opacity-40"><Plus size={16} /> {t("Add scene")} </button>
      {adding && <div className="mt-3 max-w-xl space-y-3 rounded-xl border border-[#d6e2d7] p-4">
        <textarea value={newNarration} onChange={(e) => setNewNarration(e.target.value)} placeholder={t("What the voice says")} rows={2} className="indic w-full rounded-lg bg-white p-2 text-[#263b36]" />
        <textarea value={newVisual} onChange={(e) => setNewVisual(e.target.value)} placeholder={t("What appears on screen")} rows={2} className="w-full rounded-lg bg-white p-2 text-[#263b36]" />
        <button onClick={add} disabled={busy || generating || !newNarration.trim() || !newVisual.trim()} className="btn-primary px-4 py-2 disabled:opacity-40"> {t("Save new scene")} </button>
      </div>}
      <div className="mt-8 flex justify-end">
        <div className="flex flex-col items-end gap-2">
          {!allReady && <div role="status" className="max-w-md text-right text-sm text-amber-900">
            <p> {t("You can record your voice now. Finish these pictures before rendering:")} </p>
            <p>{unfinished.join(" · ")}</p>
          </div>}
          {!canContinue && <p role="alert" className="text-right text-sm text-amber-900"> {t("Add narration and visual directions to every scene to continue.")} </p>}
          <button data-testid="scenes-continue-btn" disabled={!canContinue || busy} onClick={next}
            className="inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-40">
            {t("continue_voice")} <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}
