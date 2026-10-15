import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Film, Trash2, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useNewProject } from "@/components/AppShell";
import { useLocale } from "@/context/LocaleContext";
import "./Dashboard.css";

export default function Dashboard() {
  const { user } = useAuth();
  const { t } = useLocale();
  const newProject = useNewProject();
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState("");
  const load = useCallback(async (signal) => {
    setBusy(true); setError("");
    try { const { data } = await api.get("/projects/page", { params: { page, size: 12 }, signal }); setResult(data); }
    catch (e) { if (e.code !== "ERR_CANCELED") setError(errMsg(e)); }
    finally { if (!signal?.aborted) setBusy(false); }
  }, [page]);
  useEffect(() => { const c = new AbortController(); load(c.signal); return () => c.abort(); }, [load]);
  const remove = async (id) => {
    if (!window.confirm("Delete this story and its saved video?")) return;
    setDeleting(id);
    try { await api.delete(`/projects/${id}`); if (result.items.length === 1 && page > 1) setPage(page - 1); else await load(); }
    catch (e) { toast.error(errMsg(e)); } finally { setDeleting(""); }
  };
  return <div className="library-page">
    <header className="library-heading"><div><p>{t("dashboard_greeting")}, {user?.name?.split(" ")[0]}</p><h1>{t("my_videos")}</h1><p>One idea at a time. Make something worth sharing.</p></div><button className="btn-primary" onClick={newProject} data-testid="dashboard-new-video-btn"><Plus size={18} />{t("new_video")}</button></header>
    <div className="library-summary"><span><b>{result?.total ?? "–"}</b> {t("projects")}</span><span><b>{result?.ready ?? "–"}</b> {t("videos_ready")}</span><Link to="/coach">{t("growth_coach")} <ArrowRight size={15} /></Link></div>
    {error && <div role="alert" className="library-error">{error}<button onClick={() => load()} className="underline ml-3">Try again</button></div>}
    {busy && <p role="status" className="py-8">Loading your stories…</p>}
    {!busy && !error && result?.items.length === 0 && <section className="library-empty" data-testid="empty-projects"><Film size={32} /><h2>{t("no_videos")}</h2><p>Tell us what should happen. We will help you turn it into a video.</p><button className="btn-primary" onClick={newProject} data-testid="empty-new-video-btn">{t("create_video")}</button></section>}
    {!busy && !error && <div className="library-grid">{result?.items.map(p => <article key={p.id} className="library-story" data-testid={`project-card-${p.id}`}>
      <Link to={`/studio/${p.id}`}><div className="library-image"><img src={p.scenes?.[0]?.image_path ? mediaUrl(p.scenes[0].image_path) : `/styles/${p.style || "storybook"}.jpg`} alt="" loading="lazy" width="200" height="150" /><span>{p.render?.status === "done" ? "Ready to share" : `${t("step")} ${p.step || 1} / 6`}</span></div><h2>{p.title}</h2><p>{p.render?.status === "done" ? "Open video" : t(`step_${p.step || 1}_label`)} <ArrowRight size={14} /></p></Link>
      <button disabled={deleting === p.id} className="library-delete" aria-label={`Delete ${p.title}`} data-testid={`delete-project-${p.id}`} onClick={() => remove(p.id)}><Trash2 size={16} /></button>
    </article>)}</div>}
    {result?.total > 12 && <nav className="library-pagination" aria-label="Story pages"><button className="btn-secondary" disabled={busy || page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} of {Math.ceil(result.total / 12)}</span><button className="btn-secondary" disabled={busy || page * 12 >= result.total} onClick={() => setPage(page + 1)}>Next</button></nav>}
  </div>;
}
