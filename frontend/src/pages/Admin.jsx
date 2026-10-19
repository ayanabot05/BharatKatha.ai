import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, RefreshCw, Search, ShieldCheck, LogOut } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useSeo } from "@/lib/seo";
import { toast } from "@/components/ui/sonner";
import "@/components/Pricing.css";

const TABS = [
  { id: "users", label: "Users" },
  { id: "growth", label: "Growth" },
  { id: "waitlist", label: "Waitlist" },
  { id: "payments", label: "Payments" },
  { id: "audit", label: "Activity" },
];

const PLAN_IDS = ["free", "creator", "studio"];

function money(minor, currency) {
  const value = (minor || 0) / 100;
  const symbol = currency === "INR" ? "₹" : "$";
  return `${symbol}${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function when(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function pct(value) {
  return value === null || value === undefined ? "—" : `${value}%`;
}

/**
 * Operator dashboard.
 *
 * This is a separate surface with a separate session: it authenticates against
 * `/admin/auth/*` and is not reachable from the user experience at all. Any 401
 * — an expired cookie included — sends the operator back to /admin/login rather
 * than showing a half-loaded page.
 */
export default function Admin() {
  useSeo({ title: "Admin", description: "Operator dashboard.", path: "/admin", noindex: true });
  const nav = useNavigate();
  const [admin, setAdmin] = useState(null);
  const [checking, setChecking] = useState(true);
  const [overview, setOverview] = useState(null);
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [audit, setAudit] = useState([]);
  const [growth, setGrowth] = useState(null);
  const [signups, setSignups] = useState([]);
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState("");
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadAll = useCallback(async () => {
    setError("");
    try {
      const [me, ov, us, pay, au, gr, wl] = await Promise.all([
        api.get("/admin/auth/me"),
        api.get("/admin/overview"),
        api.get("/admin/users", { params: { limit: 50 } }),
        api.get("/admin/payments", { params: { limit: 50 } }),
        api.get("/admin/audit", { params: { limit: 30 } }),
        api.get("/admin/growth", { params: { days: 30 } }),
        api.get("/admin/signups", { params: { limit: 100 } }),
      ]);
      setAdmin(me.data);
      setOverview(ov.data);
      setUsers(us.data?.users || []);
      setPayments(pay.data?.payments || []);
      setAudit(au.data?.audit || []);
      setGrowth(gr.data || null);
      setSignups(wl.data?.signups || []);
    } catch (e) {
      if (e?.response?.status === 401) {
        nav("/admin/login", { replace: true });
        return;
      }
      setError(errMsg(e));
    } finally {
      setChecking(false);
      setLoading(false);
    }
  }, [nav]);

  useEffect(() => { loadAll(); }, [loadAll]);

  async function signOut() {
    try { await api.post("/admin/auth/logout"); } catch { /* the cookie may already be gone */ }
    nav("/admin/login", { replace: true });
  }

  async function searchUsers(e) {
    e?.preventDefault?.();
    setBusy("search");
    try {
      const res = await api.get("/admin/users", { params: { search, plan: planFilter, limit: 50 } });
      setUsers(res.data?.users || []);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy("");
    }
  }

  async function changePlan(userId, plan) {
    setBusy(userId);
    try {
      await api.post(`/admin/users/${userId}/plan`, { plan, status: "active" });
      setUsers((rows) => rows.map((r) => (r.id === userId ? { ...r, plan, status: "active" } : r)));
      toast.success(`Plan changed to ${plan}.`);
      const ov = await api.get("/admin/overview");
      setOverview(ov.data);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy("");
    }
  }

  if (checking) {
    return (
      <div className="admin">
        <p className="admin-sub"><Loader2 size={15} className="animate-spin" style={{ verticalAlign: "-3px" }} /> Checking your administrator session…</p>
      </div>
    );
  }

  const stages = growth?.funnel?.stages || [];
  const series = growth?.daily?.series || {};
  const dayKeys = Object.keys(series).sort();
  const maxVisits = Math.max(1, ...dayKeys.map((d) => Number(series[d]?.visit || 0)));

  return (
    <div className="admin">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1><ShieldCheck size={22} aria-hidden style={{ verticalAlign: "-4px", marginRight: 8, color: "#a33d52" }} />Admin</h1>
          <p className="admin-sub">
            Accounts, plans, payments and the growth funnel in one place.
            {admin?.email ? <> Signed in as <b>{admin.email}</b>.</> : null}
          </p>
        </div>
        <div className="admin-actions">
          <button type="button" className="btn-secondary" onClick={loadAll} disabled={loading}>
            {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />} Refresh
          </button>
          <button type="button" className="btn-secondary" onClick={signOut} data-testid="admin-logout-btn">
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </div>

      {error && <div className="pricing-error" role="alert">{error}</div>}

      {overview && (
        <>
          <div className="admin-stats">
            <div className="admin-stat"><span>Users</span><strong>{overview.users}</strong></div>
            <div className="admin-stat"><span>New this week</span><strong>{overview.new_users_7d}</strong></div>
            <div className="admin-stat"><span>Projects</span><strong>{overview.projects}</strong></div>
            <div className="admin-stat"><span>Videos rendered</span><strong>{overview.videos_rendered}</strong></div>
            <div className="admin-stat"><span>Paid subscriptions</span><strong>{overview.paid_count}</strong></div>
            <div className="admin-stat">
              <span>Early access</span>
              <strong>{signups.length}</strong>
            </div>
          </div>

          {!overview.billing_tables_ready && (
            <div className="admin-warn">
              Billing tables are not created yet, so plan changes are recorded on the account
              but subscriptions and payments cannot be listed. Run
              <code> python migrate.py</code> (migrations live in <code>backend/migrations/</code>)
              to switch on the full dashboard.
            </div>
          )}

          {overview.plans && Object.keys(overview.plans).length > 0 && (
            <div className="admin-tiles">
              {Object.entries(overview.plans).map(([plan, count]) => (
                <div className="admin-tile" key={plan}>
                  <h3>{plan}</h3>
                  <div className="admin-kv"><span>Active subscriptions</span><b>{count}</b></div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <div className="admin-tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-pressed={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "growth" && (
        <>
          <p className="admin-sub" data-testid="growth-window">
            Last {growth?.funnel?.days || 30} days. Recorded on this server — first-party only, no third-party scripts.
            “People” counts distinct signed-in accounts, so it never double-counts one person.
          </p>

          {growth && !growth.funnel?.tables_ready && (
            <div className="admin-warn">
              The analytics table is missing, so nothing has been recorded. Run <code> python migrate.py</code>.
            </div>
          )}

          <div className="admin-table-wrap" style={{ marginTop: 16 }}>
            <table className="admin-table" data-testid="growth-funnel">
              <thead>
                <tr><th>Stage</th><th>Events</th><th>People</th><th>From previous</th><th>From visits</th><th>Share</th></tr>
              </thead>
              <tbody>
                {stages.length === 0 && <tr><td colSpan={6} className="admin-empty">No events recorded in this window yet.</td></tr>}
                {stages.map((s) => (
                  <tr key={s.name}>
                    <td>{s.label}</td>
                    <td>{s.events}</td>
                    <td>{s.people}</td>
                    <td>{pct(s.from_previous_pct)}</td>
                    <td>{pct(s.from_top_pct)}</td>
                    <td>
                      <span className="admin-bar-track">
                        <span className="admin-bar" style={{ width: `${Math.min(100, Number(s.from_top_pct || 0))}%` }} />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {dayKeys.length > 0 && (
            <div className="admin-spark-wrap">
              <h3>Landing visits per day</h3>
              <p>{dayKeys.length} day{dayKeys.length === 1 ? "" : "s"} with activity · peak {maxVisits}</p>
              <div className="admin-spark" role="img" aria-label="Landing visits per day">
                {dayKeys.map((d) => (
                  <i key={d} title={`${d}: ${series[d]?.visit || 0}`}
                     style={{ height: `${Math.max(3, Math.round((Number(series[d]?.visit || 0) / maxVisits) * 100))}%` }} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {tab === "waitlist" && (
        <div className="admin-table-wrap" style={{ marginTop: 16 }}>
          <p className="admin-sub">People who asked to be told when full AI video motion goes live.</p>
          <table className="admin-table" data-testid="waitlist-table">
            <thead>
              <tr><th>When</th><th>Email</th><th>Topic</th><th>From</th><th>Note</th></tr>
            </thead>
            <tbody>
              {signups.length === 0 && <tr><td colSpan={5} className="admin-empty">No early-access sign-ups yet.</td></tr>}
              {signups.map((s) => (
                <tr key={s.id}>
                  <td>{when(s.created_at)}</td>
                  <td>{s.email}</td>
                  <td>{s.topic}</td>
                  <td>{s.source || "—"}</td>
                  <td>{s.note || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "users" && (
        <>
          <form className="admin-search" onSubmit={searchUsers}>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by email or name" aria-label="Search users" />
            <select value={planFilter} onChange={(e) => setPlanFilter(e.target.value)} aria-label="Filter by plan">
              <option value="">All plans</option>
              {PLAN_IDS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <button type="submit" disabled={busy === "search"}>
              {busy === "search" ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} Search
            </button>
          </form>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr><th>Email</th><th>Name</th><th>Plan</th><th>Status</th><th>Videos</th><th>Joined</th><th>Change plan</th></tr>
              </thead>
              <tbody>
                {users.length === 0 && <tr><td colSpan={7} className="admin-empty">No accounts match this search.</td></tr>}
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td>{u.name || "—"}</td>
                    <td><span className={`admin-pill${u.plan !== "free" ? " admin-pill--paid" : ""}`}>{u.plan}</span></td>
                    <td>{u.status || "active"}</td>
                    <td>{u.rendered ?? 0} / {u.projects ?? 0}</td>
                    <td>{when(u.created_at)}</td>
                    <td>
                      <select
                        value={u.plan}
                        disabled={busy === u.id}
                        aria-label={`Change plan for ${u.email}`}
                        onChange={(e) => changePlan(u.id, e.target.value)}
                      >
                        {PLAN_IDS.map((p) => <option key={p} value={p}>{p}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "payments" && (
        <div className="admin-table-wrap" style={{ marginTop: 16 }}>
          <table className="admin-table">
            <thead>
              <tr><th>When</th><th>Email</th><th>Provider</th><th>Plan</th><th>Interval</th><th>Amount</th><th>Status</th></tr>
            </thead>
            <tbody>
              {payments.length === 0 && <tr><td colSpan={7} className="admin-empty">No payments recorded yet.</td></tr>}
              {payments.map((p) => (
                <tr key={p.id}>
                  <td>{when(p.created_at)}</td>
                  <td>{p.email || p.user_id || "—"}</td>
                  <td>{p.provider || "—"}</td>
                  <td>{p.plan || "—"}</td>
                  <td>{p.interval || "—"}</td>
                  <td>{money(p.amount, p.currency)}</td>
                  <td><span className={`admin-pill${p.status === "paid" ? " admin-pill--paid" : ""}`}>{p.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "audit" && (
        <div className="admin-table-wrap" style={{ marginTop: 16 }}>
          <table className="admin-table">
            <thead>
              <tr><th>When</th><th>Action</th><th>Target</th><th>Detail</th></tr>
            </thead>
            <tbody>
              {audit.length === 0 && <tr><td colSpan={4} className="admin-empty">No admin actions yet.</td></tr>}
              {audit.map((a) => (
                <tr key={a.id}>
                  <td>{when(a.created_at)}</td>
                  <td>{a.action}</td>
                  <td>{a.target_user_id || "—"}</td>
                  <td>{typeof a.detail === "string" ? a.detail : JSON.stringify(a.detail || {})}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
