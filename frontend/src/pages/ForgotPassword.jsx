import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2, MailCheck } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useSeo } from "@/lib/seo";
import { SUPPORT_EMAIL } from "@/lib/site";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Ask for a reset link.
 *
 * The server never reveals whether an address has an account, and it reports
 * how the link will actually reach the person. When email delivery is not
 * configured yet the page says so plainly and points at support, instead of
 * telling someone to check an inbox that will stay empty.
 */
export default function ForgotPassword() {
  useSeo({ title: "Reset your password", path: "/forgot-password", description: "Reset your BharatChitra AI password." });
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [outcome, setOutcome] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const { data } = await api.post("/auth/forgot", { email });
      setOutcome(data?.delivery || "manual");
    } catch (e2) {
      setErr(errMsg(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-[#f7e0cf] px-5 py-10 text-[#263b36]">
      <div className="w-full max-w-md rounded-2xl border border-[#e8c7a6] bg-[#fbd3b4] p-7 shadow-xl shadow-[#e8c7a6]/50">
        <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#a33d52]">
          <ArrowLeft size={14} /> Back to sign in
        </Link>

        {outcome ? (
          <div data-testid="forgot-outcome" className="mt-6 space-y-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl" style={{ backgroundColor: "#a33d52" }}>
              <MailCheck size={20} color="#ffe6cf" />
            </span>
            {outcome === "email" && (
              <>
                <h1 className="text-2xl font-black tracking-tight">Check your inbox</h1>
                <p className="text-sm text-[#7a5f52]">
                  If <b>{email}</b> has an account, a reset link is on its way. It expires in 30 minutes.
                  If it does not arrive, look in spam before trying again.
                </p>
              </>
            )}
            {outcome === "manual" && (
              <>
                <h1 className="text-2xl font-black tracking-tight">Almost there</h1>
                <p className="text-sm text-[#7a5f52]">
                  If <b>{email}</b> has an account, a reset link has been created — but email delivery is not
                  switched on for this server yet. Write to{" "}
                  <a className="font-semibold text-[#a33d52]" href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>{" "}
                  and we will send it to you by hand.
                </p>
              </>
            )}
            {outcome === "unavailable" && (
              <>
                <h1 className="text-2xl font-black tracking-tight">Not available yet</h1>
                <p className="text-sm text-[#7a5f52]">
                  Password reset is not set up on this server yet. Write to{" "}
                  <a className="font-semibold text-[#a33d52]" href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>{" "}
                  and we will reset it for you.
                </p>
              </>
            )}
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-5" data-testid="forgot-form">
            <div>
              <div className="label">Password help</div>
              <h1 className="mt-2 text-3xl font-black tracking-tight">Forgot your password?</h1>
              <p className="mt-2 text-sm text-[#7a5f52]">
                Enter your email and we will set up a link to choose a new one.
              </p>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#7a5f52]" htmlFor="forgot-email">Email</Label>
              <Input id="forgot-email" data-testid="forgot-email-input" type="email" required
                     value={email} onChange={(e) => setEmail(e.target.value)} className="h-11 bg-[#fbe4cd]" />
            </div>
            {err && <div data-testid="forgot-error" role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-900">{err}</div>}
            <button data-testid="forgot-submit-btn" disabled={busy} className="btn-primary w-full">
              {busy ? <Loader2 size={16} className="animate-spin" /> : <MailCheck size={16} />} Send reset link
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
