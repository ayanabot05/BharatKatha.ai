import FeedbackForm from "@/components/FeedbackForm";
import { useEffect, useState } from "react";
import { Loader2, Film, Download, Copy, Youtube, Captions, FileText, Image as ImageIcon, Share2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { api, errMsg, mediaUrl } from "@/lib/api";
import { StepHeader } from "@/components/StepHeader";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { useLocale } from "@/context/LocaleContext";

const copy = (t) => { navigator.clipboard.writeText(t); toast.success("Copied"); };

function Meta({ label, value, testid }) {
  return (
    <div className="rounded-xl border border-[#d6e2d7] p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#587168]">{label}</span>
        <button data-testid={`copy-${testid}`} onClick={() => copy(value)} className="text-[#61736d] hover:text-[#263b36]"><Copy size={14} /></button>
      </div>
      <p className="indic mt-1 text-sm text-[#263b36] break-words" data-testid={`meta-${testid}`}>{value}</p>
    </div>
  );
}

export default function StepRender({ project, update }) {
  const { t } = useLocale();
  const [busy, setBusy] = useState(false);
  const [capsBusy, setCapsBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [previewAttempt, setPreviewAttempt] = useState(0);
  // Camera motion for this render. Ken Burns is the default and the only mode
  // offered when the depth engine is not installed on the server.
  const [motion, setMotion] = useState(project.motion === "depth_parallax" ? "depth_parallax" : "ken_burns");
  const [engines, setEngines] = useState(null);
  const [thumbnailScene, setThumbnailScene] = useState(project.scenes?.find((scene) => scene.image_path && !scene.placeholder && scene.approved)?.id || "");
  const [thumbnailTitle, setThumbnailTitle] = useState(project.script?.thumbnail_title || project.script?.title || "");
  const r = project.render || {};
  const s = project.script || {};
  useEffect(() => { setPreviewError(false); }, [r.video_path]);
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { data } = await api.get("/projects/motion/engines");
        if (alive) setEngines(data?.engines || []);
      } catch {
        // Capability probe only. If it fails we simply do not offer 2.5D.
        if (alive) setEngines(null);
      }
    })();
    return () => { alive = false; };
  }, []);
  const rendering = r.status === "rendering";
  const depthEngine = (engines || []).find((e) => e.id === "depth_parallax");
  const depthAvailable = engines ? Boolean(depthEngine && depthEngine.available !== false) : null;
  const videoReady = r.status === "done" && Boolean(r.video_path);
  const scriptApproved = project.approved && project.validation?.all_passed;
  const scenesApproved = (project.scenes || []).length > 0 && project.scenes.every((scene) => scene.status === "ready" && scene.image_path && !scene.placeholder && scene.approved);
  const unfinishedScenes = (project.scenes || []).flatMap((scene, index) => {
    if (scene.status === "ready" && scene.image_path && !scene.placeholder && scene.approved) return [];
    const reason = scene.status === "generating" ? "picture is generating"
      : scene.status === "queued" ? "picture is queued"
      : scene.status === "failed" ? "picture generation failed"
      : scene.placeholder ? "picture is a placeholder"
      : !scene.image_path ? "needs a picture"
      : !scene.approved ? "needs your picture approval"
      : `picture status is ${scene.status || "unknown"}`;
    return `Scene ${index + 1}: ${reason}`;
  });

  const start = async () => {
    setBusy(true);
    try { const { data } = await api.post(`/projects/${project.id}/render`, { motion }); update(data); }
    catch (e) {
      // A lost response can happen after the cloud job was submitted. Read the
      // persisted state before suggesting another click.
      try {
        const { data } = await api.get(`/projects/${project.id}`);
        update(data);
        if (["rendering", "done"].includes(data.render?.status)) {
          toast.info("Your video request reached the studio. Progress will update here.");
        } else toast.error(errMsg(e));
      } catch (_) {
        toast.error("Could not confirm the render status. Reopen this project before trying again.");
      }
    } finally { setBusy(false); }
  };
  const toggleCaps = async (v) => {
    setCapsBusy(true);
    try { const { data } = await api.patch(`/projects/${project.id}`, { captions_on: v }); update(data); }
    catch (e) { toast.error(errMsg(e)); }
    finally { setCapsBusy(false); }
  };
  const downloadVideo = async () => {
    setDownloading(true);
    try {
      const response = await fetch(`${mediaUrl(r.video_path)}?download=1`, { credentials: "include" });
      if (!response.ok) throw new Error(response.status === 401 ? "Your session expired. Sign in and try downloading again." : "The video could not be downloaded. Please try again.");
      if (!/^(video\/mp4|application\/octet-stream)/i.test(response.headers.get("content-type") || "")) {
        throw new Error("The studio returned an unexpected file. Please try again.");
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `${(s.title_en || s.title || "bharatkatha-video").replace(/[\\/:*?"<>|]/g, "-")}.mp4`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { toast.error(e.message || "The video could not be downloaded."); }
    finally { setDownloading(false); }
  };
  const createThumbnail = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/projects/${project.id}/thumbnail`, { scene_id: thumbnailScene, title: thumbnailTitle });
      update(data); toast.success("Thumbnail ready");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const shareVideo = async () => {
    try {
      const response = await fetch(mediaUrl(r.video_path), { credentials: "include" });
      if (!response.ok) throw new Error("Could not load video");
      const file = new File([await response.blob()], `${s.title_en || "video"}.mp4`, { type: "video/mp4" });
      if (!navigator.canShare?.({ files: [file] })) return toast.error("Sharing files is unavailable here. Download the MP4 instead.");
      await navigator.share({ title: s.title || "BharatKatha video", files: [file] });
    } catch (e) { if (e.name !== "AbortError") toast.error(e.message); }
  };
  const [srtUrl, setSrtUrl] = useState(null);
  const subtitles = r.srt || project.srt;
  useEffect(() => {
    if (!subtitles) { setSrtUrl(null); return; }
    const url = URL.createObjectURL(new Blob([subtitles], { type: "text/plain;charset=utf-8" }));
    setSrtUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [subtitles]);

  return (
    <section className="rounded-3xl border border-[#d6e2d7] bg-white backdrop-blur-xl shadow-2xl shadow-[#c7d8ca]/30 p-5 sm:p-8">
      <StepHeader n={6} title="Render & publish" pill={r.status === "done" && scenesApproved ? "Ready" : "MP4 · 9:16"}>
        <span className="text-sm">Captions · Scene timing · Ken Burns motion · Voice sync → MP4</span>
      </StepHeader>
      <div className="mt-6 grid lg:grid-cols-[300px_1fr] gap-8">
        <div>
          <div className="aspect-[9/16] rounded-2xl overflow-hidden bg-[#e7efe7] relative grain" data-testid="video-preview">
            {videoReady && scenesApproved && !previewError ? <video key={previewAttempt} controls preload="metadata" src={mediaUrl(r.video_path)} poster={mediaUrl(project.scenes?.[0]?.image_path)} onError={() => setPreviewError(true)} className="w-full h-full object-cover" data-testid="final-video" />
              : <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-5 text-center text-[#587168]"><Film size={36} /><span className="text-sm">{previewError ? "The video preview could not load. Your saved video may still be available to download." : rendering ? "Rendering your video…" : r.status === "failed" ? "Render failed. See the message beside the preview." : r.status === "done" ? "Video details are temporarily unavailable. Please reopen this project." : scenesApproved ? "No video rendered yet. Select Render my video." : "No video yet. Finish scene pictures and approvals first."}</span>{previewError && <button type="button" onClick={() => { setPreviewError(false); setPreviewAttempt((n) => n + 1); }} className="text-sm font-semibold underline">Retry preview</button>}</div>}
          </div>
          {videoReady && scenesApproved && (
            <div className="mt-3 flex gap-2">
              <button type="button" data-testid="download-mp4-btn" onClick={downloadVideo} disabled={downloading} className="flex-1 btn-primary text-sm font-semibold py-2.5 flex items-center justify-center gap-2 disabled:opacity-50">{downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}{downloading ? "Downloading…" : "Download MP4"}</button>
              {(r.caption_path || srtUrl) && <a data-testid="download-srt-btn" href={r.caption_path ? `${mediaUrl(r.caption_path)}?download=1` : srtUrl} download="captions.srt" className="flex-1 rounded-full border border-[#c4d8c9] text-sm font-semibold py-2.5 flex items-center justify-center gap-2"><FileText size={14} />SRT</a>}
              <button onClick={shareVideo} className="rounded-full border border-[#c4d8c9] px-3" title="Share video"><Share2 size={16} /></button>
            </div>
          )}
        </div>
        <div className="space-y-5">
          <div className="rounded-2xl border border-[#d6e2d7] p-5 space-y-3">
            <div className="flex items-center gap-2 font-semibold"><ImageIcon size={16} />Thumbnail</div>
            {s.thumbnail_path && <div className="flex items-start gap-3"><img src={mediaUrl(s.thumbnail_path)} alt="Video thumbnail" className="h-32 aspect-[9/16] object-cover rounded-lg" /><a href={mediaUrl(s.thumbnail_path)} download="thumbnail.png" className="text-sm text-violet-800 underline">Download PNG</a></div>}
            <select value={thumbnailScene} onChange={(e) => setThumbnailScene(e.target.value)} className="w-full rounded-lg bg-white p-2 text-[#263b36]">
              <option value="">Choose a real scene picture</option>
              {(project.scenes || []).map((scene, index) => <option key={scene.id} value={scene.id} disabled={!scene.image_path || scene.placeholder || !scene.approved}>Scene {index + 1}{scene.placeholder ? " (preview only)" : !scene.approved ? " (needs approval)" : ""}</option>)}
            </select>
            <input value={thumbnailTitle} onChange={(e) => setThumbnailTitle(e.target.value)} maxLength={80} aria-label="Thumbnail title" className="indic w-full rounded-lg bg-white p-2 text-[#263b36]" />
            <button onClick={createThumbnail} disabled={busy || !thumbnailScene || !thumbnailTitle.trim()} className="btn-primary px-4 py-2 text-sm disabled:opacity-40">{t("create_thumbnail")}</button>
          </div>
          <div className="rounded-2xl border border-[#d6e2d7] p-5">
            {!scriptApproved && <div role="alert" className="mb-4 rounded-lg bg-amber-500/15 p-3 text-sm text-amber-900">
              Review and approve the current script before rendering.
              <button onClick={() => update(project, 2)} className="ml-2 font-semibold underline">Go to script review</button>
            </div>}
            {!scenesApproved && <div role="alert" className="mb-4 rounded-lg bg-amber-500/15 p-3 text-sm text-amber-900">
              <p className="font-semibold">Video render is blocked by these scenes:</p>
              <ul className="mt-2 list-disc pl-5">{unfinishedScenes.map((message) => <li key={message}>{message}</li>)}</ul>
              <button onClick={() => update(project, 4)} className="mt-3 rounded-lg bg-amber-100 px-3 py-2 font-semibold text-slate-950">Go to Scene editor</button>
            </div>}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold"><Captions size={16} />{t("burn_in_captions")}</div>
              <Switch data-testid="captions-switch" checked={project.captions_on !== false} onCheckedChange={toggleCaps} disabled={rendering || capsBusy} />
            </div>
            <div className="mt-5" data-testid="motion-picker">
              <div className="flex items-center gap-2 font-semibold"><Sparkles size={16} />Camera motion</div>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <button type="button" data-testid="motion-ken_burns" aria-pressed={motion === "ken_burns"}
                  onClick={() => setMotion("ken_burns")} disabled={rendering}
                  className={`rounded-xl border p-3 text-left text-sm transition-colors ${motion === "ken_burns" ? "border-[#a33d52] bg-[#f8d9c6] ring-1 ring-[#a33d52]" : "border-[#e8c7a6] bg-[#fbe6d6] hover:bg-[#f7ddc9]"} disabled:opacity-50`}>
                  <span className="block font-semibold">Standard camera</span>
                  <span className="mt-1 block text-xs text-[#587168]">Smooth zoom and pan. Fast and reliable.</span>
                </button>
                <button type="button" data-testid="motion-depth_parallax" aria-pressed={motion === "depth_parallax"}
                  onClick={() => setMotion("depth_parallax")} disabled={rendering || depthAvailable === false}
                  className={`rounded-xl border p-3 text-left text-sm transition-colors ${motion === "depth_parallax" ? "border-[#a33d52] bg-[#f8d9c6] ring-1 ring-[#a33d52]" : "border-[#e8c7a6] bg-[#fbe6d6] hover:bg-[#f7ddc9]"} disabled:opacity-50`}>
                  <span className="block font-semibold">Depth (2.5D)</span>
                  <span className="mt-1 block text-xs text-[#587168]">{depthAvailable === false ? "Not installed on this server." : "Real per-pixel depth. Slower on CPU."}</span>
                </button>
              </div>
              <p className="mt-2 text-xs text-[#587168]">Depth (2.5D) estimates a depth map for each picture and moves near and far areas at different speeds, so the scene has real depth. Pictures with no depth to separate fall back to the standard camera automatically.</p>
            </div>
            {project.audio?.mode !== "ai" && <p className="mt-3 text-sm text-[#587168]">Scene cuts for uploaded or recorded narration are estimated. Watch the final video to check that each picture matches your words.</p>}
            {r.caption_timing === "estimated" && <p className="mt-3 text-sm text-amber-800">Caption timing is estimated from the script and narration length. Review the rendered subtitles before sharing.</p>}
            {!project.audio && <p className="mt-3 text-sm text-amber-800">Add narration in Audio Studio before rendering.</p>}
            <button data-testid="render-btn" onClick={start} disabled={busy || rendering || !scenesApproved || !scriptApproved || !project.audio}
              className="mt-5 w-full btn-primary py-3 flex items-center justify-center gap-2 disabled:opacity-50">
              {busy || rendering ? <Loader2 size={16} className="animate-spin" /> : <Film size={16} />}
              {rendering ? "Rendering…" : r.status === "done" ? "Re-render video" : t("render_my_video")}
            </button>
            {(rendering || r.status === "failed") && (
              <div className="mt-4" data-testid="render-progress" role="status" aria-live="polite">
                <Progress value={Math.max(0, Math.min(100, Number(r.progress) || 0))} />
                <p className={`mt-2 text-sm ${r.status === "failed" ? "text-rose-700" : "text-[#587168]"}`} data-testid="render-message">{r.status === "failed" ? r.message || "Rendering stopped. You can try again." : `${Math.round(Number(r.progress) || 0)}% · ${r.message || "Preparing your video"}`}</p>
                {rendering && <p className="mt-2 text-xs text-[#587168]">You can leave this page. Your video will remain in My videos when it is ready.</p>}
              </div>
            )}
          </div>
          <div className="grid gap-3">
            <button
              data-testid="copy-full-package-btn"
              onClick={() => {
                const pkg = `${s.title || ""}\n\n${s.description || ""}\n\n${(s.hashtags || []).join(" ")}\n\nTags:\n${(s.tags || []).join(", ")}`;
                copy(pkg);
                toast.success(t("copied_package"));
              }}
              className="w-full rounded-xl border border-violet-500/40 bg-violet-600/20 py-2.5 px-4 text-xs font-semibold text-violet-800 hover:bg-violet-600/30 flex items-center justify-center gap-2 transition-colors"
            >
              <Copy size={14} />
              {t("copy_package")}
            </button>
            <Meta label="Title" value={s.title || ""} testid="title" />
            <Meta label="Description" value={s.description || ""} testid="description" />
            <Meta label="Tags" value={(s.tags || []).join(", ")} testid="tags" />
            <Meta label="Hashtags" value={(s.hashtags || []).join(" ")} testid="hashtags" />
          </div>
          <div className="rounded-2xl border border-dashed border-[#c4d8c9] p-5 flex items-start gap-4" data-testid="youtube-upload-card">
            <Youtube className="text-rose-400 shrink-0" />
            <div className="text-sm">
              <div className="font-semibold">Private YouTube upload</div>
              <p className="text-[#61736d]">Uploads go as <b>private</b> first so you can review. Connect your channel in <Link to="/settings" className="text-violet-800 font-semibold">Settings</Link> (coming next).</p>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-6"><FeedbackForm projectId={project.id} /></div>
    </section>
  );
}
