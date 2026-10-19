import { Link } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
import { Logo } from "@/components/AppShell";
import Pricing from "@/components/Pricing";
import { Aurora, Reveal3D } from "@/components/fx3d";
import { useSeo } from "@/lib/seo";
import "./PhaseZero.css";

export default function PricingPage() {
  useSeo({
    title: "Pricing — BharatKatha storytelling studio",
    description: "BharatKatha pricing: start free with 2 videos a month, then ₹549 or $8.99 a month for 8 videos up to 60 seconds. Studio adds 16 videos up to 75 seconds. Annual plans save 15%.",
    path: "/pricing",
  });
  return (
    <div className="phase-landing fx3d-root">
      <Aurora />
      <header className="phase-nav phase-wrap">
        <Link to="/" aria-label="Home"><Logo light /></Link>
        <nav aria-label="Main navigation">
          <Link to="/">Home</Link>
          <Link to="/dashboard">My videos</Link>
          <Link to="/login">Sign in</Link>
        </nav>
        <Link to="/register" className="btn-primary fx3d-shine">Create a video</Link>
      </header>
      <main className="phase-wrap" style={{ paddingBlock: "28px 64px" }}>
        <section aria-label="Plans"><Reveal3D><Pricing /></Reveal3D></section>
        <section className="phase-start" style={{ marginTop: 40 }} aria-label="Questions">
          <Reveal3D>
            <div>
              <h2>Questions before you start?</h2>
              <p>Videos are storytelling: your idea, a written script you approve, illustrations and a voice-over in your language. Nothing is published anywhere without you.</p>
            </div>
          </Reveal3D>
          <Reveal3D delay={0.08}>
            <Link to="/register" className="btn-primary fx3d-shine">Start free <ArrowRight size={18} /></Link>
          </Reveal3D>
        </section>
        <p className="pricing-free-note" style={{ marginTop: 20 }}>
          <Check size={13} aria-hidden style={{ verticalAlign: "-2px" }} /> You can change or cancel a plan anytime. Nothing renews without you choosing it.
        </p>
      </main>
      <footer className="phase-wrap phase-footer">
        <Logo light />
        <span>Made for Indian storytellers</span>
        <Link to="/">Home</Link>
      </footer>
    </div>
  );
}
