import axios from "axios";

export const API = `${(process.env.REACT_APP_BACKEND_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000")).replace(/\/$/, "")}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const cfg = err.config || {};
    const authAction = /\/auth\/(login|register|refresh|logout)(?:[/?]|$)/.test(String(cfg.url));
    if (err.response?.status === 401 && !cfg._retry && !authAction) {
      cfg._retry = true;
      refreshing = refreshing || api.post("/auth/refresh").finally(() => { refreshing = null; });
      try { await refreshing; return api(cfg); } catch (e) { /* fall through */ }
    }
    return Promise.reject(err);
  }
);

export function errMsg(e) {
  if (!e?.response) return "We couldn’t reach the studio. Check your connection and try again. Your saved work is safe.";
  if (e.response.status === 429) return e.response.data?.detail || "Please wait a moment before trying again.";
  if (e.response.status >= 500) return "The studio couldn’t finish this request. Please try again shortly. Your saved work is safe.";
  const d = e?.response?.data?.detail;
  if (d == null) return e?.message || "Something went wrong. Please try again.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

export const mediaUrl = (p) => (p ? `${API}/media/${p}` : null);
