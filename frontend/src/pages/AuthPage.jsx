import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, ArrowRight } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Logo } from "@/components/AppShell";
import PhoneShort from "@/components/PhoneShort";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AuthPage({ mode }) {
  const isLogin = mode === "login";
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const { setUser } = useAuth();
  const nav = useNavigate();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const body = isLogin ? { email: form.email, password: form.password } : form;
      const { data } = await api.post(`/auth/${isLogin ? "login" : "register"}`, body);
      setUser(data);
      nav("/dashboard");
    } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#f7f3e9] text-[#263b36]">
      <div className="relative flex flex-col p-6 sm:p-10 overflow-hidden">
        <Link to="/" className="relative"><Logo light /></Link>
        <form onSubmit={submit} className="relative m-auto w-full max-w-sm space-y-5 rise" data-testid="auth-form">
          <div>
            <div className="label">{isLogin ? "Welcome back" : "Free plan · no card"}</div>
            <h1 className="mt-2 text-4xl font-black tracking-tight">{isLogin ? "Sign in to your studio" : "Create your studio"}</h1>
          </div>
          {!isLogin && (
            <div className="space-y-1.5"><Label className="text-[#587168]">Name</Label><Input data-testid="auth-name-input" value={form.name} onChange={set("name")} required className="h-11 bg-white" /></div>
          )}
          <div className="space-y-1.5"><Label className="text-[#587168]">Email</Label><Input data-testid="auth-email-input" type="email" value={form.email} onChange={set("email")} required className="h-11 bg-white" /></div>
          <div className="space-y-1.5"><Label className="text-[#587168]">Password</Label><Input data-testid="auth-password-input" type="password" minLength={6} value={form.password} onChange={set("password")} required className="h-11 bg-white" /></div>
          {err && <div data-testid="auth-error" className="text-sm text-rose-800 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2">{err}</div>}
          <button data-testid="auth-submit-btn" disabled={busy} className="btn-primary w-full">
            {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />} {isLogin ? "Sign in" : "Create account"}
          </button>
          <p className="text-sm text-center text-[#587168]">
            {isLogin ? "New here? " : "Already have an account? "}
            <Link data-testid="auth-switch-link" className="font-semibold text-teal-800" to={isLogin ? "/register" : "/login"}>{isLogin ? "Create an account" : "Sign in"}</Link>
          </p>
        </form>
      </div>
      <div className="hidden lg:flex relative items-center justify-center bg-[#e7efe7] border-l border-[#d6e2d7] grid-bg overflow-hidden">
        <div className="relative flex flex-col items-center gap-8">
          <PhoneShort />
          <div className="text-center">
            <p className="indic text-2xl font-bold">కథ మీది. వీడియో మాది.</p>
            <p className="text-[#587168] text-sm mt-1">Your story. We make the video.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
