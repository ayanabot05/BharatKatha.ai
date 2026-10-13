import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg } from "@/lib/api";
import { toast } from "sonner";
import { useLocale, UI_LANGUAGES } from "@/context/LocaleContext";
import { Globe, LayoutGrid, Plus, TrendingUp, Settings, LogOut, Clapperboard } from "lucide-react";

export const Logo = ({ light = false }) => (
  <div className="flex items-center gap-2.5" data-testid="app-logo">
    <div className="relative h-9 w-9 rounded-xl bg-[#A33D52] grid place-items-center shadow-lg shadow-rose-900/20">
      <Clapperboard size={18} className="text-white" />
    </div>
    <div className="leading-tight">
      <div className={`font-display text-lg font-extrabold tracking-tight ${light ? "text-slate-950" : "text-white"}`}>VidBharat</div>
      <div className={`text-[9px] uppercase tracking-[0.25em] font-mono ${light ? "text-slate-600" : "text-slate-400"}`}>AI Video Studio</div>
    </div>
  </div>
);

const NAV = [
  { to: "/dashboard", key: "my_videos", defaultLabel: "My videos", icon: LayoutGrid, id: "nav-dashboard" },
  { to: "/coach", key: "growth_coach", defaultLabel: "Growth Coach", icon: TrendingUp, id: "nav-coach" },
  { to: "/settings", key: "settings", defaultLabel: "Settings", icon: Settings, id: "nav-settings" },
];

export function useNewProject() {
  const nav = useNavigate();
  return async () => {
    try {
      const { data } = await api.post("/projects", {});
      nav(`/studio/${data.id}`);
    } catch (e) { toast.error(errMsg(e)); }
  };
}

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const { locale, changeLocale, t } = useLocale();
  const newProject = useNewProject();
  return (
    <div className="min-h-screen flex bg-[#261F2C] text-slate-100">
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-white/10 bg-[#342939] p-5 sticky top-0 h-screen overflow-hidden">
        <div className="orb w-64 h-64 bg-rose-700 -bottom-24 -left-24 !opacity-15" />
        <div className="relative"><Logo /></div>
        <button data-testid="sidebar-new-video-btn" onClick={newProject} className="relative btn-primary mt-8 w-full">
          <Plus size={16} /> {t("new_video")}
        </button>
        <nav className="relative mt-6 space-y-1">
          {NAV.map(({ to, key, defaultLabel, icon: Icon, id }) => (
            <NavLink key={to} to={to} data-testid={id}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${isActive ? "bg-white/[0.06] text-white border border-white/10" : "text-slate-400 hover:text-white hover:bg-white/[0.03]"}`}>
              <Icon size={16} /> {t(key) || defaultLabel}
            </NavLink>
          ))}
        </nav>
        <div className="relative mt-auto space-y-3">
          <div className="flex items-center justify-between px-1 text-xs text-slate-300">
            <span className="flex items-center gap-1 text-slate-400"><Globe size={13} /> UI</span>
            <div className="flex gap-1" data-testid="ui-lang-switcher">
              {UI_LANGUAGES.map((l) => (
                <button key={l.id} onClick={() => changeLocale(l.id)}
                  className={`px-1.5 py-0.5 rounded text-[11px] transition-colors ${locale === l.id ? "bg-[#A33D52] text-white font-semibold" : "text-slate-400 hover:text-white"}`}>
                  {l.label}
                </button>
              ))}
            </div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-sm font-semibold text-white truncate" data-testid="sidebar-user-name">{user?.name}</div>
            <div className="text-xs text-slate-300 truncate">{user?.email}</div>
            <div className="mt-2 inline-flex rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 px-2.5 py-0.5 text-[10px] font-mono uppercase tracking-wider" data-testid="sidebar-plan">{user?.plan} plan</div>
            <button data-testid="logout-btn" onClick={logout} className="mt-3 flex items-center gap-2 text-sm text-slate-400 hover:text-white">
              <LogOut size={14} /> {t("sign_out")}
            </button>
          </div>
        </div>
      </aside>
      <div className="flex-1 min-w-0 relative">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-rose-300/10 to-transparent" />
        <header className="md:hidden sticky top-0 z-40 backdrop-blur-xl bg-[#342939]/95 flex items-center justify-between gap-2 border-b border-white/10 px-3 sm:px-4 py-3">
          <Logo />
          <div className="flex items-center gap-2 sm:gap-4 text-slate-100 shrink-0">
            {NAV.map(({ to, icon: Icon, id }) => <NavLink key={to} to={to} data-testid={`m-${id}`}><Icon size={18} /></NavLink>)}
            <button onClick={newProject} data-testid="m-new-video-btn" className="rounded-lg bg-[#A33D52] text-white p-1.5"><Plus size={16} /></button>
          </div>
        </header>
        <main className="relative px-4 sm:px-8 lg:px-12 py-8 max-w-6xl">{children}</main>
      </div>
    </div>
  );
}
