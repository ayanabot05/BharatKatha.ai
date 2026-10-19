import { useRef, useState } from "react";
import { Lightbulb, Sparkles, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { StepHeader, StepArrow } from "@/components/StepHeader";
import { LANGUAGES, TONES, CATEGORIES, PLATFORMS } from "@/constants/studio";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useLocale } from "@/context/LocaleContext";

const Pick = ({ value, onChange, items, testid, label }) => (
  <div className="space-y-1.5">
    <div className="text-xs font-semibold uppercase tracking-wider text-[#587168]">{label}</div>
    <Select value={String(value)} onValueChange={onChange}>
      <SelectTrigger data-testid={testid} className="bg-[#f5f9f4]"><SelectValue /></SelectTrigger>
      <SelectContent>{items.map((i) => <SelectItem key={i.v} value={String(i.v)} disabled={i.disabled}>{i.l}</SelectItem>)}</SelectContent>
    </Select>
  </div>
);

const REGIONS = ["Andhra Pradesh", "Telangana", "Tamil Nadu", "Karnataka", "Kerala", "Maharashtra", "Gujarat", "West Bengal", "Odisha", "India"];
const AUDIENCES = ["Families & kids", "Children", "Young adults", "Adults", "Everyone"];

function CustomPick({ value, onChange, options, label, testid, placeholder }) {
  const { t } = useLocale();
  const [custom, setCustom] = useState(!options.includes(value));
  return <div className="space-y-2">
    <Pick label={label} testid={`${testid}-select`} value={custom ? "__other__" : value}
      onChange={(next) => { setCustom(next === "__other__"); onChange(next === "__other__" ? "" : next); }}
      items={[...options.map((item) => ({ v: item, l: t(item) })), { v: "__other__", l: t("Other") }]} />
    {custom && <Input aria-label={placeholder} data-testid={`${testid}-input`} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />}
  </div>;
}

function EntryCard({ icon: Icon, title, sub, active, onClick, testid }) {
  return (
    <button data-testid={testid} onClick={onClick}
      className={`rounded-2xl p-6 text-center border bg-[#f5f9f4] transition-[border-color,box-shadow,transform] hover:-translate-y-0.5 hover:shadow-md ${active ? "border-violet-500 ring-4 ring-violet-500/20" : "border-[#d6e2d7] hover:border-amber-400"}`}>
      <Icon className="mx-auto text-[#263b36]" size={22} />
      <div className="mt-3 text-lg font-semibold text-[#263b36]">{title}</div>
      <div className="text-sm text-[#587168]">{sub}</div>
    </button>
  );
}

export default function StepIdea({ project, update }) {
  const { t, locale, changeLocale } = useLocale();
  const [mode, setMode] = useState(project.idea ? "have" : null);
  const [cfg, setCfg] = useState({ language: project.language || "te", region: project.region || "Andhra Pradesh", duration: project.duration || 45, tone: project.tone || "Emotional" });
  const [idea, setIdea] = useState(project.idea || "");
  const [find, setFind] = useState({ category: project.brief?.category || CATEGORIES[0], platform: project.brief?.platform || PLATFORMS[0], audience: project.brief?.audience || "Families & kids" });
  const [ideas, setIdeas] = useState([]);
  const [trends, setTrends] = useState([]);
  const [trendNote, setTrendNote] = useState("");
  const [busy, setBusy] = useState("");
  const trendRequest = useRef(0);
  const writing = useRef(false);
  const clearTrends = () => { trendRequest.current += 1; setTrends([]); setTrendNote(""); };

  const suggest = async () => {
    setBusy("ideas");
    try {
      const { data } = await api.post("/ideas/suggest", { ...find, language: cfg.language, region: cfg.region });
      setIdeas(data.ideas);
    } catch (e) { toast.error(t(errMsg(e))); } finally { setBusy(""); }
  };
  const loadTrends = async () => {
    const request = ++trendRequest.current;
    setBusy("trends");
    try {
      const { data } = await api.get("/ideas/trending", { params: {
        language: cfg.language, region: cfg.region, category: find.category, audience: find.audience,
      } });
      if (request === trendRequest.current) {
        setTrends(data.items || []); setTrendNote(data.note || "");
      }
    } catch (e) { if (request === trendRequest.current) toast.error(t(errMsg(e))); } finally { setBusy(""); }
  };

  const write = async (text, key = "custom") => {
    if (busy || writing.current) return;
    if (!text || text.trim().length < 3) return toast.error(t("Describe your idea first"));
    writing.current = true;
    setBusy(`script-${key}`);
    try {
      const { data } = await api.post(`/projects/${project.id}/script/generate`, { idea: text, ...find, ...cfg, duration: Number(cfg.duration) });
      toast.success(t("Script ready — review it with the AI agents"));
      update(data, 2);
    } catch (e) { toast.error(t(errMsg(e))); } finally { writing.current = false; setBusy(""); }
  };

  return (
    <section className="rounded-3xl border border-[#d6e2d7] bg-white backdrop-blur-xl shadow-2xl shadow-[#c7d8ca]/30 p-5 sm:p-8">
      <StepHeader n={1} title="Start creating with Ram AI" pill="Ram AI 1.0" />
      <div className="mt-6 grid sm:grid-cols-2 gap-4">
        <EntryCard testid="entry-have-idea" icon={Lightbulb} title={t("have_idea")} sub={t("Describe your concept")} active={mode === "have"} onClick={() => setMode("have")} />
        <EntryCard testid="entry-find-idea" icon={Sparkles} title={t("find_idea")} sub={t("Ram AI suggests regional hooks")} active={mode === "find"} onClick={() => setMode("find")} />
      </div>

      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
        <Pick label={t("language")} testid="idea-language-select" value={cfg.language} onChange={(v) => { setCfg({ ...cfg, language: v }); changeLocale(v); clearTrends(); }} items={LANGUAGES.map((l) => ({ v: l.id, l: `${locale === "en" ? `${l.native} · ${l.label}` : l.native}${l.id === "or" ? " · record your own voice" : ""}` }))} />
        <CustomPick label={t("region")} testid="idea-region" value={cfg.region} options={REGIONS} placeholder={t("Enter your region")} onChange={(region) => { setCfg({ ...cfg, region }); clearTrends(); }} />
        <Pick label={t("length")} testid="idea-duration-select" value={cfg.duration} onChange={(v) => setCfg({ ...cfg, duration: v })} items={[30, 45, 60, 75].map((d) => ({ v: d, l: `${d} ${t("seconds")}` }))} />
        <Pick label={t("tone")} testid="idea-tone-select" value={cfg.tone} onChange={(v) => setCfg({ ...cfg, tone: v })} items={TONES.map((item) => ({ v: item, l: t(item) }))} />
      </div>

          <div className="mt-4 mb-6 grid sm:grid-cols-3 gap-3">
            <Pick label={t("Category")} testid="find-category-select" value={find.category} onChange={(v) => { setFind({ ...find, category: v }); clearTrends(); }} items={CATEGORIES.map((c) => ({ v: c, l: t(c) }))} />
            <Pick label={t("Platform")} testid="find-platform-select" value={find.platform} onChange={(v) => setFind({ ...find, platform: v })} items={PLATFORMS.map((c) => ({ v: c, l: t(c) }))} />
            <CustomPick label={t("Audience")} testid="find-audience" value={find.audience} options={AUDIENCES} placeholder={t("Enter your audience")} onChange={(audience) => { setFind({ ...find, audience }); clearTrends(); }} />
          </div>
      <p className="mt-3 text-sm text-[#587168]"> {t("Length is a guide. We keep your story concise and allow a little extra time for a complete ending.")} </p>
      {mode === "have" && (
        <div className="mt-6 rise">
          <Textarea data-testid="idea-textarea" rows={4} value={idea} onChange={(e) => setIdea(e.target.value)} className="indic bg-[#f5f9f4] text-base"
            placeholder={t("e.g. A poor village boy finds a talking cow that teaches him honesty… (any language)")} />
          <button data-testid="write-script-btn" onClick={() => write(idea, "custom")} disabled={!!busy}
            className="mt-4 inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-60">
            {busy === "script-custom" ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />} {busy === "script-custom" ? t("Ram AI is writing your story…") : t("write_script")}
          </button>
        </div>
      )}

      {mode === "find" && (
        <div className="mt-6 rise">
          <div className="mb-6 rounded-2xl border border-cyan-500/30 bg-cyan-500/5 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><div className="font-semibold"> {t("Recent videos for your topic")} </div><p className="text-xs text-[#587168]"> {t("Search YouTube using your language and story category. Use the ideas to make an original story.")} </p></div>
              <button onClick={loadTrends} disabled={!!busy} className="rounded-full border border-cyan-400 px-4 py-2 text-sm text-teal-800 disabled:opacity-40">{busy === "trends" ? t("Loading…") : t("Find relevant videos")}</button>
            </div>
            {trendNote && <p className="mt-3 text-xs text-[#61736d]">{trendNote}</p>}
            {trends.length > 0 && <div className="mt-4 grid gap-2 sm:grid-cols-2 max-h-80 overflow-y-auto">
              {trends.map((video) => <div key={video.id} className="rounded-xl bg-[#f5f9f4] p-3 text-sm">
                <a href={video.url} target="_blank" rel="noopener noreferrer" className="font-medium text-teal-800 hover:underline">{video.title}</a>
                <p className="mt-1 text-xs text-[#587168]">{video.channel} · {video.views.toLocaleString()} views {video.language ? `· tagged ${video.language}` : ""}</p>
                <button onClick={() => { setIdea(`Create an original ${cfg.language} video for ${cfg.region} inspired by the broad topic of: ${video.title}. Do not copy its script, characters, or visuals.`); setMode("have"); }} className="mt-2 text-xs font-semibold text-violet-800"> {t("Use this topic as inspiration →")} </button>
              </div>)}
            </div>}
          </div>
          <button data-testid="suggest-ideas-btn" onClick={suggest} disabled={!!busy}
            className="mt-4 inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-60">
            {busy === "ideas" ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} {t("Suggest 6 ideas")} </button>
          <p className="mt-2 text-xs text-[#61736d]"> {t("AI-suggested from regional knowledge — not live trending data yet.")} </p>
          <div className="mt-6 grid md:grid-cols-2 gap-3">
            {ideas.map((it, i) => {
              const title = it.title || it.title_en || "Untitled";
              const titleEn = it.title_en || it.title || "";
              const logline = it.logline || it.description || it.summary || "";
              const hook = it.hook || "";
              const payoff = it.payoff || "";
              const why = it.why_it_works || it.why || "";
              const fullIdea = [
                `Selected story: ${titleEn || title}`,
                logline ? `Story promise: ${logline}` : "",
                hook ? `Opening question or hook: ${hook}` : "",
                payoff ? `Required payoff: ${payoff}` : "",
              ].filter(Boolean).join("\n");
              return (
                <div key={i} className="rounded-2xl border border-[#d6e2d7] p-5 bg-[#f5f9f4] rise" data-testid={`idea-card-${i}`}>
                  <div className="indic font-bold text-[#263b36]">{title}</div>
                  {locale === "en" && titleEn && titleEn !== title && <div className="text-xs text-[#587168]">{titleEn}</div>}
                  {logline && <p className="indic mt-2 text-sm text-[#587168]">{logline}</p>}
                  {payoff && <p className="indic mt-2 text-xs text-teal-800">{t("Payoff")}: {payoff}</p>}
                  {why && <p className="mt-2 text-xs text-violet-800 bg-violet-500/10 rounded-lg px-2.5 py-1.5">{t("Why")}: {why}</p>}
                  <button data-testid={`use-idea-btn-${i}`} disabled={!!busy} onClick={() => { setIdea(fullIdea); write(fullIdea, i); }}
                    className="mt-3 text-sm font-semibold text-violet-800 hover:text-violet-800 inline-flex items-center gap-1 disabled:opacity-50"> {busy === `script-${i}` ? <><Loader2 size={14} className="animate-spin" /> {t("Writing your script…")}</> : <>{t("Use this idea")} <ArrowRight size={14} /></>}
                  </button>
                </div>
              );
            })}
          </div>
          {busy?.startsWith("script") && <div className="mt-4 flex items-center gap-2 text-sm text-[#61736d]"><Loader2 size={14} className="animate-spin" /> {t("Writing your script…")} </div>}
        </div>
      )}
      <StepArrow />
      <div className="text-center text-sm text-[#61736d]"> {t("Next: AI Script Studio")} </div>
    </section>
  );
}
