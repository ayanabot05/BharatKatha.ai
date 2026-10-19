import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, ShieldAlert } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useSeo } from "@/lib/seo";
import { SUPPORT_EMAIL } from "@/lib/site";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Choose a new password with a one-time token from the emailed link.
 *
 * The token is single use: a successful reset invalidates it and every other
 * outstanding link for the account, so a forwarded email is useless afterwards.
 */
export default function ResetPassword() {
  useSeo({ title: "Choose a new password", path: "/reset-password", noindex: true });
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [form, setForm] = useState({ password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (form.password !== form.confirm) { setErr("Those two passwords do not match."); return; }
    setBusy(true);
    try {
      await api.post("/auth/reset", { token, password: form.password });
      setDone(true);
    } catch (e2) {
      setErr(errMsg(e2));
    } finally {
      setBusy(false);
    }
  };

  const shell = (children) => (
    <div className="min-h-screen grid place-items-center bg-[#f7e0cf] px-5 py-10 text-[#263b36]">
      <div className="w-full max-w-md rounded-2xl border border-[#e8c7a6] bg-[#fbd3b4] p-7 shadow-xl shadow-[#e8c7a6]/50">
        {children}
      </div>
    </div>
  );

  if (!token) {
    return shell(
      <div data-testid="reset-no-token" className="space-y-3">
        <span className="grid h-11 w-11 place-items-center rounded-xl" style={{ backgroundColor: "#a33d52" }}>
          <ShieldAlert size={20} color="#ffe6cf" />
        </span>
        <h1 className="text-2xl font-black tracking-tight">This link is incomplete</h1>
        <p className="text-sm text-[#7a5f52]">
          The reset link is missing its token. Request a fresh one, or write to{" "}
          <a className="font-semibold text-[#a33d52]" href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
        </p>
        <Link className="btn-primary inline-flex" to="/forgot-password">Request a new link</Link>
      </div>
    );
  }

  if (done) {
    return shell(
      <div data-testid="reset-done" className="space-y-3">
        <span className="grid h-11 w-11 place-items-center rounded-xl" style={{ backgroundColor: "#a33d52" }}>
          <CheckCircle2 size={20} color="#ffe6cf" />
        </span>
        <h1 className="text-2xl font-black tracking-tight">Password changed</h1>
        <p className="text-sm text-[#7a5f52]">
          You can sign in with your new password now. Any other reset links you were sent have stopped working.
        </p>
        <Link className="btn-primary inline-flex" to="/login" data-testid="reset-go-login">Sign in</Link>
      </div>
    );
  }

  return shell(
    <form onSubmit={submit} className="space-y-5" data-testid="reset-form">
      <div>
        <div className="label">Password reset</div>
        <h1 className="mt-2 text-3xl font-black tracking-tight">Choose a new password</h1>
      </div>
      <div className="space-y-1.5">
        <Label className="text-[#7a5f52]" htmlFor="reset-password">New password</Label>
        <Input id="reset-password" data-testid="reset-password-input" type="password" minLength={6} required
               value={form.password} onChange={set("password")} className="h-11 bg-[#fbe4cd]" />
      </div>
      <div className="space-y-1.5">
        <Label className="text-[#7a5f52]" htmlFor="reset-confirm">Repeat password</Label>
        <Input id="reset-confirm" data-testid="reset-confirm-input" type="password" minLength={6} required
               value={form.confirm} onChange={set("confirm")} className="h-11 bg-[#fbe4cd]" />
      </div>
      {err && <div data-testid="reset-error" role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-900">{err}</div>}
      <button data-testid="reset-submit-btn" disabled={busy} className="btn-primary w-full">
        {busy ? <Loader2 size={16} className="animate-spin" /> : null} Set new password
      </button>
      <p className="text-center text-xs text-[#7a5f52]">
        <Link className="font-semibold text-[#a33d52]" to="/forgot-password">Request a different link</Link>
      </p>
    </form>
  );
}
