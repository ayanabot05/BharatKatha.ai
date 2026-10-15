import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg } from "@/lib/api";
import { toast } from "sonner";
import { useLocale, UI_LANGUAGES } from "@/context/LocaleContext";
import { Globe, LayoutGrid, Plus, TrendingUp, Settings, LogOut, Clapperboard, Menu } from "lucide-react";
import { Magnetic, RamAvatar } from "@/components/fx";

export const Logo = ({ light = false }) => (
  <div className="flex items-center gap-2.5" data-testid="app-logo">
    <div className="relative h-9 w-9 rounded-xl bg-gradient-to-br from-[#d0687d] to-[#b44a63] grid place-items-center shadow-lg shadow-rose-300/40">
      <Clapperboard size={18} className="text-white" />
    </div>
    <div className="leading-tight">
      <div className={`font-display text-lg font-extrabold tracking-tight ${light ? "text-[#4a3f58]" : "text-white"}`}>VidBharat</div>
      <div className={`text-[9px] uppercase tracking-[0.25em] font-mono ${light ? "text-[#8a7a86]" : "text-rose-100"}`}>AI Video Studio</div>
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
    <div className="min-h-screen flex bg-[#faf8f3] text-[#4a3f58]">

      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-[#f0dfd8] bg-[#eef2eb] p-5 sticky top-0 h-screen overflow-hidden">
        <div className="relative"><Logo light /></div>
        <div className="relative mt-8"><Magnetic strength={0.25}>
          <button data-testid="sidebar-new-video-btn" onClick={newProject} className="btn-primary w-full min-w-[184px]"><Plus size={16} /> {t("new_video")}</button>
        </Magnetic></div>
        <nav className="relative mt-5 space-y-1">
          {NAV.map(({ to, key, defaultLabel, icon: Icon, id }) => (
            <NavLink key={to} to={to} data-testid={id}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 ${isActive ? "bg-white text-[#a23f58] border border-[#efd5d6] shadow-sm translate-x-1" : "text-[#7b6a73] hover:text-[#a23f58] hover:bg-white/70 hover:translate-x-0.5 border border-transparent"}`}>
              <Icon size={16} /> {t(key) || defaultLabel}
            </NavLink>
          ))}
        </nav>
        <div className="relative mt-auto space-y-3">
          <div className="flex items-center gap-2.5 rounded-2xl bg-white/70 border border-[#f0dfd8] p-3">
            <RamAvatar state="idle" size={34} />
            <div className="leading-tight"><div className="text-xs font-bold text-[#a23f58]">Ram AI</div><div className="text-[11px] text-[#7b7083]">Ready for your next story</div></div>
          </div>
          <div className="flex items-center justify-between px-1 text-xs text-[#7b7083]">
            <span className="flex items-center gap-1"><Globe size={13} /> UI</span>
            <select aria-label={t("language")} data-testid="ui-lang-switcher" value={locale} onChange={(e) => changeLocale(e.target.value)} className="max-w-32 rounded-lg bg-white px-2 py-1.5 text-xs font-semibold text-[#4a3f58] border border-[#f0dfd8]">
              {UI_LANGUAGES.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
          </div>
          <div className="rounded-2xl border border-[#f0dfd8] bg-white p-4">
            <div className="text-sm font-semibold text-[#4a3f58] truncate" data-testid="sidebar-user-name">{user?.name}</div>
            <div className="text-xs text-[#7b7083] truncate">{user?.email}</div>
            <div className="mt-2 inline-flex rounded-full bg-[#fdeee3] text-[#a2603f] border border-[#f3d9c5] px-2.5 py-0.5 text-[10px] font-mono uppercase tracking-wider" data-testid="sidebar-plan">{user?.plan} plan</div>
            <button data-testid="logout-btn" onClick={logout} className="mt-3 flex items-center gap-2 text-sm text-[#7b7083] hover:text-[#a23f58] transition-colors">
              <LogOut size={14} /> {t("sign_out")}
            </button>
          </div>
        </div>
      </aside>
      <div className="flex-1 min-w-0 relative">
        <header className="md:hidden sticky top-0 z-40 backdrop-blur-xl bg-[#eef2eb]/95 flex items-center justify-between gap-2 border-b border-[#f0dfd8] px-3 sm:px-4 py-3">
          <Logo light />
          <div className="flex items-center gap-2 sm:gap-4 text-[#4a3f58] shrink-0">
            <select aria-label={t("language")} value={locale} onChange={(e) => changeLocale(e.target.value)} className="w-20 rounded-lg bg-white px-1 py-1.5 text-xs text-[#4a3f58] border border-[#f0dfd8]">
              {UI_LANGUAGES.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
            {NAV.map(({ to, icon: Icon, id }) => <NavLink key={to} to={to} data-testid={`m-${id}`} className="hidden sm:inline-flex"><Icon size={18} /></NavLink>)}
            <details className="relative sm:hidden">
              <summary className="list-none rounded-lg p-1.5" aria-label="Open menu"><Menu size={20} /></summary>
              <nav className="absolute right-0 top-10 z-50 w-44 rounded-xl border border-[#f0dfd8] bg-white p-2 shadow-xl">
                {NAV.map(({ to, key, icon: Icon }) => <NavLink key={to} to={to} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm"><Icon size={16} />{t(key)}</NavLink>)}
                <button onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm"><LogOut size={16} />{t("sign_out")}</button>
              </nav>
            </details>
            <button aria-label={t("new_video")} onClick={newProject} data-testid="m-new-video-btn" className="rounded-lg bg-gradient-to-br from-[#d0687d] to-[#b44a63] text-white p-1.5"><Plus size={16} /></button>
          </div>
        </header>
        <main className="relative px-3 sm:px-6 lg:px-8 py-5 sm:py-7 max-w-7xl mx-auto">{children}</main>
      </div>
    </div>
  );
}