import { Youtube, Cpu, Mic2, ImageIcon, PenLine, Captions } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { PLANS } from "@/constants/studio";

const ENGINES = [
  { icon: PenLine, k: "Script & review agents", now: "Gemini 3 Flash", next: "Fine-tuned Indic story model on approved scripts" },
  { icon: ImageIcon, k: "Scene images & edits", now: "Nano Banana (Gemini image)", next: "Own LoRA styles: Indian cartoon, storybook, village" },
  { icon: Mic2, k: "Narration voice", now: "OpenAI TTS-HD (+ your own voice)", next: "Bharat Voice — fine-tuned Indic TTS on consented native speakers" },
  { icon: Captions, k: "Captions", now: "Whisper + script timing", next: "Indic ASR with word-level Telugu line breaking" },
];

export default function Settings() {
  const { user } = useAuth();
  const plan = PLANS.find((p) => p.id === user?.plan);
  return (
    <div className="space-y-8">
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight rise">Settings</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-[#d6e2d7] p-6" data-testid="settings-profile">
          <div className="text-xs uppercase tracking-wider text-[#587168]">Account</div>
          <div className="mt-2 font-semibold">{user?.name}</div>
          <div className="text-sm text-[#587168]">{user?.email}</div>
          <div className="mt-4 text-sm">Plan: <b className="capitalize">{plan?.name}</b> · {plan?.price}/mo · {plan?.note}</div>
          <p className="text-xs text-[#61736d] mt-1">Upgrades & payments are coming soon.</p>
        </div>
        <div className="rounded-2xl border border-[#d6e2d7] p-6" data-testid="settings-youtube">
          <div className="flex items-center gap-2 font-semibold"><Youtube className="text-rose-400" />YouTube channel</div>
          <span className="mt-2 inline-flex rounded-full bg-white px-2.5 py-0.5 text-xs font-semibold text-[#61736d]" data-testid="youtube-status">Not connected</span>
          <p className="mt-3 text-sm text-[#61736d]">Private uploads + YouTube Analytics need a Google Cloud OAuth client (YouTube Data API v3 + Analytics API). Unverified apps can only upload as <b>private</b> until Google's audit — which is exactly our review-first flow.</p>
          <button disabled data-testid="connect-youtube-btn" className="mt-4 rounded-full bg-[#e7efe7] text-[#587168] font-semibold px-5 py-2 text-sm cursor-not-allowed">Connect YouTube (coming next)</button>
        </div>
      </div>
      <div className="rounded-3xl border border-[#d6e2d7] bg-white backdrop-blur-xl shadow-2xl shadow-[#c7d8ca]/30 p-6 sm:p-8" data-testid="settings-engines">
        <div className="flex items-center gap-2 font-semibold"><Cpu size={18} className="text-violet-400" />AI engines — today vs. our own models</div>
        <p className="text-sm text-[#61736d] mt-1">Every engine sits behind one provider interface, so we can swap in our in-house Indian models without changing your workflow.</p>
        <div className="mt-6 divide-y divide-[#d6e2d7]">
          {ENGINES.map(({ icon: Icon, k, now, next }) => (
            <div key={k} className="py-4 grid md:grid-cols-[220px_1fr_1fr] gap-2 md:gap-6 text-sm">
              <div className="flex items-center gap-2 font-semibold"><Icon size={16} />{k}</div>
              <div><span className="text-[10px] uppercase tracking-wider text-emerald-600 font-semibold">Live now</span><div>{now}</div></div>
              <div><span className="text-[10px] uppercase tracking-wider text-amber-600 font-semibold">Our own (roadmap)</span><div className="text-[#61736d]">{next}</div></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
