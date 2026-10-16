import { createContext, useContext, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useLocale } from "./LocaleContext";

const ProjectCopyContext = createContext(null);
const cache = new Map();
const needsTranslation = (value, locale) => {
  if (locale === "en" || typeof value !== "string") return false;
  const letters = value.match(/\p{L}/gu) || [];
  return letters.length > 0 && letters.filter((c) => /[a-z]/i.test(c)).length / letters.length > 0.5;
};

export function ProjectCopyProvider({ project, enabled, children }) {
  const { locale, t } = useLocale();
  const contract = project.content_contract || {};
  const script = project.script || {};
  const sources = [...new Set([
    contract.promise, script.story,
    ...(contract.requirements || []).map((item) => item.requirement),
    ...(project.scenes || []).map((s) => s.visual), ...(script.scenes || []).map((s) => s.visual),
    ...(project.validation?.agents || []).flatMap((agent) => [agent.verdict, ...(agent.fixes || []), ...(agent.misses || []),
      ...(agent.requirements || []).flatMap((item) => [item.source, ...(item.evidence || []).map((e) => e.quote)])]),
    ...(project.validation?.content_gaps || []),
  ].filter((value) => needsTranslation(value, locale)))];
  const signature = JSON.stringify([project.id, locale, sources]);
  const [result, setResult] = useState({ key: "", translations: {} });
  const [failed, setFailed] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [originalKey, setOriginalKey] = useState("");
  const required = enabled && sources.length > 0;
  useEffect(() => {
    if (!required) return undefined;
    let active = true;
    if (cache.has(signature)) { setResult({ key: signature, translations: cache.get(signature) }); return undefined; }
    setFailed("");
    api.get(`/projects/${project.id}/display-copy`, { params: { language: locale }, timeout: 100000 })
      .then(({ data }) => {
        if (!active) return;
        const translations = data.translations || {};
        const requested = JSON.parse(signature)[2];
        if (!requested.every((source) => typeof translations[source] === "string" && translations[source].trim())) throw new Error("Incomplete translation");
        cache.set(signature, translations);
        if (cache.size > 20) cache.delete(cache.keys().next().value);
        setResult({ key: signature, translations });
      }).catch(() => { if (active) setFailed(signature); });
    return () => { active = false; };
  }, [signature, required, project.id, locale, attempt]);
  const translations = result.key === signature ? result.translations : cache.get(signature) || {};
  const pending = (value) => required && originalKey !== signature && sources.includes(value) && !translations[value];
  const display = (value) => pending(value) ? t(failed === signature ? "Translation unavailable" : "Translating…") : (originalKey !== signature && translations[value]) || value;
  const loading = required && originalKey !== signature && sources.some(pending);
  return <ProjectCopyContext.Provider value={{ display, pending }}>
    {loading && <div role="status" className="mb-4 rounded-xl border border-teal-200 bg-teal-50 p-3 text-sm text-teal-900">
      {failed === signature ? <>
        <p>{t("Translation is unavailable. Your saved story is unchanged.")}</p>
        <button className="mt-2 mr-4 underline" onClick={() => setAttempt((n) => n + 1)}>{t("Try again")}</button>
        <button className="mt-2 underline" onClick={() => setOriginalKey(signature)}>{t("Show original text")}</button>
      </> : <span className="flex items-center gap-2"><Loader2 size={16} className="animate-spin" />{t("Translating scene descriptions and story details…")}</span>}
    </div>}
    {children}
  </ProjectCopyContext.Provider>;
}

export const useProjectCopy = () => useContext(ProjectCopyContext) || { display: (value) => value, pending: () => false };
