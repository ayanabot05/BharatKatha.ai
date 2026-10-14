import { Check } from "lucide-react";
import { STEPS } from "@/constants/studio";
import { useLocale } from "@/context/LocaleContext";
import { RamAvatar } from "@/components/fx";

/* A journey path: Ram AI hops along the nodes as you move through the studio */
export default function StudioStepper({ view, maxStep, setView, ramState = "idle" }) {
  const { t } = useLocale();
  const last = STEPS.length - 1;
  const pos = (view - 1) / last;
  const fill = Math.min(1, Math.max(0, (maxStep - 1) / last));
  return (
    <div data-testid="studio-stepper">
      <label htmlFor="studio-step-select" className="block sm:hidden text-sm font-semibold text-[#6c5a72] mb-2">{t("step")}</label>
      <select id="studio-step-select" data-testid="studio-step-select"
        className="block sm:hidden w-full rounded-xl border border-[#ecd9d3] bg-white px-4 py-3 text-[#4a3f58] font-semibold"
        value={view} onChange={(e) => { const next = Number(e.target.value); e.target.value = String(view); setView(next); }}>
        {STEPS.map((s) => <option key={s.n} value={s.n} disabled={s.n > maxStep}>{s.n}. {t(`step_${s.n}_label`) || s.label}</option>)}
      </select>

      <div className="path hidden sm:block rounded-2xl bg-[#fffbf8] border border-[#f0e1db]">
        <div className="path-track"><div className="path-fill" style={{ width: `${fill * 100}%` }} /></div>
        <span className="path-marker" style={{ left: `calc(32px + (100% - 64px) * ${pos})` }} aria-hidden="true"><RamAvatar state={ramState} size={30} /></span>
        <ol className="path-nodes" data-testid="studio-step-list">
          {STEPS.map((s) => {
            const allowed = s.n <= maxStep;
            const active = s.n === view;
            const done = s.n < maxStep && !active;
            const label = t(`step_${s.n}_label`) || s.label;
            return (
              <li key={s.n} className={`path-node ${active ? "is-active" : ""}`}>
                <button data-testid={`stepper-step-${s.n}`} disabled={!allowed} onClick={() => setView(s.n)} aria-current={active ? "step" : undefined} aria-label={label}
                  className={`path-dot ${active ? "active" : done ? "done" : ""}`}>
                  {done ? <Check size={14} /> : s.n}
                </button>
                <span className="path-label">{label}</span>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}