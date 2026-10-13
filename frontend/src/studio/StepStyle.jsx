import { useState } from "react";
import { Check, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { StepHeader, StepArrow } from "@/components/StepHeader";
import { STYLES } from "@/constants/studio";

export default function StepStyle({ project, update }) {
  const [style, setStyle] = useState(project.style);
  const [busy, setBusy] = useState(false);
  const hasImages = project.scenes?.some((s) => s.image_path);

  const go = async () => {
    setBusy(true);
    try {
      await api.patch(`/projects/${project.id}`, { style });
      if (hasImages && style === project.style) {
        const { data } = await api.patch(`/projects/${project.id}`, { step: Math.max(project.step, 4) });
        return update(data, 4);
      }
      const { data } = await api.post(`/projects/${project.id}/scenes/generate`);
      toast.success("Generating your scenes…");
      update(data, 4);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <section className="rounded-3xl border border-white/10 bg-[#302837]/80 backdrop-blur-xl shadow-2xl shadow-black/40 p-5 sm:p-8">
      <StepHeader n={3} title="Choose a video style">
        <span className="text-sm">The look is applied to every scene and kept consistent across characters.</span>
      </StepHeader>
      <div className="mt-6 grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4" data-testid="style-grid">
        {STYLES.map((s, i) => {
          const on = style === s.id;
          return (
            <button key={s.id} data-testid={`style-card-${s.id}`} onClick={() => setStyle(s.id)}
              className={`group text-center rise rise-${(i % 4) + 1}`}>
              <div className={`relative rounded-2xl overflow-hidden transition-[box-shadow,transform] ${on ? "ring-4 ring-violet-500 ring-offset-2 ring-offset-[#261F2C]" : "group-hover:shadow-lg"}`}>
                <img src={`/styles/${s.id}.jpg`} alt={s.label} className="w-full aspect-square object-cover transition-transform duration-500 group-hover:scale-[1.03]" />
                {on && <span className="absolute top-3 right-3 h-7 w-7 rounded-full bg-violet-600 text-white grid place-items-center"><Check size={16} /></span>}
              </div>
              <div className="mt-3 text-sm font-semibold text-white">{s.label}</div>
              <div className="text-xs text-slate-300">{s.hint}</div>
            </button>
          );
        })}
      </div>
      <StepArrow />
      <div className="flex justify-center">
        <button data-testid="generate-scenes-btn" disabled={!style || busy || !project.approved} onClick={go}
          className="inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-40">
          {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
          {hasImages && style === project.style ? "Continue to scenes" : "Generate scenes in this style"}
        </button>
      </div>
      {!project.approved && <p className="mt-2 text-center text-xs text-rose-400">Approve the script in step 2 first.</p>}
    </section>
  );
}
