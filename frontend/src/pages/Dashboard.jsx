import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Film, Trash2, Clock } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useNewProject } from "@/components/AppShell";
import { STEPS, STYLES } from "@/constants/studio";

function ProjectCard({ p, onDelete }) {
  const thumb = p.scenes?.find((s) => s.image_path)?.image_path;
  const done = p.render?.status === "done";
  return (
    <div className="group rounded-2xl border border-[#65546B] overflow-hidden bg-[#3A3040] hover:shadow-lg hover:border-cyan-400/40 transition-[box-shadow,border-color]" data-testid={`project-card-${p.id}`}>
      <Link to={`/studio/${p.id}`} className="block">
        <div className="aspect-[4/5] bg-[#181A26] relative overflow-hidden">
          {thumb ? <img src={mediaUrl(thumb)} alt="" className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-500" />
            : <img src={`/styles/${p.style || "storybook"}.jpg`} alt="" className="w-full h-full object-cover opacity-40 grayscale" />}
          <span className={`absolute top-3 left-3 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${done ? "bg-emerald-500 text-white" : "bg-black/60 backdrop-blur text-white"}`}>
            {done ? "Video ready" : `Step ${p.step} · ${STEPS[p.step - 1]?.label}`}
          </span>
        </div>
        <div className="p-4">
          <div className="font-semibold text-white truncate indic">{p.script?.title || p.title}</div>
          <div className="mt-1 text-xs text-slate-300 flex items-center gap-2">
            <span className="uppercase font-mono">{p.language}</span>·<span>{STYLES.find((s) => s.id === p.style)?.label || "No style"}</span>
          </div>
        </div>
      </Link>
      <div className="px-4 pb-4 flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-1"><Clock size={12} />{new Date(p.updated_at).toLocaleDateString()}</span>
        <button data-testid={`delete-project-${p.id}`} onClick={() => onDelete(p.id)} className="text-slate-400 hover:text-rose-400"><Trash2 size={14} /></button>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [items, setItems] = useState(null);
  const [loadError, setLoadError] = useState("");
  const newProject = useNewProject();
  const load = () => api.get("/projects")
    .then((r) => { setItems(r.data); setLoadError(""); })
    .catch((e) => setLoadError(errMsg(e)));
  useEffect(() => { load(); }, []);
  const del = async (id) => {
    if (!window.confirm("Delete this project?")) return;
    await api.delete(`/projects/${id}`); load();
  };
  const ready = items?.filter((p) => p.render?.status === "done").length || 0;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4 rise">
        <div>
          <p className="text-sm text-slate-300">Namaskaram, {user?.name?.split(" ")[0]}</p>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">Your videos</h1>
        </div>
        <button data-testid="dashboard-new-video-btn" onClick={newProject} className="inline-flex items-center gap-2 btn-primary px-5 py-2.5">
          <Plus size={16} /> Create new video
        </button>
      </div>
      <div className="mt-8 grid grid-cols-3 max-w-lg divide-x divide-white/5 rounded-2xl border border-[#65546B] rise rise-1">
        {[["Projects", items?.length ?? "–"], ["Videos ready", ready], ["Plan", user?.plan]].map(([k, v]) => (
          <div key={k} className="p-4"><div className="text-xs text-slate-300">{k}</div><div className="text-xl font-bold capitalize" data-testid={`stat-${k.replace(" ", "-").toLowerCase()}`}>{v}</div></div>
        ))}
      </div>
      {loadError && <div role="alert" className="mt-6 rounded-xl bg-rose-500/15 p-4 text-sm text-rose-100">
        {loadError} <button onClick={load} className="ml-2 font-semibold underline">Try again</button>
      </div>}
      {items && items.length === 0 && (
        <div className="mt-10 rounded-2xl border border-dashed border-[#383D54] p-12 text-center rise rise-2" data-testid="empty-projects">
          <Film className="mx-auto text-slate-300" size={36} />
          <p className="mt-3 font-semibold">No videos yet</p>
          <p className="text-sm text-slate-300">Start with an idea — or let AI find one for you.</p>
          <button onClick={newProject} data-testid="empty-new-video-btn" className="mt-5 btn-primary font-semibold px-5 py-2.5">Start creating</button>
        </div>
      )}
      <div className="mt-10 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        {items?.map((p) => <ProjectCard key={p.id} p={p} onDelete={del} />)}
      </div>
    </div>
  );
}
