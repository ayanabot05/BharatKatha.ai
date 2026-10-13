import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Mic, Square, Upload, Sparkles, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { StepHeader } from "@/components/StepHeader";
import { Slider } from "@/components/ui/slider";
import { LANGUAGES } from "@/constants/studio";

const VOICES = [
  { id: "coral", name: "Female voice", desc: "Edge neural voice" },
  { id: "fable", name: "Male voice", desc: "Edge neural voice" },
];
const femaleLegacyVoices = new Set(["coral", "nova", "shimmer"]);
const selectedVoice = (id) => femaleLegacyVoices.has(id) ? "coral" : "fable";
const TABS = [{ id: "ai", label: "Regional AI voice" }, { id: "record", label: "Record my voice" }, { id: "upload", label: "Upload voice-over" }];

function Recorder({ onDone, busy }) {
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
    } catch { toast.error("Microphone permission denied"); }
  };
  const stop = () => { rec?.stop(); setRec(null); };
  return (
    <div className="rounded-2xl border border-[#65546B] p-6 text-center">
      <button data-testid="record-toggle-btn" onClick={rec ? stop : start}
        className={`h-20 w-20 rounded-full grid place-items-center mx-auto transition-colors ${rec ? "bg-rose-600 animate-pulse" : "bg-slate-900 hover:bg-violet-700"} text-white`}>
        {rec ? <Square size={26} /> : <Mic size={28} />}
      </button>
      <p className="mt-3 text-sm text-slate-400">{rec ? "Recording… read your script aloud" : "Tap to record your narration"}</p>
      {blob && (
        <div className="mt-4 space-y-3">
          <audio controls src={URL.createObjectURL(blob)} className="mx-auto" data-testid="record-preview" />
          <button data-testid="use-recording-btn" disabled={busy} onClick={() => onDone(blob, "recording.webm", "record")} className="rounded-full bg-violet-600 text-white font-semibold px-5 py-2.5 disabled:opacity-50">Use this recording</button>
        </div>
      )}
    </div>
  );
}

export default function StepAudio({ project, update }) {
  const [tab, setTab] = useState("ai");
  const [voice, setVoice] = useState(selectedVoice(project.audio?.voice));
  const [speed, setSpeed] = useState(project.audio?.speed || 1);
  const [busy, setBusy] = useState("");
  const previewPlayer = useRef(null);
  const previewRequest = useRef(0);
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
  const sample = project.scenes?.[0]?.narration?.slice(0, 160) || "Namaskaram";

  const preview = async (v) => {
    stopPreview();
    const request = previewRequest.current;
    setBusy(`p-${v}`);
    try {
      const r = await api.post("/voice/preview", { voice: v, text: sample, speed, language: project.language }, { responseType: "blob" });
      if (request !== previewRequest.current) return;
      const player = new Audio(URL.createObjectURL(r.data));
      previewPlayer.current = player;
      player.onended = () => { if (previewPlayer.current === player) stopPreview(); };
      await player.play();
    } catch (e) { if (request === previewRequest.current) { stopPreview(); setBusy(""); toast.error(errMsg(e)); } }
    finally { if (request === previewRequest.current) setBusy(""); }
  };
  const genAI = async () => {
    stopPreview();
    setBusy("ai");
    try { const { data } = await api.post(`/projects/${project.id}/audio/ai`, { voice, speed }); update(data); toast.success("Narration generated"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(""); }
  };
  const uploadAudio = async (file, name, mode) => {
    setBusy("up");
    const fd = new FormData(); fd.append("file", file, name);
    try { const { data } = await api.post(`/projects/${project.id}/audio/upload?mode=${mode}`, fd); update(data); toast.success("Voice-over added"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(""); }
  };

  return (
    <section className="rounded-3xl border border-white/10 bg-[#302837]/80 backdrop-blur-xl shadow-2xl shadow-black/40 p-5 sm:p-8">
      <StepHeader n={5} title="Audio Studio" pill={lang?.label}>
        <span>Regional AI voice / Your own recording</span>
        <div className="text-xs text-slate-300 mt-1">{LANGUAGES.filter((l) => l.id !== "en").map((l) => l.native).join(" · ")}</div>
      </StepHeader>
      <div className="mt-6 inline-flex rounded-full bg-[#181A26] p-1">
        {TABS.map((t) => (
          <button key={t.id} data-testid={`audio-tab-${t.id}`} onClick={() => { stopPreview(); if (busy.startsWith("p-")) setBusy(""); setTab(t.id); }}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${tab === t.id ? "bg-[#3A3040] shadow-sm text-white" : "text-slate-300"}`}>{t.label}</button>
        ))}
      </div>

      {tab === "ai" && (
        <div className="mt-6">
          <p className="mb-3 text-sm text-slate-200">{project.language === "or" ? "Odia AI voice is currently unavailable. Record or upload your narration." : "Choose a female or male voice, then preview the pronunciation."}</p>
          <div className="grid sm:grid-cols-2 gap-3">
            {VOICES.map((v) => (
              <div key={v.id} data-testid={`voice-card-${v.id}`} onClick={() => setVoice(v.id)}
                className={`cursor-pointer rounded-2xl border p-4 flex items-center justify-between transition-colors ${voice === v.id ? "border-violet-500 bg-violet-500/10" : "border-[#65546B] hover:border-cyan-400/40"}`}>
                <div><div className="font-semibold">{v.name}</div><div className="text-xs text-slate-300">{v.desc}</div></div>
                <button data-testid={`voice-preview-${v.id}`} disabled={!!busy || project.language === "or"} onClick={(e) => { e.stopPropagation(); preview(v.id); }} className="h-9 w-9 rounded-full border border-[#383D54] grid place-items-center hover:bg-white/10 disabled:opacity-40">
                  {busy === `p-${v.id}` ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                </button>
              </div>
            ))}
          </div>
          <div className="mt-5 max-w-sm">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-300">Speed · {speed.toFixed(2)}x</div>
            <Slider data-testid="voice-speed-slider" className="mt-3" min={0.75} max={1.25} step={0.05} value={[speed]} onValueChange={([s]) => setSpeed(s)} />
          </div>
          <p className="mt-3 text-xs text-slate-400">Speed changes pacing, not the voice. Listen to a preview for pronunciation; you can also record or upload your own narration.</p>
          <button data-testid="generate-voice-btn" onClick={genAI} disabled={!!busy || project.language === "or"} className="mt-5 inline-flex items-center gap-2 btn-primary px-6 py-3 disabled:opacity-50">
            {busy === "ai" ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} Generate narration for all scenes
          </button>
        </div>
      )}
      {tab === "record" && <div className="mt-6 max-w-md"><Recorder busy={!!busy} onDone={uploadAudio} /></div>}
      {tab === "upload" && (
        <label className="mt-6 block max-w-md rounded-2xl border-2 border-dashed border-[#383D54] hover:border-violet-500 p-10 text-center cursor-pointer transition-colors">
          {busy === "up" ? <Loader2 className="mx-auto animate-spin" /> : <Upload className="mx-auto text-slate-400" />}
          <div className="mt-2 font-semibold">Upload MP3 / WAV / M4A</div>
          <div className="text-xs text-slate-300">Up to 25 MB · automatic captions require successful transcription</div>
          <input data-testid="audio-upload-input" type="file" accept="audio/*" className="hidden" onChange={(e) => e.target.files[0] && uploadAudio(e.target.files[0], e.target.files[0].name, "upload")} />
        </label>
      )}

      {project.audio && (
        <div className="mt-8 rounded-2xl bg-[#0C0E16] border border-[#65546B] p-5 flex flex-wrap items-center gap-4 justify-between" data-testid="current-audio">
          <div>
            <div className="text-xs uppercase tracking-wider text-slate-300">Current voice-over · {project.audio.mode}</div>
            <audio controls src={mediaUrl(project.audio.path)} className="mt-2" data-testid="current-audio-player" />
            <div className="text-xs text-slate-300 mt-1">{project.audio.duration?.toFixed(1)}s</div>
            {project.duration && Math.abs(project.audio.duration - project.duration) > 1 && <p className="mt-2 text-sm text-amber-200">
              Narration is {project.audio.duration?.toFixed(1)} seconds; your target is {project.duration} seconds. Adjust the script or speaking speed if you need that duration.
            </p>}
          </div>
          <button data-testid="audio-continue-btn" onClick={() => update(project, 6)} className="inline-flex items-center gap-2 btn-primary px-6 py-3">
            Continue to render <ArrowRight size={16} />
          </button>
        </div>
      )}
    </section>
  );
}
