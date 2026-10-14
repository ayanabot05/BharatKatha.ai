import { useEffect, useState } from "react";
import { Heart, MessageCircle, Share2, Sparkles } from "lucide-react";

export const SHOWCASE = [
  { img: "/showcase/s0.jpg", cap: "మీరు ఎప్పుడైనా మాట్లాడే ఆవుని చూశారా?" },
  { img: "/showcase/s1.jpg", cap: "అడవిలో రాముకి బంగారు నాణేల సంచీ దొరికింది" },
  { img: "/showcase/s2.jpg", cap: "అబద్ధంతో పొందే సుఖం, నీడలాంటిది.." },
  { img: "/showcase/s3.jpg", cap: "రాము సంచీని సర్పంచికి అప్పగించాడు" },
  { img: "/showcase/s4.jpg", cap: "నిజాయితీ ఉంటే దేవుడే దారి చూపిస్తాడు!" },
];

export default function PhoneShort({ className = "" }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    const t = setInterval(() => setI((x) => (x + 1) % SHOWCASE.length), 4000);
    return () => clearInterval(t);
  }, []);
  const s = SHOWCASE[i];
  return (
    <div className={`relative ${className}`} data-testid="hero-phone">
      <div className="absolute -inset-6 rounded-[3rem] bg-rose-300/35 blur-2xl" />
      <div className="relative w-[220px] sm:w-[300px] aspect-[9/19] rounded-[2.6rem] bg-[#e7efe7] p-2.5 shadow-2xl ring-1 ring-[#c4d8c9]">
        <div className="relative h-full w-full rounded-[2.1rem] overflow-hidden bg-[#e7efe7]">
          <img key={i} src={s.img} alt="AI scene" className="absolute inset-0 h-full w-full object-cover kenburns" />
          <div className="absolute inset-0 bg-gradient-to-b from-[#29443e]/50 via-transparent to-[#29443e]/70" />
          <div className="absolute top-3 inset-x-3 flex gap-1">
            {SHOWCASE.map((_, j) => (
              <div key={j} className="h-0.5 flex-1 rounded bg-white/25 overflow-hidden">
                {j === i && <div key={`b${i}`} className="h-full bg-white bar" />}
                {j < i && <div className="h-full w-full bg-white" />}
              </div>
            ))}
          </div>
          <div className="absolute top-7 left-3 flex items-center gap-2 text-white text-xs font-semibold">
            <span className="h-6 w-6 rounded-full bg-rose-600 grid place-items-center"><Sparkles size={12} /></span>
            Telugu Kathalu · <span className="text-rose-200">Shorts</span>
          </div>
          <div key={`c${i}`} className="pop absolute bottom-20 inset-x-4 text-center">
            <span className="indic inline-block rounded-xl bg-[#29443e]/75 backdrop-blur px-3 py-2 text-white font-bold text-[15px] leading-snug">{s.cap}</span>
          </div>
          <div className="absolute right-2.5 bottom-24 flex flex-col items-center gap-4 text-white text-[10px] font-semibold">
            <div className="flex flex-col items-center"><Heart size={22} className="fill-rose-500 text-rose-500" /></div>
            <div className="flex flex-col items-center"><MessageCircle size={22} /></div>
            <div className="flex flex-col items-center"><Share2 size={22} /></div>
          </div>
          <div className="absolute bottom-5 left-3 right-14 text-white">
            <div className="indic text-sm font-bold">మాట్లాడే ఆవు - నిజాయితీ పాఠం</div>
            <div className="text-[10px] text-white/70">#shorts #TeluguStories #MoralStories</div>
          </div>
        </div>
      </div>
    </div>
  );
}
