import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Mic, Square, Upload, Sparkles, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { StepHeader } from "@/components/StepHeader";
import { Slider } from "@/components/ui/slider";
import { LANGUAGES } from "@/constants/studio";
import { useLocale } from "@/context/LocaleContext";

const DEFAULT_VOICES = [
  { id: "coral", name: "Female voice", desc: "Regional AI voice" },
  { id: "fable", name: "Male voice", desc: "Regional AI voice" },
];
const femaleLegacyVoices = new Set(["coral", "nova", "shimmer"]);
const selectedVoice = (id) => id === "M1" ? "M1" : femaleLegacyVoices.has(id) ? "coral" : "fable";
const TABS = [{ id: "ai", label: "Regional AI voice" }, { id: "record", label: "Record my voice" }, { id: "upload", label: "Upload voice-over" }];

function Recorder({ onDone, busy }) {
  const { t } = useLocale();
  const [rec, setRec] = useState(null);
  const [blob, setBlob] = useState(null);
  const chunks = useRef([]);
  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunks.current = [];
      mr.ondataavailable = (e) => chunks.current.push(e.data);
      mr.onstop = () => { setBlob(new Blob(chunks.current, { type: "audio/webm" })); stream.getTracks().forEach((t) => t.stop()); };
      mr.start(); setRec(mr); setBlob(null);
    } catch { toast.error(t("Microphone permission denied")); }
  };
  const stop = () => { rec?.stop(); setRec(null); };
  return (
    <div className="rounded-2xl border border-[#d6e2d7] p-6 text-center">
      <button data-testid="record-toggle-btn" onClick={rec ? stop : start}
        className={`h-20 w-20 rounded-full grid place-items-center mx-auto transition-colors ${rec ? "bg-rose-600 animate-pulse" : "bg-[#316b55] hover:bg-[#24543f]"} text-white`}>
        {rec ? <Square size={26} /> : <Mic size={28} />}
      </button>
      <p className="mt-3 text-sm text-[#61736d]">{rec ? t("Recording… read your script aloud") : t("Tap to record your narration")}</p>
      {blob && (
        <div className="mt-4 space-y-3">
          <audio controls src={URL.createObjectURL(blob)} className="mx-auto" data-testid="record-preview" />
          <button data-testid="use-recording-btn" disabled={busy} onClick={() => onDone(blob, "recording.webm", "record")} className="rounded-full bg-[#316b55] text-white font-semibold px-5 py-2.5 disabled:opacity-50"> {t("Use this recording")} </button>
        </div>
      )}
    </div>
  );
}

export default function StepAudio({ project, update }) {
  const { t } = useLocale();
  const [tab, setTab] = useState("ai");
  const [voices, setVoices] = useState(DEFAULT_VOICES);
  const [providers, setProviders] = useState([]);
  const [premiumRates, setPremiumRates] = useState({});
  const [premiumBudget, setPremiumBudget] = useState("");
  const preferredProvider = project.audio?.provider || ({ te: "piper", hi: "supertonic", en: "supertonic" }[project.language] || "edge");
  const [provider, setProvider] = useState(preferredProvider);
  const [voice, setVoice] = useState(selectedVoice(project.audio?.voice));
  const [speed, setSpeed] = useState(project.audio?.speed || 1);
  const [busy, setBusy] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const generationLock = useRef(false);
  useEffect(() => {
    if (busy !== "ai") return undefined;
    const started = Date.now();
    setElapsed(0);
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [busy]);
  const previewPlayer = useRef(null);
  const previewRequest = useRef(0);
  useEffect(() => {
    let active = true;
    api.get("/meta").then(({ data }) => {
      if (active && Array.isArray(data?.voices) && data.voices.length) setVoices(data.voices);
      if (active && Array.isArray(data?.voice_providers)) setProviders(data.voice_providers);
      if (active && data?.premium_voice_rates) setPremiumRates(data.premium_voice_rates);
      if (active && Array.isArray(data?.voice_providers)) {
        const offered = (id) => data.voice_providers.some((item) => item.id === id && item.languages.includes(project.language));
        const selected = [preferredProvider, data.default_voice_provider, "supertonic", "edge"]
          .find((id) => id && offered(id));
        if (selected) {
          setProvider(selected);
          if (selected === "piper") setVoice("coral");
          else if (selected === "supertonic") setVoice("M1");
          else if (!project.audio?.voice) setVoice("fable");
        }
      }
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  useEffect(() => { if (project.audio?.speed) setSpeed(project.audio.speed); }, [project.audio?.speed]);
  const stopPreview = () => {
    previewRequest.current += 1;
    if (previewPlayer.current) {
      previewPlayer.current.pause();
      URL.revokeObjectURL(previewPlayer.current.src);
      previewPlayer.current = null;
    }
  };
  useEffect(() => () => stopPreview(), []);
  const lang = LANGUAGES.find((l) => l.id === project.language);
  const providerSupported = providers.length > 0
    ? providers.some((item) => item.id === provider && item.languages.includes(project.language))
    : provider !== "piper" && project.language !== "or";
  const sample = project.scenes?.[0]?.narration?.slice(0, 160) || "Namaskaram";
  const premium = providers.find((item) => item.id === provider)?.type === "premium";
  const rate = premiumRates[provider];
  const quote = (text) => rate ? Math.ceil(text.length * Number(rate.all_in_inr_per_1000_chars) / 10) / 100 : 0;
  const previewEstimate = quote(sample);
  const narrationEstimate = Math.round((project.scenes || []).reduce((total, scene) => total + quote(scene.narration || ""), 0) * 100) / 100;
  const budget = Number(premiumBudget);
  const premiumReady = !premium || (rate && premiumBudget !== "" && Number.isFinite(budget)
    && budget >= Math.max(previewEstimate, narrationEstimate) && budget <= Number(rate.max_request_inr));

  const preview = async (v) => {
    stopPreview();
    const request = previewRequest.current;
    setBusy(`p-${v}`);
    try {
      const r = await api.post("/voice/preview", { voice: v, text: sample, speed, language: project.language, provider,
        ...(premium ? { max_cost_inr: budget } : {}) }, { responseType: "blob" });
      if (request !== previewRequest.current) return;
      const player = new Audio(URL.createObjectURL(r.data));
      previewPlayer.current = player;
      player.onended = () => { if (previewPlayer.current === player) stopPreview(); };
      await player.play();
    } catch (e) { if (request === previewRequest.current) { stopPreview(); setBusy(""); toast.error(t(errMsg(e))); } }
    finally { if (request === previewRequest.current) setBusy(""); }
  };
  const genAI = async () => {
    if (generationLock.current || busy) return;
    generationLock.current = true;
    stopPreview();
    setBusy("ai");
    try {
      const { data } = await api.post(`/projects/${project.id}/audio/ai`, { voice, speed, provider,
        ...(premium ? { max_cost_inr: budget } : {}) });
      update(data);
      if (data.audio?.caption_status === "failed") toast.warning(t("Voice saved. Caption timing needs attention."));
      else toast.success(t("Narration generated"));
    }
    catch (e) { toast.error(t(errMsg(e))); } finally { generationLock.current = false; setBusy(""); }
  };
  const uploadAudio = async (file, name, mode) => {
    setBusy("up");
    const fd = new FormData(); fd.append("file", file, name);
    try { const { data } = await api.post(`/projects/${project.id}/audio/upload?mode=${mode}`, fd); update(data); toast.success(t("Voice-over added")); }
    catch (e) { toast.error(t(errMsg(e))); } finally { setBusy(""); }
  };
  const continueWithoutCaptions = async () => {
    setBusy("captions");
    try {
      const { data } = await api.patch(`/projects/${project.id}`, { captions_on: false });
      update(data, 6);
    } catch (e) { toast.error(t(errMsg(e))); } finally { setBusy(""); }
  };

  return (
    <section className="rounded-3xl border border-[#d6e2d7] bg-white backdrop-blur-xl shadow-2xl shadow-[#c7d8ca]/30 p-5 sm:p-8">
      <StepHeader n={5} title="Audio Studio" pill={lang?.native}>
        <span> {t("Regional AI voice / Your own recording")} </span>
        <div className="text-xs text-[#587168] mt-1">{LANGUAGES.filter((l) => l.id !== "en").map((l) => l.native).join(" · ")}</div>
      </StepHeader>
      <div className="mt-6 inline-flex rounded-full bg-white p-1">
        {TABS.map((item) => (
          <button key={item.id} data-testid={`audio-tab-${item.id}`} onClick={() => { stopPreview(); if (busy.startsWith("p-")) setBusy(""); setTab(item.id); }}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${tab === item.id ? "bg-[#f5f9f4] shadow-sm text-[#263b36]" : "text-[#587168]"}`}>{t(item.label)}</button>
        ))}
      </div>

      {tab === "ai" && (
        <div className="mt-6">
          {providers.length > 0 && <div className="mb-5">
            <label htmlFor="voice-provider" className="block text-sm font-semibold text-[#35574c]">{t("Voice provider")}</label>
            <select id="voice-provider" data-testid="voice-provider-select" value={provider} onChange={(e) => { stopPreview(); setProvider(e.target.value); if (e.target.value === "piper") setVoice("coral"); else if (e.target.value === "supertonic") setVoice("M1"); else setVoice("fable"); }} className="mt-2 rounded-lg border border-[#c4d8c9] bg-white px-3 py-2">
              {providers.filter((item) => item.languages.includes(project.language)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            {premium && <div className="mt-2 text-sm text-amber-800">
              <p>{t("This voice uses a paid AI service. Preview and generation may incur charges.")}</p>
              {rate && <><p className="mt-1">{t("Estimated maximum for this narration")}: ₹{narrationEstimate.toFixed(2)} · {t("Preview")}: ₹{previewEstimate.toFixed(2)}</p>
                <label htmlFor="premium-voice-budget" className="mt-2 block">{t("Maximum budget for each request (INR)")}</label>
                <input id="premium-voice-budget" data-testid="premium-voice-budget" type="number" min="0.01" step="0.01"
                  value={premiumBudget} onChange={(e) => setPremiumBudget(e.target.value)}
                  className="mt-1 w-36 rounded-lg border border-amber-300 bg-white px-3 py-2" />
                <p className="mt-1">{t("Operator request cap")}: ₹{Number(rate.max_request_inr).toFixed(2)}</p></>}
            </div>}
          </div>}
          <p className="mb-3 text-sm text-[#35574c]">{!providerSupported ? t("This voice provider is unavailable for the project language. Choose another provider or upload narration.") : provider === "piper" ? t("Piper uses the voice configured for this language. Preview pronunciation before generating.") : provider === "supertonic" ? "Hindi AI-generated voice. The exported video labels its narration as AI-generated. Preview pronunciation before generating." : t("Choose a female or male voice, then preview the pronunciation.")}</p>
          <div className="grid sm:grid-cols-2 gap-3">
            {(provider === "supertonic" ? [{ id: "M1", name: "Hindi M1", desc: "Local Supertonic 3 voice" }] : provider === "piper" ? voices.slice(0, 1) : voices).map((v) => (
              <div key={v.id} data-testid={`voice-card-${v.id}`} onClick={() => setVoice(v.id)}
                className={`cursor-pointer rounded-2xl border p-4 flex items-center justify-between transition-colors ${voice === v.id ? "border-violet-500 bg-violet-500/10" : "border-[#d6e2d7] hover:border-cyan-400/40"}`}>
                <div><div className="font-semibold">{provider === "piper" ? t("Configured Piper voice") : t(v.name)}</div><div className="text-xs text-[#587168]">{provider === "piper" ? t("Open-source voice model hosted by the operator") : t(v.desc)}</div></div>
                <button data-testid={`voice-preview-${v.id}`} disabled={!!busy || !providerSupported || !premiumReady} onClick={(e) => { e.stopPropagation(); preview(v.id); }} className="h-9 w-9 rounded-full border border-[#c4d8c9] grid place-items-center hover:bg-white/10 disabled:opacity-40">
                  {busy === `p-${v.id}` ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                </button>
              </div>
            ))}
          </div>
          <div className="mt-5 max-w-sm">
            <div className="text-xs font-semibold uppercase tracking-wider text-[#587168]">{t("Speed")} · {speed.toFixed(2)}x</div>
            <Slider data-testid="voice-speed-slider" className="mt-3" min={0.75} max={1.25} step={0.05} value={[speed]} onValueChange={([s]) => setSpeed(s)} />
          </div>
          <p className="mt-3 text-xs text-[#61736d]"> {t("At 1.00x, the narrator speaks at a natural pace. The video follows the finished voice length. Choose another speed if you prefer, and preview pronunciation before generating.")} </p>
          <button data-testid="generate-voice-btn" onClick={genAI} disabled={!!busy || !providerSupported || !premiumReady} className="mt-5 inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-50">
            {busy === "ai" ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} {busy === "ai" ? `${t("Creating narration and caption timing…")} ${elapsed} ${t("seconds")}` : t("Generate narration for all scenes")}
          </button>
          {busy === "ai" && <p role="status" className="mt-3 text-sm text-[#35574c]"> {t(premium
            ? "Keep this page open. Premium voice requests are not retried automatically because an attempt may be billed."
            : "Keep this page open. Temporary connection failures are retried automatically.")} </p>}
        </div>
      )}
      {tab === "record" && <div className="mt-6 max-w-md"><Recorder busy={!!busy} onDone={uploadAudio} /></div>}
      {tab === "upload" && (
        <label className="mt-6 block max-w-md rounded-2xl border-2 border-dashed border-[#c4d8c9] hover:border-violet-500 p-10 text-center cursor-pointer transition-colors">
          {busy === "up" ? <Loader2 className="mx-auto animate-spin" /> : <Upload className="mx-auto text-[#61736d]" />}
          <div className="mt-2 font-semibold"> {t("Upload MP3 / WAV / M4A")} </div>
          <div className="text-xs text-[#587168]"> {t("Up to 25 MB · automatic captions require successful transcription")} </div>
          <input data-testid="audio-upload-input" type="file" accept="audio/*" className="hidden" onChange={(e) => e.target.files[0] && uploadAudio(e.target.files[0], e.target.files[0].name, "upload")} />
        </label>
      )}

      {project.audio?.caption_status === "failed" && project.captions_on !== false && <div role="alert" className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">{t("Voice saved. Caption timing needs attention.")}</p>
        <p className="mt-2">{t("Your narration is ready to play. Subtitles could not be aligned reliably. Retry using the saved audio, or choose to render without captions.")}</p>
        <div className="mt-3 flex flex-wrap gap-3">
          <button disabled={!!busy} onClick={genAI} className="rounded-lg border border-amber-700 px-3 py-2 disabled:opacity-50">{t("Retry caption timing")}</button>
          <button disabled={!!busy} onClick={continueWithoutCaptions} className="rounded-lg border border-amber-700 px-3 py-2 disabled:opacity-50">{t("Continue without captions")}</button>
        </div>
      </div>}
      {project.audio?.caption_status === "estimated" && project.captions_on !== false && <div role="status" className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        {t("Caption timing is estimated from the script and audio length. Review the rendered subtitles before sharing.")}
      </div>}
      {project.audio && (
        <div className="mt-8 rounded-2xl bg-[#f5f9f4] border border-[#d6e2d7] p-5 flex flex-wrap items-center gap-4 justify-between" data-testid="current-audio">
          <div>
            <div className="text-xs uppercase tracking-wider text-[#587168]">{t("Current voice-over")} · {t(TABS.find((item) => item.id === project.audio.mode)?.label || "Regional AI voice")}</div>
            <audio controls src={mediaUrl(project.audio.path)} className="mt-2" data-testid="current-audio-player" />
            <div className="text-xs text-[#587168] mt-1">{project.audio.duration?.toFixed(1)} {t("seconds")}</div>
            {project.audio.duration_matched && <p className="mt-2 text-xs text-teal-800">{t("audio_paced_note", { speed: project.audio.speed?.toFixed(2) })}</p>}
            {project.duration && Math.abs(project.audio.duration - project.duration) > 1 && <p className="mt-2 text-sm text-amber-800">
              {t("audio_duration_note", { actual: project.audio.duration?.toFixed(1), target: project.duration })}
            </p>}
          </div>
          <button data-testid="audio-continue-btn" disabled={!!busy || (project.audio.caption_status === "failed" && project.captions_on !== false)} onClick={() => update(project, 6)} className="inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-50"> {t("Continue to render")} <ArrowRight size={16} />
          </button>
        </div>
      )}
    </section>
  );
}
