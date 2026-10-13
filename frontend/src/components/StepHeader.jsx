import { ArrowDown } from "lucide-react";

export function StepHeader({ n, title, pill, children }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 rise">
      <div>
        <div className="label">Step {String(n).padStart(2, "0")} / 06</div>
        <h2 className="mt-1.5 text-2xl sm:text-3xl font-bold tracking-tight text-white" data-testid={`step-${n}-title`}>
          Step {n} — {title}
        </h2>
        {children && <div className="mt-2 text-slate-300">{children}</div>}
      </div>
      {pill && (
        <span className="shrink-0 rounded-full px-3 py-1 bg-rose-300/10 border border-rose-300/30 text-xs font-mono text-rose-100">{pill}</span>
      )}
    </div>
  );
}

export const StepArrow = () => (
  <div className="flex justify-center py-5 text-slate-600"><ArrowDown size={18} className="animate-bounce" /></div>
);

export function ScoreRing({ score = 0, size = 64, color = "#D9788B" }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} className="-rotate-90 shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} stroke="#65546B" strokeWidth="6" fill="none" />
      <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="6" fill="none" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c - (c * score) / 100} style={{ transition: "stroke-dashoffset .9s ease", filter: `drop-shadow(0 0 6px ${color}88)` }} />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" className="rotate-90 origin-center font-bold" fill="#F8FAFC" style={{ fontSize: size / 4 }}>
        {score}
      </text>
    </svg>
  );
}
