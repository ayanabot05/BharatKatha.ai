import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Loader2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { priceParams, countryHint } from "@/lib/geo";
import { useAuth } from "@/context/AuthContext";
import "./Pricing.css";

const RAZORPAY_SRC = "https://checkout.razorpay.com/v1/checkout.js";

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve(true);
    const el = document.createElement("script");
    el.src = src;
    el.async = true;
    el.onload = () => resolve(true);
    el.onerror = () => reject(new Error("Could not open the payment window."));
    document.body.appendChild(el);
  });
}

/**
 * Pricing table. Reads the catalog from the API so a price change is a backend
 * change, never a frontend deploy. Checkout is honest about its own state: when
 * the provider has no credentials the plan is still shown, and the reason is
 * displayed verbatim instead of a button that quietly does nothing.
 */
export default function Pricing({ onNavigate }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [annual, setAnnual] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await api.get("/billing/plans", { params: priceParams() });
        if (alive) setData(res.data);
      } catch (e) {
        if (alive) {
          setError(
            e?.response?.status === 404
              ? "Pricing is not available from this server yet. If you are running the studio locally, restart the backend so the billing routes load."
              : errMsg(e)
          );
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const plans = useMemo(() => (data?.plans || []), [data]);
  const live = Boolean(data?.checkout_live);
  const discount = data?.annual_discount_percent ?? 15;
  // Derived, not typed: the free-tier note can never drift from the catalog.
  const freePlan = useMemo(() => plans.find((p) => p.tier === 0), [plans]);

  async function openRazorpay(order) {
    await loadScript(RAZORPAY_SRC);
    await new Promise((resolve, reject) => {
      if (!window.Razorpay) return reject(new Error("Could not open the payment window."));
      const rzp = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "BharatKatha",
        description: order.description,
        order_id: order.order_id,
        prefill: { email: order.email || "" },
        theme: { color: "#a33d52" },
        handler: () => resolve(true),
        modal: { ondismiss: () => reject(new Error("Payment window closed before finishing.")) },
      });
      rzp.on("payment.failed", () => reject(new Error("The payment did not go through. Nothing was charged.")));
      rzp.open();
    });
  }

  async function choose(plan) {
    setError("");
    if (plan.tier === 0) {
      if (onNavigate) onNavigate();
      return;
    }
    if (!user) {
      window.location.assign("/register");
      return;
    }
    setBusy(plan.id);
    try {
      const res = await api.post("/billing/checkout", {
        plan: plan.id,
        interval: annual ? "year" : "month",
        // Send the currency that was displayed so the amount charged matches
        // the amount on the page. Real edge geography still outranks it.
        currency: data?.currency || undefined,
        country: countryHint() || undefined,
      });
      const order = res.data || {};
      if (!order.ready) {
        setError(order.reason || "Checkout is not available yet.");
        return;
      }
      if (order.url) {
        window.location.assign(order.url);
        return;
      }
      await openRazorpay(order);
      window.location.assign("/dashboard?upgraded=1");
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="pricing">
      <div className="pricing-head">
        <div>
          <span className="phase-eyebrow">Pricing</span>
          <h2>Start free. Grow when your stories do.</h2>
          <p>Every plan uses all 11 Indian languages, all 6 story styles and captions. You only pay for more videos and longer stories.</p>
        </div>
        <div className="pricing-toggle" role="group" aria-label="Billing period">
          <button type="button" aria-pressed={!annual} onClick={() => setAnnual(false)}>Monthly</button>
          <button type="button" aria-pressed={annual} onClick={() => setAnnual(true)}>
            Annual <span className="pricing-save">save {discount}%</span>
          </button>
        </div>
      </div>

      {loading && <div className="pricing-banner">Loading plans…</div>}
      {error && <div className="pricing-error" role="alert">{error}</div>}
      {!loading && !live && !error && (
        <div className="pricing-banner" role="status">
          Prices are final and shown in your local currency. Card and UPI checkout is being
          switched on right now — if a payment is declined with “being switched on”, please
          try again shortly.
        </div>
      )}

      <div className="pricing-grid">
        {plans.map((plan) => {
          const paid = plan.tier > 0;
          const amount = annual ? plan.year_display : plan.month_display;
          const unit = annual ? "/year" : "/month";
          return (
            <article key={plan.id} className={`pricing-card${plan.popular ? " pricing-card--popular" : ""}`}>
              {plan.popular && <span className="pricing-badge">Most chosen</span>}
              <h3>{plan.name}</h3>
              <p className="pricing-tagline">{plan.tagline}</p>
              <div className="pricing-amount">
                <strong>{amount}</strong>
                <span>{unit}</span>
              </div>
              {paid ? (
                <div className="pricing-was">
                  {annual
                    ? `${plan.year_per_month_display}/month billed yearly · save ${plan.savings_percent}%`
                    : `Save ${plan.savings_percent}% by paying yearly`}
                </div>
              ) : (
                <div className="pricing-was">Free forever, no card needed</div>
              )}
              <ul className="pricing-list">
                {plan.features.map((f) => (
                  <li key={f}><Check size={15} aria-hidden /> {f}</li>
                ))}
              </ul>
              {paid ? (
                <button
                  type="button"
                  className={`btn-primary pricing-cta${busy === plan.id ? " is-busy" : ""}`}
                  onClick={() => choose(plan)}
                  disabled={busy === plan.id}
                  data-testid={`pricing-buy-${plan.id}`}
                >
                  {busy === plan.id ? <><Loader2 size={16} className="animate-spin" /> Opening checkout…</> : `Choose ${plan.name}`}
                </button>
              ) : (
                <Link to="/register" className="btn-secondary pricing-cta" data-testid="pricing-free-cta">
                  {user ? "Create a video" : "Start free"}
                </Link>
              )}
            </article>
          );
        })}
      </div>

      {freePlan && (
        <p className="pricing-free-note">
          Free includes <strong>{freePlan.videos} videos every {freePlan.period_label}</strong>,
          up to {freePlan.max_seconds} seconds each. Unused videos reset each{" "}
          {freePlan.period_label}. Cancel anytime — you keep access until the end of the
          period you paid for.
        </p>
      )}
    </div>
  );
}
