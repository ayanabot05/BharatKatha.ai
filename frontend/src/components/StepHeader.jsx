import { ArrowDown } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";

export function StepHeader({ n, title, pill, children }) {
  const { locale, t } = useLocale();
  const heading = locale === "en" ? title : n === 4 ? t("scene_editor") : t(`step_${n}_label`);
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 rise">
      <div>
        <div className="label">{t("step")} {String(n).padStart(2, "0")} / 06</div>
        <h2 className="mt-1.5 text-2xl sm:text-3xl font-bold tracking-tight text-[#263b36]" data-testid={`step-${n}-title`}>
          {heading}
        </h2>
        {children && <div className="mt-2 text-[#587168]">{children}</div>}
      </div>
      {pill && (
        <span className="shrink-0 rounded-full px-3 py-1 bg-[#f6e7e3] border border-[#e8c4c0] text-xs font-mono text-[#924457]">{pill}</span>
      )}
    </div>
  );
}

export const StepArrow = () => (
  <div className="flex justify-center py-5 text-[#759284]"><ArrowDown size={18} className="animate-bounce" /></div>
);

export function ScoreRing({ score = 0, size = 64, color = "#D9788B" }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} className="-rotate-90 shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} stroke="#d6e2d7" strokeWidth="6" fill="none" />
      <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="6" fill="none" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c - (c * score) / 100} style={{ transition: "stroke-dashoffset .9s ease", filter: `drop-shadow(0 0 6px ${color}88)` }} />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" className="rotate-90 origin-center font-bold" fill="#263b36" style={{ fontSize: size / 4 }}>
        {score}
      </text>
    </svg>
  );
}
