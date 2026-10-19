import { useState } from "react";
import { BellRing, Check, Loader2, Sparkles } from "lucide-react";
import { api, errMsg } from "@/lib/api";

/**
 * "What's next" — an honest account of motion.
 *
 * The studio already animates stills with real camera motion, including true
 * depth parallax. Full generative video motion (characters that move, action
 * between scenes) needs GPU video models we do not run yet, so it is presented
 * as *coming soon* and never as something a visitor can buy today. The
 * notify-me list is what tells people the moment it is real.
 */
export default function MotionSoon() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState(null);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const { data } = await api.post("/notify", { email, topic: "ai_motion", source: "landing-motion" });
      if (data?.saved) setOutcome(data.already ? "already" : "done");
      else setOutcome("unavailable");
    } catch (e2) {
      setErr(errMsg(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section id="motion" className="phase-wrap phase-motion" aria-labelledby="motion-title">
      <div className="phase-motion-head">
        <span className="phase-eyebrow">What&rsquo;s next</span>
        <h2 id="motion-title">The pictures move. Soon, so will the stories.</h2>
        <p>
          Every video today is animated from your illustrations by a moving camera. That is real
          motion, and it is included. Full AI video motion — characters that act, movement between
          scenes — is not live yet. We will not pretend otherwise, and we will not charge for it
          until it is genuine.
        </p>
      </div>

      <div className="phase-motion-tiers">
        <article className="phase-motion-card phase-motion-card--now">
          <span className="phase-motion-tag"><Check size={13} /> Available now</span>
          <h3>Camera motion</h3>
          <ul>
            <li><b>Standard camera</b> — a smooth push or drift across your picture, on by default.</li>
            <li><b>Depth 2.5D</b> — your illustration is split into real depth layers and the camera moves between them, so the scene gains true parallax rather than a flat pan.</li>
            <li>Included in every render, on every plan, in all 11 languages.</li>
          </ul>
        </article>

        <article className="phase-motion-card phase-motion-card--soon">
          <span className="phase-motion-tag"><Sparkles size={13} /> In development</span>
          <h3>Generative video motion</h3>
          <ul>
            <li>Characters that move and act inside a shot.</li>
            <li>Action carried between scenes, not just stills.</li>
            <li>Needs GPU video models we do not run yet — so it stays switched off, honestly labelled, and unbilled.</li>
          </ul>
        </article>
      </div>

      <div className="phase-motion-notify">
        {outcome ? (
          <div className="phase-motion-outcome" data-testid="notify-outcome" role="status">
            <BellRing size={16} />
            {outcome === "done" && <span>You&rsquo;re on the list. We&rsquo;ll email you the day AI video motion goes live.</span>}
            {outcome === "already" && <span>You&rsquo;re already on the list — we&rsquo;ll be in touch.</span>}
            {outcome === "unavailable" && <span>We couldn&rsquo;t save that just now. Please try again in a moment.</span>}
          </div>
        ) : (
          <form className="phase-motion-form" onSubmit={submit} data-testid="notify-form">
            <label htmlFor="notify-email" className="phase-motion-form-label">
              Tell me when AI video motion is ready
            </label>
            <div className="phase-motion-form-row">
              <input
                id="notify-email"
                data-testid="notify-email-input"
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <button type="submit" className="btn-primary" disabled={busy} data-testid="notify-submit-btn">
                {busy ? <Loader2 size={16} className="animate-spin" /> : <BellRing size={16} />} Notify me
              </button>
            </div>
            {err && <div className="phase-motion-err" data-testid="notify-error" role="alert">{err}</div>}
            <p className="phase-motion-fineprint">One email when it ships. No newsletter, no sharing your address.</p>
          </form>
        )}
      </div>
    </section>
  );
}
