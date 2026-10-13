import { createContext, useContext, useState, useEffect } from "react";

const DICTIONARY = {
  new_video: { en: "New video", te: "కొత్త వీడియో", hi: "नया वीडियो", ta: "புதிய வீடியோ" },
  my_videos: { en: "My videos", te: "నా వీడియోలు", hi: "मेरे वीडियो", ta: "என் வீடியோக்கள்" },
  growth_coach: { en: "Growth Coach", te: "గ్రోత్ కోచ్", hi: "ग्रोथ कोच", ta: "வளர்ச்சி வழிகாட்டி" },
  settings: { en: "Settings", te: "సెట్టింగులు", hi: "सेटिंग्स", ta: "அமைப்புகள்" },
  sign_out: { en: "Sign out", te: "లాగౌట్", hi: "लॉग आउट", ta: "வெளியேறு" },
  step_1_label: { en: "Idea", te: "ఆలోచన", hi: "विचार", ta: "யோசனை" },
  step_2_label: { en: "Script", te: "స్క్రిప్ట్", hi: "पटकथा", ta: "கதை" },
  step_3_label: { en: "Style", te: "శైలి", hi: "शैली", ta: "பாணி" },
  step_4_label: { en: "Scenes", te: "దృశ్యాలు", hi: "दृश्य", ta: "காட்சிகள்" },
  step_5_label: { en: "Voice", te: "వాయిస్", hi: "आवाज", ta: "குரல்" },
  step_6_label: { en: "Render", te: "వీడియో", hi: "वीडियो", ta: "வீடியோ" },
  render_my_video: { en: "Render my video", te: "నా వీడియో తయారు చేయి", hi: "मेरा वीडियो बनाएं", ta: "என் வீடியோவை உருவாக்கு" },
  create_thumbnail: { en: "Create thumbnail", te: "థంబ్‌నెయిల్ చేయి", hi: "थंबनेल बनाएं", ta: "சிறுபடம் உருவாக்கு" },
  copy_package: { en: "Copy Complete YouTube Shorts Package", te: "మొత్తం YouTube వివరాలు కాపీ చేయి", hi: "पूरा YouTube पैकेज कॉपी करें", ta: "முழு YouTube தொகுப்பையும் நகலெடு" },
  burn_in_captions: { en: "Burn-in captions", te: "వీడియోపై అక్షరాలు (Captions)", hi: "वीडियो पर कैप्शन", ta: "வீడియో வசனங்கள்" },
  copied_package: { en: "Copied full metadata package for YouTube/Instagram!", te: "YouTube/Instagram వివరాలు కాపీ అయ్యాయి!", hi: "YouTube/Instagram पैकेज कॉपी किया गया!", ta: "YouTube/Instagram விவரங்கள் நகலெடுக்கப்பட்டன!" },
};

export const UI_LANGUAGES = [
  { id: "en", label: "English" },
  { id: "te", label: "తెలుగు" },
  { id: "hi", label: "हिन्दी" },
  { id: "ta", label: "தமிழ்" },
];

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const [locale, setLocale] = useState(() => {
    try {
      return localStorage.getItem("vidbharat_ui_lang") || "en";
    } catch {
      return "en";
    }
  });

  const changeLocale = (lang) => {
    setLocale(lang);
    try {
      localStorage.setItem("vidbharat_ui_lang", lang);
    } catch {
      /* ignore */
    }
  };

  const t = (key) => {
    return DICTIONARY[key]?.[locale] || DICTIONARY[key]?.en || key;
  };

  return (
    <LocaleContext.Provider value={{ locale, changeLocale, t }}>
      {children}
    </LocaleContext.Provider>
  );
}

export const useLocale = () => useContext(LocaleContext) || { locale: "en", changeLocale: () => {}, t: (k) => k };
