import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, ShieldCheck, ArrowRight } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useSeo } from "@/lib/seo";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Administrator sign-in.
 *
 * Deliberately its own page, with its own credential store on the server, and
 * deliberately not linked from anywhere in the product: a normal visitor never
 * learns that this surface exists. Nothing here touches the user session.
 */
export default function AdminLogin() {
  useSeo({ title: "Administrator sign-in", description: "Administrator access.", path: "/admin/login", noindex: true });
  const [form, setForm] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await api.post("/admin/auth/login", form);
      nav("/admin", { replace: true });
    } catch (e2) {
      setErr(errMsg(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-[#f7e0cf] px-5 py-10 text-[#263b36]">
      <div className="w-full max-w-sm rounded-2xl border border-[#e8c7a6] bg-[#fbd3b4] p-7 shadow-xl shadow-[#e8c7a6]/50">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-xl" style={{ backgroundColor: "#a33d52" }}>
            <ShieldCheck size={18} color="#ffe6cf" />
          </span>
          <div className="leading-tight">
            <div className="font-bold">BharatChitra AI</div>
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#7a5f52]">Administrator</div>
          </div>
        </div>

        <form onSubmit={submit} className="mt-7 space-y-4" data-testid="admin-login-form">
          <p className="text-xs text-[#7a5f52]">
            This is a separate sign-in. It is not your studio account and is not linked anywhere on the site.
          </p>
          <div className="space-y-1.5">
            <Label className="text-[#7a5f52]" htmlFor="admin-email">Administrator email</Label>
            <Input id="admin-email" data-testid="admin-email-input" type="email" required
                   value={form.email} onChange={set("email")} className="h-11 bg-[#fbe4cd]" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-[#7a5f52]" htmlFor="admin-password">Password</Label>
            <Input id="admin-password" data-testid="admin-password-input" type="password" required
                   value={form.password} onChange={set("password")} className="h-11 bg-[#fbe4cd]" />
          </div>
          {err && (
            <div data-testid="admin-login-error" role="alert"
                 className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-900">
              {err}
            </div>
          )}
          <button data-testid="admin-login-btn" disabled={busy} className="btn-primary w-full">
            {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />} Sign in
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-[#7a5f52]">
          Looking for your studio? <Link className="font-semibold text-[#a33d52]" to="/login">Use the normal sign-in</Link>
        </p>
      </div>
    </div>
  );
}
