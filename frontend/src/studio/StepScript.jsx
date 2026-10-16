import { useState } from "react";
import { Loader2, ShieldCheck, ShieldAlert, Wand2, Save, CheckCircle2, ScanSearch } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { StepHeader } from "@/components/StepHeader";
import { ScoreRing } from "@/components/StepHeader";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { useLocale } from "@/context/LocaleContext";
import { useProjectCopy } from "@/context/ProjectCopyContext";

const FLOW = ["Hook", "Story", "Scene breakdown", "Ending", "Review and approve"];
const COLORS = { concept: "#38BDF8", trend: "#7C3AED", hook: "#F59E0B", safety: "#10B981" };

function AgentCard({ a }) {
  const { t } = useLocale();
  const { display } = useProjectCopy();
  return (
    <div className="rounded-2xl border border-[#d6e2d7] p-5 bg-[#f5f9f4] rise" data-testid={`agent-card-${a.key}`}>
      <div className="flex items-center gap-4">
        <ScoreRing score={a.score} color={COLORS[a.key]} />
        <div>
          <div className="font-semibold text-[#263b36]">{t(a.name)}</div>
          {a.key === "safety" && (
            <span data-testid="safety-badge" className={`inline-flex items-center gap-1 text-xs font-semibold rounded-full px-2 py-0.5 mt-1 ${a.safe ? "bg-emerald-500/10 text-emerald-800" : "bg-rose-500/10 text-rose-800"}`}>
              {a.safe ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}{a.safe ? t("No issues flagged by AI") : t("Flagged")}
            </span>
          )}
          {a.key === "concept" && (
            <span className={`inline-flex text-xs font-semibold rounded-full px-2 py-0.5 mt-1 ${a.aligned ? "bg-emerald-500/10 text-emerald-800" : "bg-rose-500/10 text-rose-800"}`}>
              {a.aligned ? t("Matches your idea") : t("Concept changed")}
            </span>
          )}
        </div>
      </div>
      <p className="mt-3 text-sm text-[#587168]">{display(a.verdict)}</p>
      {a.fixes?.length > 0 && (
        <ul className="mt-3 space-y-1.5 text-xs text-[#61736d] list-disc pl-4">{a.fixes.slice(0, 3).map((f, i) => <li key={i}>{display(f)}</li>)}</ul>
      )}
      {a.misses?.length > 0 && <p className="mt-2 text-xs text-rose-800">{t("Missing from your idea")}: {a.misses.slice(0, 2).map(display).join("; ")}</p>}
      {a.requirements?.length > 0 && <details className="mt-3 text-xs text-[#587168]">
        <summary className="cursor-pointer font-semibold"> {t("How your idea appears in the scenes")} </summary>
        <ul className="mt-2 space-y-2">{a.requirements.map((item, index) => <li key={index}>
          <span className={item.status === "met" ? "text-emerald-800" : "text-rose-800"}>{t(item.status)}</span>: {display(item.source)}
          {item.evidence.map((e, i) => <p key={i} className="mt-1 text-[#61736d]"> {t("Scene")} {e.scene}: “{display(e.quote)}”</p>)}
        </li>)}</ul>
      </details>}
    </div>
  );
}

export default function StepScript({ project, update }) {
  const { t } = useLocale();
  const { display, pending } = useProjectCopy();
  const [script, setScript] = useState(project.script);
  const [busy, setBusy] = useState("");
  const v = project.validation;
  const dirty = JSON.stringify(script) !== JSON.stringify(project.script);

  const call = async (key, fn, ok) => {
    setBusy(key);
    try { const { data } = await fn(); update(data, data.approved && key === "approve" ? 3 : undefined); setScript(data.script); if (key === "improve" && !data.validation) toast.message(t("Script updated. Run the review before approving.")); else if (ok) toast.success(t(ok)); }
    catch (e) { toast.error(t(errMsg(e))); } finally { setBusy(""); }
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

  if (!script) return <p className="text-[#587168]"> {t("Go back to step 1 and write a script first.")} </p>;
  return (
    <section className="rounded-3xl border border-[#d6e2d7] bg-white backdrop-blur-xl shadow-2xl shadow-[#c7d8ca]/30 p-5 sm:p-8">
      <StepHeader n={2} title="AI Script Studio" pill={project.approved ? t("Approved") : t("Draft")}>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-base">
          {FLOW.map((f, i) => <span key={f} className="text-[#587168]">{t(f)}{i < FLOW.length - 1 && <span className="text-[#61736d]"> →</span>}</span>)}
        </div>
      </StepHeader>

      {project.content_contract?.promise && (
        <div className="mt-6 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4 text-sm text-[#263b36]">
          <div className="text-xs font-bold uppercase tracking-wider text-teal-800"> {t("Your story promise")} </div>
          <p className="mt-1">{display(project.content_contract.promise)}</p>
          <details className="mt-2 text-xs text-[#587168]">
            <summary className="cursor-pointer font-semibold"> {t("Content the script must deliver")} </summary>
            <ul className="mt-2 list-disc pl-5 space-y-1">
              {project.content_contract.requirements?.map((item, i) => <li key={i}>{display(item.requirement)}</li>)}
            </ul>
          </details>
        </div>
      )}

      <div className="mt-6 grid lg:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-4">
          <Input data-testid="script-title-input" className="indic text-lg font-bold bg-[#f5f9f4]" value={script.title || ""} onChange={(e) => setScript({ ...script, title: e.target.value })} />
          <div className="rounded-2xl bg-amber-500/10 border border-amber-500/30 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-amber-800"> {t("Opening narration · scene 1")} </div>
            <Textarea data-testid="script-hook-input" rows={2} className="indic mt-2 bg-[#f5f9f4]" value={script.scenes?.[0]?.narration || ""} onChange={(e) => setScene(0, "narration", e.target.value)} />
          </div>
          <p className="text-sm text-[#61736d]"><span className="font-semibold">{t("Story")}: </span>{display(script.story)}</p>
          <div className="space-y-3">
            {script.scenes?.map((s, i) => (
              <div key={i} className="rounded-2xl border border-[#d6e2d7] p-4 bg-[#f5f9f4]" data-testid={`script-scene-${i}`}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-[#61736d]"> {t("SCENE")} {String(i + 1).padStart(2, "0")}</span>
                  <span className="uppercase tracking-wider font-semibold text-violet-400">{t(s.beat)}</span>
                </div>
                {i > 0 && i < script.scenes.length - 1
                  ? <Textarea data-testid={`scene-narration-input-${i}`} rows={2} className="indic mt-2 bg-[#f5f9f4]" value={s.narration} onChange={(e) => setScene(i, "narration", e.target.value)} />
                  : <p className="mt-2 text-xs text-[#61736d]">{i === 0 ? t("Edit the opening narration above.") : t("Edit the ending narration below.")}</p>}
                <Input data-testid={`scene-visual-input-${i}`} disabled={pending(s.visual)} className="mt-2 text-sm text-[#61736d] bg-[#f5f9f4]" value={display(s.visual)} onChange={(e) => setScene(i, "visual", e.target.value)} />
              </div>
            ))}
          </div>
          <div className="rounded-2xl bg-[#f5f9f4] border border-[#d6e2d7] p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-[#587168]"> {t("Ending / CTA")} </div>
            <Textarea data-testid="script-ending-input" rows={2} className="indic mt-2 bg-[#f5f9f4]" value={script.scenes?.[script.scenes.length - 1]?.narration || ""} onChange={(e) => setScene(script.scenes.length - 1, "narration", e.target.value)} />
          </div>
          <button data-testid="save-script-btn" onClick={save} disabled={!dirty || !!busy} className="inline-flex items-center gap-2 rounded-full border border-[#c4d8c9] px-5 py-2 text-sm font-semibold disabled:opacity-40">
            {busy === "save" ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} {t("Save edits")} </button>
        </div>

        <aside className="space-y-3 lg:sticky lg:top-6 self-start">
          <div className="rounded-2xl bg-gradient-to-br from-[#e2eee4] via-white to-[#f7eee2] border border-[#d6e2d7] text-[#263b36] p-5">
            <div className="text-xs uppercase tracking-wider text-amber-400 font-mono"> {t("Ram AI 1.0 Craft Review")} </div>
            <div className="mt-1 text-3xl font-extrabold" data-testid="overall-score">{v ? `${v.overall}/100` : "—"}</div>
            <p className="text-xs font-semibold text-amber-800 mt-1">{t(v?.rating_label || "Ram AI Craft Opinion")} <span className="text-[#61736d] font-normal"> {t("(Not a view forecast)")} </span></p>
            <p className="text-[11px] text-[#61736d] mt-1.5 leading-snug">{t(v?.disclaimer || "Pacing and story structure evaluation across Indian short-form standards.")}</p>

            <button data-testid="run-review-btn" onClick={review} disabled={!!busy} className="mt-4 w-full btn-primary py-2.5 flex items-center justify-center gap-2 disabled:opacity-60">
              {busy === "review" ? <Loader2 size={16} className="animate-spin" /> : <ScanSearch size={16} />} {v ? t("Re-run Ram AI review") : t("Run Ram AI review")}
            </button>
            {v && (
              <button data-testid="apply-fixes-btn" onClick={() => call("improve", () => api.post(`/projects/${project.id}/script/improve`), "Ram AI fixes applied & re-reviewed")} disabled={!!busy}
                className="mt-2 w-full rounded-full border border-cyan-500/40 hover:border-cyan-400 bg-cyan-500/10 py-2.5 text-sm font-semibold flex items-center justify-center gap-2 text-teal-800 disabled:opacity-60">
                {busy === "improve" ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />} {t("Apply Ram AI fixes")} </button>
            )}
          </div>

          {v?.ram_ai_checks && (
            <div className="rounded-2xl border border-[#d6e2d7] p-4 bg-[#f5f9f4] rise">
              <div className="text-xs font-bold uppercase tracking-wider text-[#61736d] mb-2.5"> {t("Ram AI Script Checks")} </div>
              <ul className="space-y-2 text-xs">
                {v.ram_ai_checks.map((c, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className={`h-4 w-4 rounded-full shrink-0 flex items-center justify-center text-[10px] mt-0.5 ${c.advisory ? "bg-amber-500/20 text-amber-400 border border-amber-500/40" : c.passed ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40" : "bg-rose-500/20 text-rose-400 border border-rose-500/40"}`}>
                      {c.advisory ? "i" : c.passed ? "✓" : "✗"}
                    </span>
                    <div>
                      <div className={`font-semibold ${c.advisory ? "text-amber-800" : c.passed ? "text-[#35574c]" : "text-rose-800"}`}>{t(c.check)}</div>
                      <div className="text-[11px] text-[#61736d]">{t(c.detail)}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {v?.content_gaps?.length > 0 && (
            <div role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-800">
              <div className="font-semibold"> {t("The script does not yet deliver the selected idea")} </div>
              <ul className="mt-2 list-disc pl-5">{v.content_gaps.map((gap, i) => <li key={i}>{display(gap)}</li>)}</ul>
            </div>
          )}

          {v?.agents.map((a) => <AgentCard key={a.key} a={a} />)}
          <button data-testid="approve-script-btn" disabled={!v || !v.all_passed || !!busy || dirty}
            onClick={() => call("approve", () => api.post(`/projects/${project.id}/script/approve`), "Script approved")}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2 disabled:opacity-40">
            <CheckCircle2 size={16} /> {t("Approve script")} </button>
          {!v?.safe && v && <p className="text-xs text-rose-400 text-center"> {t("Safety checks flagged. Apply fixes to enable approval.")} </p>}
          {v?.safe && !v?.all_passed && <p className="text-xs text-rose-400 text-center"> {t("Resolve missing story content and failed script checks, then re-run review to enable approval.")} </p>}
          {dirty && <p className="text-xs text-[#587168] text-center"> {t("Save or re-run the review after editing.")} </p>}
        </aside>
      </div>
    </section>
  );
}
