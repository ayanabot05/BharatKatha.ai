import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Wand2, ArrowRight, AlertTriangle, ImageIcon, Trash2, Plus, Save, CheckCircle2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { StepHeader } from "@/components/StepHeader";

function SceneCard({ s, i, project, update, approveScene, approvingId, approveError, generationActive }) {
  const [instr, setInstr] = useState("");
  const [narration, setNarration] = useState(s.narration);
  const [visual, setVisual] = useState(s.visual);
  const [saving, setSaving] = useState(false);
  useEffect(() => { setNarration(s.narration); }, [s.narration]);
  useEffect(() => { setVisual(s.visual); }, [s.visual]);
  const generating = s.status === "generating";
  const queued = s.status === "queued";
  const batchActive = generationActive || generating || queued;
  const run = async (instruction) => {
    try {
      const { data } = await api.post(`/projects/${project.id}/scenes/${s.id}/regenerate`, { instruction: instruction || null });
      update(data); setInstr("");
    } catch (e) { toast.error(errMsg(e)); }
  };
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/projects/${project.id}/scenes/${s.id}`, { narration, visual });
      update(data);
      toast.success("Scene saved. Review the changed script again before generating or rendering.");
    } catch (e) { toast.error(errMsg(e)); } finally { setSaving(false); }
  };
  const remove = async () => {
    if (!window.confirm(`Remove scene ${i + 1}?`)) return;
    try { const { data } = await api.delete(`/projects/${project.id}/scenes/${s.id}`); update(data); }
    catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="rounded-2xl border border-[#65546B] bg-[#3A3040] overflow-hidden" data-testid={`scene-card-${i}`}>
      <div className="relative aspect-[9/16] bg-[#181A26]">
        {s.image_path && <img src={mediaUrl(s.image_path)} alt={`Scene ${i + 1}`} className={`w-full h-full object-cover ${generating ? "opacity-40" : ""}`} />}
        {generating && (
          <div className={`absolute inset-0 grid place-items-center ${s.image_path ? "" : "shimmer"}`}>
            <div className="flex flex-col items-center gap-2 text-slate-400 text-xs font-semibold"><Loader2 className="animate-spin" />Painting scene…</div>
          </div>
        )}
        {queued && <div role="status" className="absolute inset-0 grid place-items-center bg-black/50 text-center text-slate-100 text-xs font-semibold p-3">Queued — waiting for the previous picture</div>}
        {!s.image_path && !batchActive && <div className="absolute inset-0 grid place-items-center text-slate-300"><ImageIcon size={32} /></div>}
        {(s.status === "failed" || (s.status === "pending" && s.error)) && (
          <div className="absolute inset-x-2 top-2 rounded-lg bg-rose-600 text-white text-xs p-2 flex gap-1.5"><AlertTriangle size={14} className="shrink-0" />{s.status === "pending" ? "Generation paused" : "Image generation failed"}</div>
        )}
        <span className="absolute top-2 left-2 font-mono text-[10px] bg-black/60 text-white rounded px-1.5 py-0.5">{String(i + 1).padStart(2, "0")}</span>
        {s.versions?.length > 1 && <span className="absolute top-2 right-2 text-[10px] bg-slate-900/80 text-white rounded px-1.5 py-0.5">v{s.versions.length}</span>}
      </div>
      <div className="p-3 space-y-2">
        {(s.status === "failed" || (s.status === "pending" && s.error)) && <p role="alert" className="rounded-lg bg-rose-500/15 p-2 text-xs text-rose-100">{s.error || "The image could not be generated. Try again."}</p>}
        {s.placeholder && <p role="status" className="rounded-lg bg-amber-500/15 p-2 text-xs text-amber-200">Preview placeholder — the image provider did not generate this scene. Regenerate when image access is available.</p>}
        {s.image_path && !s.placeholder && s.status === "ready" && (
          <div className="flex items-center justify-between gap-2">
            <a href={mediaUrl(s.image_path)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-cyan-200 underline"><ExternalLink size={13} /> Inspect full picture</a>
            {s.approved ? <span className="inline-flex items-center gap-1 text-xs text-emerald-300"><CheckCircle2 size={14} /> Approved</span>
              : <button type="button" data-testid={`scene-approve-btn-${i}`} onClick={() => approveScene(s.id)} disabled={!!approvingId}
                  className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
                  {approvingId === s.id ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                  {approvingId === s.id ? "Approving…" : "Approve picture"}
                </button>}
          </div>
        )}
        {approveError?.id === s.id && <p role="alert" className="rounded-lg bg-rose-500/15 p-2 text-xs text-rose-100">Approval failed: {approveError.message}</p>}
        <label className="block text-xs text-slate-400">Narration
          <textarea value={narration} onChange={(e) => setNarration(e.target.value)} disabled={batchActive} rows={3}
            className="indic mt-1 w-full rounded-lg border border-[#65546B] bg-[#181A26] px-2.5 py-2 text-white" />
        </label>
        <label className="block text-xs text-slate-400">What should appear
          <textarea value={visual} onChange={(e) => setVisual(e.target.value)} disabled={batchActive} rows={3}
            className="mt-1 w-full rounded-lg border border-[#65546B] bg-[#181A26] px-2.5 py-2 text-white" />
        </label>
        <div className="flex gap-2">
          <button onClick={save} disabled={saving || batchActive || (!narration.trim() || !visual.trim()) || (narration === s.narration && visual === s.visual)}
            className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-cyan-900/70 px-2 py-2 text-xs text-white disabled:opacity-40"><Save size={13} /> Save scene</button>
          <button onClick={remove} disabled={batchActive || project.scenes.length <= 1} title="Remove scene"
            className="rounded-lg border border-rose-700/50 px-2.5 text-rose-300 disabled:opacity-40"><Trash2 size={14} /></button>
        </div>
        <div className="flex gap-1.5">
          <input data-testid={`scene-edit-input-${i}`} value={instr} onChange={(e) => setInstr(e.target.value)} disabled={batchActive || !s.image_path}
            placeholder="e.g. add a rat near the cat" className="flex-1 min-w-0 text-xs rounded-lg border border-[#65546B] px-2.5 py-2 focus:outline-none focus:border-violet-500" />
          <button data-testid={`scene-edit-btn-${i}`} disabled={!instr.trim() || batchActive} onClick={() => run(instr)} title="Apply edit"
            className="rounded-lg bg-violet-600 text-white px-2.5 disabled:opacity-40"><Wand2 size={14} /></button>
        </div>
        <button data-testid={`scene-regen-btn-${i}`} disabled={batchActive} onClick={() => run(null)}
          className="w-full text-xs font-semibold text-slate-400 hover:text-white flex items-center justify-center gap-1.5 py-1 disabled:opacity-40">
          <RefreshCw size={12} /> Regenerate
        </button>
      </div>
    </div>
  );
}

export default function StepScenes({ project, update }) {
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
    const reason = s.status === "generating" ? "picture is generating"
      : s.status === "queued" ? "picture is queued"
      : s.status === "failed" ? "picture generation failed"
      : s.placeholder ? "picture is a placeholder"
      : !s.image_path ? "needs a picture"
      : !s.approved ? "needs picture approval"
      : `picture status is ${s.status || "unknown"}`;
    return [`Scene ${i + 1}: ${reason}`];
  });
  const needsPictures = scenes.some((s) => s.status === "failed" || s.status === "pending" || s.status === "queued" || s.placeholder || !s.image_path);
  const generating = scenes.some((s) => s.status === "generating" || s.status === "queued");
  const next = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/projects/${project.id}`, { step: Math.max(project.step, 5) });
      update(data, 5);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const add = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/projects/${project.id}/scenes`, { narration: newNarration, visual: newVisual });
      update(data); setNewNarration(""); setNewVisual(""); setAdding(false);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const generateAll = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/projects/${project.id}/scenes/generate`);
      update(data);
      toast.success("Generating missing pictures one scene at a time…");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <section className="rounded-3xl border border-white/10 bg-[#302837]/80 backdrop-blur-xl shadow-2xl shadow-black/40 p-5 sm:p-8">
      <StepHeader n={4} title="Scene editor" pill={`${ready}/${scenes.length} approved`}>
        <span className="text-sm">Inspect each story picture and approve it before rendering your video. You can record your voice while pictures are pending.</span>
      </StepHeader>
      {!project.approved && <div role="alert" className="mt-5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
        This script changed after review. Re-run Ram AI review and approve it before generating pictures or rendering.
        <button onClick={() => update(project, 2)} className="ml-3 font-semibold underline">Go to script review</button>
      </div>}
      {needsPictures && <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
        <p className="text-sm text-amber-100">{generating ? "Pictures are being generated one scene at a time. Later scenes are queued." : "Some scenes need real pictures. Sample or failed images cannot be exported."}</p>
        <button onClick={generateAll} disabled={busy || generating || !project.approved} className="btn-primary px-4 py-2 text-sm disabled:opacity-40">{busy || generating ? "Generating one at a time…" : "Generate missing pictures"}</button>
      </div>}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {scenes.map((s, i) => <SceneCard key={s.id} s={s} i={i} project={project} update={update}
          approveScene={approveScene} approvingId={approvingId} approveError={approveError} generationActive={generating} />)}
      </div>
      <button onClick={() => setAdding(!adding)} disabled={scenes.length >= 12 || generating}
        className="mt-5 inline-flex items-center gap-2 rounded-xl border border-violet-500/50 px-4 py-2 text-sm text-violet-200 disabled:opacity-40"><Plus size={16} /> Add scene</button>
      {adding && <div className="mt-3 max-w-xl space-y-3 rounded-xl border border-[#65546B] p-4">
        <textarea value={newNarration} onChange={(e) => setNewNarration(e.target.value)} placeholder="What the voice says" rows={2} className="indic w-full rounded-lg bg-[#181A26] p-2 text-white" />
        <textarea value={newVisual} onChange={(e) => setNewVisual(e.target.value)} placeholder="What appears on screen" rows={2} className="w-full rounded-lg bg-[#181A26] p-2 text-white" />
        <button onClick={add} disabled={busy || generating || !newNarration.trim() || !newVisual.trim()} className="btn-primary px-4 py-2 disabled:opacity-40">Save new scene</button>
      </div>}
      <div className="mt-8 flex justify-end">
        <div className="flex flex-col items-end gap-2">
          {!allReady && <div role="status" className="max-w-md text-right text-sm text-amber-100">
            <p>You can record your voice now. Finish these pictures before rendering:</p>
            <p>{unfinished.join(" · ")}</p>
          </div>}
          {!canContinue && <p role="alert" className="text-right text-sm text-amber-100">Add narration and visual directions to every scene to continue.</p>}
          <button data-testid="scenes-continue-btn" disabled={!canContinue || busy} onClick={next}
            className="inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-40">
            Continue to voice <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}
