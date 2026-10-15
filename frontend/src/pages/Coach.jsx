import { useEffect, useState } from "react";
import { Loader2, Plus, Trash2, TrendingUp, FlaskConical, CalendarDays, Lightbulb, Gauge } from "lucide-react";
import { toast } from "sonner";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, errMsg } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { LANGUAGES } from "@/constants/studio";
import { useLocale } from "@/context/LocaleContext";
import { ScoreRing } from "@/components/StepHeader";

const POINTS = [0, 5, 10, 15, 20, 30, 40];
const blank = () => ({ title: "", views: null, avg_viewed_pct: null, viewed_vs_swiped_pct: null, likes: null, retention: [null, null, null, null, null, null, null] });
const EXAMPLE = {
  channel_name: "Telugu Kathalu", niche: "Moral stories", language: "te", subscribers: 1200,
  videos: [
    { title: "Talking cow & honest boy", views: 12400, avg_viewed_pct: 42, viewed_vs_swiped_pct: 58, likes: 610, retention: [100, 72, 59, 50, 44, 32, 22] },
    { title: "Grandma's magic pot", views: 3100, avg_viewed_pct: 31, viewed_vs_swiped_pct: 44, likes: 120, retention: [100, 58, 45, 37, 30, 22, 15] },
  ],
};

function Num({ label, value, onChange, testid }) {
  return (
    <label className="block">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-[#587168]">{label}</span>
      <Input data-testid={testid} type="number" min="0" value={value ?? ""} placeholder="Optional" onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} className="mt-1 bg-[#f5f9f4]" />
    </label>
  );
}

function Report({ doc }) {
  const r = doc.report;
  const chart = POINTS.map((t, i) => ({ t: `${t}s`, ...Object.fromEntries(doc.input.videos.map((v, j) => [`v${j}`, v.retention?.[i] ?? null])) }));
  const List = ({ icon: Icon, title, items, testid }) => (
    <div className="rounded-2xl border border-[#d6e2d7] p-5" data-testid={testid}>
      <div className="flex items-center gap-2 font-semibold"><Icon size={16} className="text-violet-400" />{title}</div>
      <ul className="mt-3 space-y-2 text-sm text-[#587168] list-disc pl-5">{(items || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
  return (
    <div className="mt-10 space-y-5 rise" data-testid="coach-report">
      <div className="rounded-2xl bg-gradient-to-br from-[#e2eee4] via-white to-[#f7eee2] border border-[#d6e2d7] text-[#263b36] p-6 flex flex-wrap items-center gap-6">
        {r.health_score != null && <div className="bg-[#f5f9f4] rounded-full p-1"><ScoreRing score={r.health_score} size={84} /></div>}
        <div className="flex-1 min-w-[220px]">
          <div className="text-xs uppercase tracking-wider text-[#61736d]">{r.health_score == null ? "Your next steps" : "AI assessment from your supplied numbers"}</div>
          <p className="mt-1 text-lg" data-testid="coach-summary">{r.summary}</p>
        </div>
      </div>
      {doc.input.videos.some(v => v.retention?.some(n => n != null)) && <div className="rounded-2xl border border-[#d6e2d7] p-5">
        <div className="font-semibold">Audience retention</div>
        <div className="h-56 mt-3">
          <ResponsiveContainer>
            <LineChart data={chart}><CartesianGrid stroke="#65546B" /><XAxis dataKey="t" fontSize={12} /><YAxis unit="%" fontSize={12} /><Tooltip />
              {doc.input.videos.map((v, j) => <Line key={j} dataKey={`v${j}`} name={v.title} stroke={["#7C3AED", "#F59E0B", "#10B981", "#EF4444"][j % 4]} strokeWidth={2.5} dot={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>}
      <div className="grid md:grid-cols-2 gap-4">
        <List icon={Gauge} title="Measured (from your numbers)" items={r.measured} testid="coach-measured" />
        <List icon={Lightbulb} title="Hypotheses (possible causes)" items={r.hypotheses} testid="coach-hypotheses" />
      </div>
      <div className="rounded-2xl border border-[#d6e2d7] p-5" data-testid="coach-experiments">
        <div className="flex items-center gap-2 font-semibold"><FlaskConical size={16} className="text-amber-500" />Experiments to run</div>
        <div className="mt-3 grid md:grid-cols-2 gap-3">
          {(r.experiments || []).map((x, i) => (
            <div key={i} className="rounded-xl bg-[#f5f9f4] p-4 text-sm"><div className="font-semibold">{x.title}</div><p className="text-[#61736d] mt-1">{x.how}</p><p className="text-xs text-violet-800 mt-2">Measure: {x.metric}</p></div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl border border-[#d6e2d7] p-5" data-testid="coach-weekly-plan">
        <div className="flex items-center gap-2 font-semibold"><CalendarDays size={16} className="text-emerald-600" />This week's plan</div>
        <div className="mt-3 divide-y divide-[#d6e2d7]">
          {(r.weekly_plan || []).map((d, i) => (
            <div key={i} className="py-2.5 grid grid-cols-[48px_1fr] gap-3 text-sm"><span className="font-mono text-[#61736d]">{d.day}</span><div><div className="indic font-medium">{d.idea}</div><div className="indic text-xs text-[#587168]">Hook: {d.hook}</div></div></div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Coach() {
  const { locale, t } = useLocale();
  const [example, setExample] = useState(false);
  const [form, setForm] = useState({ channel_name: "", niche: "Stories", language: locale, subscribers: null, goal: "", videos: [blank()] });
  const [busy, setBusy] = useState(false);
  const [doc, setDoc] = useState(null);
  useEffect(() => { api.get("/coach/reports").then((r) => r.data[0] && setDoc(r.data[0])).catch((e) => toast.error(errMsg(e))); }, []);
  const setV = (i, k, v) => setForm({ ...form, videos: form.videos.map((x, j) => (j === i ? { ...x, [k]: v } : x)) });
  const setR = (i, p, v) => setV(i, "retention", form.videos[i].retention.map((x, j) => (j === p ? v : x)));

  const analyze = async () => {
    if (form.videos.some((v) => !v.title.trim())) return toast.error("Give each video a title");
    setBusy(true);
    try { const { data } = await api.post("/coach/analyze", { ...form, language: locale }); setDoc(data); toast.success("Analysis ready"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <div className="rise">
        <span className="inline-flex rounded-full px-3 py-1 bg-violet-500/10 text-violet-800 border border-violet-500/30 text-xs font-semibold">Ram AI 1.0</span>
        <h1 className="mt-3 text-3xl sm:text-4xl font-extrabold tracking-tight flex items-center gap-3"><TrendingUp className="text-violet-400" />{t("growth_coach")}</h1>
        <p className="mt-2 text-[#61736d] max-w-2xl">Tell us your topic and goal to plan your next video. Already posting? Add numbers from YouTube Studio. Leave anything you do not know blank.</p>
      </div>
      <div className="mt-8 rounded-3xl border border-[#d6e2d7] bg-white backdrop-blur-xl shadow-2xl shadow-[#c7d8ca]/30 p-5 sm:p-8 space-y-6">
        <div className="flex flex-wrap gap-3 items-end">
          <label className="flex-1 min-w-[200px]"><span className="text-[11px] font-semibold uppercase tracking-wider text-[#587168]">Channel</span>
            <Input data-testid="coach-channel-input" value={form.channel_name} onChange={(e) => setForm({ ...form, channel_name: e.target.value })} className="mt-1" /></label>
          <label className="flex-1 min-w-[160px]"><span className="text-[11px] font-semibold uppercase tracking-wider text-[#587168]">Niche</span>
            <Input data-testid="coach-niche-input" value={form.niche} onChange={(e) => setForm({ ...form, niche: e.target.value })} className="mt-1" /></label>
          <div className="w-32"><Num label="Subscribers" testid="coach-subs-input" value={form.subscribers} onChange={(v) => setForm({ ...form, subscribers: v })} /></div>
          <button data-testid="coach-load-example-btn" onClick={() => { setForm(EXAMPLE); setExample(true); }} className="rounded-full border border-[#c4d8c9] px-4 py-2 text-sm font-semibold">Load example</button>
        </div>
        {example && <p role="status" className="text-sm text-[#8b4053]">These are sample numbers, not your channel results. Replace them before requesting advice.</p>}
        <label className="block text-sm">What would you like to improve?<Input value={form.goal || ""} maxLength={500} onChange={e => setForm({ ...form, goal: e.target.value })} placeholder="For example: make my story opening clearer" className="mt-2" /></label>
        <p className="text-sm text-[#607269]">Advice language: {LANGUAGES.find(l => l.id === locale)?.native}. Change it with the app language selector.</p>
        {form.videos.map((v, i) => (
          <div key={i} className="rounded-2xl bg-[#f5f9f4] border border-[#d6e2d7] p-4" data-testid={`coach-video-${i}`}>
            <div className="flex gap-2">
              <Input data-testid={`coach-video-title-${i}`} placeholder="Video title or a topic you plan to make" value={v.title} onChange={(e) => setV(i, "title", e.target.value)} className="bg-[#f5f9f4]" />
              {form.videos.length > 1 && <button onClick={() => setForm({ ...form, videos: form.videos.filter((_, j) => j !== i) })} className="text-[#61736d] hover:text-rose-400 px-2"><Trash2 size={16} /></button>}
            </div>
            <details className="mt-3"><summary className="cursor-pointer text-sm font-semibold">Add performance numbers (optional)</summary>
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
              <Num label="Views" testid={`coach-views-${i}`} value={v.views} onChange={(x) => setV(i, "views", x)} />
              <Num label="Avg viewed %" testid={`coach-avg-${i}`} value={v.avg_viewed_pct} onChange={(x) => setV(i, "avg_viewed_pct", x)} />
              <Num label="Viewed vs swiped %" testid={`coach-swiped-${i}`} value={v.viewed_vs_swiped_pct} onChange={(x) => setV(i, "viewed_vs_swiped_pct", x)} />
              <Num label="Likes" testid={`coach-likes-${i}`} value={v.likes} onChange={(x) => setV(i, "likes", x)} />
            </div>
            <div className="mt-3 text-[11px] font-semibold uppercase tracking-wider text-[#587168]">Retention % at</div>
            <div className="mt-1 grid grid-cols-7 gap-1.5">
              {POINTS.map((t, p) => (
                <label key={t} className="text-center"><span className="text-[10px] text-[#61736d] font-mono">{t}s</span>
                  <input type="number" min="0" max="1000" value={v.retention[p] ?? ""} onChange={(e) => setR(i, p, e.target.value === "" ? null : Number(e.target.value))} className="w-full rounded-md border border-[#d6e2d7] px-1 py-1 text-xs text-center" data-testid={`coach-ret-${i}-${p}`} /></label>
              ))}
            </div></details>
          </div>
        ))}
        <div className="flex flex-wrap gap-3">
          <button data-testid="coach-add-video-btn" disabled={form.videos.length >= 10} onClick={() => setForm({ ...form, videos: [...form.videos, blank()] })} className="rounded-full border border-[#c4d8c9] px-4 py-2 text-sm font-semibold flex items-center gap-1.5"><Plus size={14} />Add video</button>
          <button data-testid="coach-analyze-btn" onClick={analyze} disabled={busy} className="btn-primary px-6 py-2.5 flex items-center gap-2 disabled:opacity-50">
            {busy && <Loader2 size={16} className="animate-spin" />} Plan my next steps
          </button>
        </div>
      </div>
      {doc && <Report doc={doc} />}
    </div>
  );
}
