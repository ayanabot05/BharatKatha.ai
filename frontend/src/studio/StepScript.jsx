import { useState } from "react";
import { Loader2, ShieldCheck, ShieldAlert, Wand2, Save, CheckCircle2, ScanSearch } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { StepHeader } from "@/components/StepHeader";
import { ScoreRing } from "@/components/StepHeader";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

const FLOW = ["Hook", "Story", "Scene breakdown", "Ending", "Review and approve"];
const COLORS = { concept: "#38BDF8", trend: "#7C3AED", hook: "#F59E0B", safety: "#10B981" };

function AgentCard({ a }) {
  return (
    <div className="rounded-2xl border border-[#65546B] p-5 bg-[#3A3040] rise" data-testid={`agent-card-${a.key}`}>
      <div className="flex items-center gap-4">
        <ScoreRing score={a.score} color={COLORS[a.key]} />
        <div>
          <div className="font-semibold text-white">{a.name}</div>
          {a.key === "safety" && (
            <span data-testid="safety-badge" className={`inline-flex items-center gap-1 text-xs font-semibold rounded-full px-2 py-0.5 mt-1 ${a.safe ? "bg-emerald-500/10 text-emerald-300" : "bg-rose-500/10 text-rose-300"}`}>
              {a.safe ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}{a.safe ? "No issues flagged by AI" : "Flagged"}
            </span>
          )}
          {a.key === "concept" && (
            <span className={`inline-flex text-xs font-semibold rounded-full px-2 py-0.5 mt-1 ${a.aligned ? "bg-emerald-500/10 text-emerald-300" : "bg-rose-500/10 text-rose-300"}`}>
              {a.aligned ? "Matches your idea" : "Concept changed"}
            </span>
          )}
        </div>
      </div>
      <p className="mt-3 text-sm text-slate-300">{a.verdict}</p>
      {a.fixes?.length > 0 && (
        <ul className="mt-3 space-y-1.5 text-xs text-slate-400 list-disc pl-4">{a.fixes.slice(0, 3).map((f, i) => <li key={i}>{f}</li>)}</ul>
      )}
      {a.misses?.length > 0 && <p className="mt-2 text-xs text-rose-300">Missing from your idea: {a.misses.slice(0, 2).join("; ")}</p>}
      {a.requirements?.length > 0 && <details className="mt-3 text-xs text-slate-300">
        <summary className="cursor-pointer font-semibold">How your idea appears in the scenes</summary>
        <ul className="mt-2 space-y-2">{a.requirements.map((item, index) => <li key={index}>
          <span className={item.status === "met" ? "text-emerald-300" : "text-rose-300"}>{item.status}</span>: {item.source}
          {item.evidence.map((e, i) => <p key={i} className="mt-1 text-slate-400">Scene {e.scene}: “{e.quote}”</p>)}
        </li>)}</ul>
      </details>}
    </div>
  );
}

export default function StepScript({ project, update }) {
  const [script, setScript] = useState(project.script);
  const [busy, setBusy] = useState("");
  const v = project.validation;
  const dirty = JSON.stringify(script) !== JSON.stringify(project.script);

  const call = async (key, fn, ok) => {
    setBusy(key);
    try { const { data } = await fn(); update(data, data.approved && key === "approve" ? 3 : undefined); setScript(data.script); if (ok) toast.success(ok); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(""); }
  };
  const save = () => call("save", () => api.patch(`/projects/${project.id}`, { script }), "Script saved");
  const review = () => call("review", async () => {
    if (dirty) {
      const saved = await api.patch(`/projects/${project.id}`, { script });
      update(saved.data);
    }
    return api.post(`/projects/${project.id}/script/validate`);
  }, "AI review complete");
  const setScene = (i, k, val) => setScript({ ...script,
    ...(k === "narration" && i === 0 ? { hook: val } : {}),
    ...(k === "narration" && i === script.scenes.length - 1 ? { ending: val } : {}),
    scenes: script.scenes.map((s, j) => (j === i ? { ...s, [k]: val } : s)) });

  if (!script) return <p className="text-slate-300">Go back to step 1 and write a script first.</p>;
  return (
    <section className="rounded-3xl border border-white/10 bg-[#302837]/80 backdrop-blur-xl shadow-2xl shadow-black/40 p-5 sm:p-8">
      <StepHeader n={2} title="AI Script Studio" pill={project.approved ? "Approved" : "Draft"}>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-base">
          {FLOW.map((f, i) => <span key={f} className="text-slate-300">{f}{i < FLOW.length - 1 && <span className="text-slate-400"> →</span>}</span>)}
        </div>
      </StepHeader>

      {project.content_contract?.promise && (
        <div className="mt-6 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4 text-sm text-slate-100">
          <div className="text-xs font-bold uppercase tracking-wider text-cyan-200">Your story promise</div>
          <p className="mt-1">{project.content_contract.promise}</p>
          <details className="mt-2 text-xs text-slate-300">
            <summary className="cursor-pointer font-semibold">Content the script must deliver</summary>
            <ul className="mt-2 list-disc pl-5 space-y-1">
              {project.content_contract.requirements?.map((item, i) => <li key={i}>{item.requirement}</li>)}
            </ul>
          </details>
        </div>
      )}

      <div className="mt-6 grid lg:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-4">
          <Input data-testid="script-title-input" className="indic text-lg font-bold bg-[#3A3040]" value={script.title || ""} onChange={(e) => setScript({ ...script, title: e.target.value })} />
          <div className="rounded-2xl bg-amber-500/10 border border-amber-500/30 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-amber-300">Opening narration · scene 1</div>
            <Textarea data-testid="script-hook-input" rows={2} className="indic mt-2 bg-[#3A3040]" value={script.scenes?.[0]?.narration || ""} onChange={(e) => setScene(0, "narration", e.target.value)} />
          </div>
          <p className="text-sm text-slate-400"><span className="font-semibold">Story: </span>{script.story}</p>
          <div className="space-y-3">
            {script.scenes?.map((s, i) => (
              <div key={i} className="rounded-2xl border border-[#65546B] p-4 bg-[#3A3040]" data-testid={`script-scene-${i}`}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-slate-400">SCENE {String(i + 1).padStart(2, "0")}</span>
                  <span className="uppercase tracking-wider font-semibold text-violet-400">{s.beat}</span>
                </div>
                {i > 0 && i < script.scenes.length - 1
                  ? <Textarea data-testid={`scene-narration-input-${i}`} rows={2} className="indic mt-2 bg-[#3A3040]" value={s.narration} onChange={(e) => setScene(i, "narration", e.target.value)} />
                  : <p className="mt-2 text-xs text-slate-400">{i === 0 ? "Edit the opening narration above." : "Edit the ending narration below."}</p>}
                <Input data-testid={`scene-visual-input-${i}`} className="mt-2 text-sm text-slate-400 bg-[#0C0E16]" value={s.visual} onChange={(e) => setScene(i, "visual", e.target.value)} />
              </div>
            ))}
          </div>
          <div className="rounded-2xl bg-[#0C0E16] border border-[#65546B] p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-300">Ending / CTA</div>
            <Textarea data-testid="script-ending-input" rows={2} className="indic mt-2 bg-[#3A3040]" value={script.scenes?.[script.scenes.length - 1]?.narration || ""} onChange={(e) => setScene(script.scenes.length - 1, "narration", e.target.value)} />
          </div>
          <button data-testid="save-script-btn" onClick={save} disabled={!dirty || !!busy} className="inline-flex items-center gap-2 rounded-full border border-[#383D54] px-5 py-2 text-sm font-semibold disabled:opacity-40">
            {busy === "save" ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save edits
          </button>
        </div>

        <aside className="space-y-3 lg:sticky lg:top-6 self-start">
          <div className="rounded-2xl bg-gradient-to-br from-violet-600/25 via-[#3A3040] to-rose-500/10 border border-violet-500/30 text-white p-5">
            <div className="text-xs uppercase tracking-wider text-amber-400 font-mono">Ram AI 1.0 Craft Review</div>
            <div className="mt-1 text-3xl font-extrabold" data-testid="overall-score">{v ? `${v.overall}/100` : "—"}</div>
            <p className="text-xs font-semibold text-amber-300 mt-1">{v?.rating_label || "Ram AI Craft Opinion"} <span className="text-slate-400 font-normal">(Not a view forecast)</span></p>
            <p className="text-[11px] text-slate-400 mt-1.5 leading-snug">{v?.disclaimer || "Pacing and story structure evaluation across Indian short-form standards."}</p>

            <button data-testid="run-review-btn" onClick={review} disabled={!!busy} className="mt-4 w-full btn-primary py-2.5 flex items-center justify-center gap-2 disabled:opacity-60">
              {busy === "review" ? <Loader2 size={16} className="animate-spin" /> : <ScanSearch size={16} />} {v ? "Re-run Ram AI review" : "Run Ram AI review"}
            </button>
            {v && (
              <button data-testid="apply-fixes-btn" onClick={() => call("improve", () => api.post(`/projects/${project.id}/script/improve`), "Ram AI fixes applied & re-reviewed")} disabled={!!busy}
                className="mt-2 w-full rounded-full border border-cyan-500/40 hover:border-cyan-400 bg-cyan-500/10 py-2.5 text-sm font-semibold flex items-center justify-center gap-2 text-cyan-300 disabled:opacity-60">
                {busy === "improve" ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />} Apply Ram AI fixes
              </button>
            )}
          </div>

          {v?.ram_ai_checks && (
            <div className="rounded-2xl border border-[#65546B] p-4 bg-[#3A3040] rise">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5">Ram AI Script Checks</div>
              <ul className="space-y-2 text-xs">
                {v.ram_ai_checks.map((c, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className={`h-4 w-4 rounded-full shrink-0 flex items-center justify-center text-[10px] mt-0.5 ${c.advisory ? "bg-amber-500/20 text-amber-400 border border-amber-500/40" : c.passed ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40" : "bg-rose-500/20 text-rose-400 border border-rose-500/40"}`}>
                      {c.advisory ? "i" : c.passed ? "✓" : "✗"}
                    </span>
                    <div>
                      <div className={`font-semibold ${c.advisory ? "text-amber-300" : c.passed ? "text-slate-200" : "text-rose-300"}`}>{c.check}</div>
                      <div className="text-[11px] text-slate-400">{c.detail}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {v?.content_gaps?.length > 0 && (
            <div role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-100">
              <div className="font-semibold">The script does not yet deliver the selected idea</div>
              <ul className="mt-2 list-disc pl-5">{v.content_gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul>
            </div>
          )}

          {v?.agents.map((a) => <AgentCard key={a.key} a={a} />)}
          <button data-testid="approve-script-btn" disabled={!v || !v.all_passed || !!busy || dirty}
            onClick={() => call("approve", () => api.post(`/projects/${project.id}/script/approve`), "Script approved")}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2 disabled:opacity-40">
            <CheckCircle2 size={16} /> Approve script
          </button>
          {!v?.safe && v && <p className="text-xs text-rose-400 text-center">Safety checks flagged. Apply fixes to enable approval.</p>}
          {v?.safe && !v?.all_passed && <p className="text-xs text-rose-400 text-center">Resolve missing story content and failed script checks, then re-run review to enable approval.</p>}
          {dirty && <p className="text-xs text-slate-300 text-center">Save or re-run the review after editing.</p>}
        </aside>
      </div>
    </section>
  );
}
