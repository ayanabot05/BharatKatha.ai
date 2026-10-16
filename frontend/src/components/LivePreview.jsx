import { useEffect, useState } from "react";
import { mediaUrl } from "@/lib/api";
import { useLocale } from "@/context/LocaleContext";
import { RamAvatar, BlurReveal, reducedMotion } from "@/components/fx";

/* What Ram AI is doing right now, derived from the project + the step the user is on */
export function ramStatus(project, view) {
  const scenes = project.scenes || [];
  const gen = scenes.filter((s) => s.status === "generating" || s.status === "queued");
  if (project.render?.status === "rendering") return { state: "painting", text: `Rendering your video · ${Math.round(Number(project.render.progress) || 0)}%` };
  if (gen.length) return { state: "painting", text: `Painting scene ${scenes.length - gen.length + 1} of ${scenes.length}…` };
  const map = {
    1: ["thinking", "Listening to your idea"], 2: ["writing", "Shaping your script"], 3: ["idle", "Choosing the look"],
    4: ["idle", "Polishing your scenes"], 5: ["idle", "Adding the voice"], 6: ["idle", "Ready to render"],
  };
  const [state, text] = map[view] || ["idle", "Ready"];
  return { state, text };
}

const captionOf = (s) => s?.caption || s?.text || s?.narration || s?.line || "";

/* Phone preview that stays beside every step so the video is always visible while it takes shape */
export default function LivePreview({ project, view }) {
  const { t } = useLocale();
  const scenes = project.scenes || [];
  const slides = scenes.filter((s) => s.image_path);
  const [i, setI] = useState(0);
  useEffect(() => {
    if (slides.length < 2 || reducedMotion()) return undefined;
    const id = setInterval(() => setI((v) => (v + 1) % slides.length), 2800);
    return () => clearInterval(id);
  }, [slides.length]);
  const idx = slides.length ? i % slides.length : 0;
  const { state, text } = ramStatus(project, view);
  const title = project.script?.title || project.title;
  const pct = project.render?.status === "done" ? 100
    : project.render?.status === "rendering" ? Math.max(0, Math.min(99, Math.round(Number(project.render.progress) || 0)))
      : Math.round(((Math.min(project.step || 1, 6) - 1) / 6) * 100);

  return (
    <div className="lp" data-testid="live-preview">
      <div className="lp-phone" style={{ viewTransitionName: `proj-${project.id}` }}>
        <div className="lp-screen">
          {slides.length ? slides.map((s, k) => (
            <BlurReveal key={s.image_path} src={mediaUrl(s.image_path)} className={`lp-slide ${k === idx ? "on fx-kb" : ""}`} />
          )) : (
            <div className="lp-empty"><RamAvatar state={state} size={54} /> {t("Your video appears here as you build it")} </div>
          )}
          {slides.length > 0 && <><div className="lp-shade" />{captionOf(slides[idx]) && <div className="lp-cap indic">{captionOf(slides[idx])}</div>}</>}
        </div>
      </div>
      <div className="flex items-center gap-2.5 w-full">
        <RamAvatar state={state} size={34} />
        <div className="min-w-0">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#a23f58]">Ram AI</div>
          <div className="text-sm font-semibold text-[#4a3f58]" aria-live="polite">{t(text)}</div>
        </div>
      </div>
      <div className="w-full">
        <div className="flex justify-between text-[11px] font-semibold text-[#7b7083] mb-1.5"><span className="indic truncate max-w-[70%]">{title}</span><span>{pct}%</span></div>
        <div className="lp-bar"><i style={{ width: `${pct}%` }} /></div>
      </div>
    </div>
  );
}
