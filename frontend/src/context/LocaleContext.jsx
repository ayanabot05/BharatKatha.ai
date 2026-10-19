import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { LANGUAGES } from "@/constants/studio";
import { translateStudioTelugu } from "./studioTelugu";

const DICTIONARY = {
  audio_duration_note: { en: "Narration is {actual} seconds; your target is {target} seconds. Adjust the script or speaking speed if you need that duration." },
  audio_paced_note: { en: "Paced to {speed}x after measuring the first read." },
  dashboard_greeting: { en: "Welcome", te: "స్వాగతం", hi: "स्वागत है", ta: "வரவேற்கிறோம்", bn: "স্বাগতম", mr: "स्वागत", gu: "સ્વાગત છે", ur: "خوش آمدید", kn: "ಸ್ವಾಗತ", ml: "സ്വാഗതം", or: "ସ୍ୱାଗତ" },
  create_video: { en: "Create a video", te: "వీడియో తయారు చేయండి", hi: "वीडियो बनाएं", ta: "வீடியோ உருவாக்குங்கள்", bn: "ভিডিও তৈরি করুন", mr: "व्हिडिओ तयार करा", gu: "વિડિયો બનાવો", ur: "ویڈیو بنائیں", kn: "ವೀಡಿಯೊ ರಚಿಸಿ", ml: "വീഡിയോ നിർമ്മിക്കുക", or: "ଭିଡିଓ ତିଆରି କରନ୍ତୁ" },
  continue_story: { en: "Continue story", te: "కథను కొనసాగించండి", hi: "कहानी जारी रखें", ta: "கதையைத் தொடருங்கள்", bn: "গল্প চালিয়ে যান", mr: "कथा पुढे सुरू ठेवा", gu: "વાર્તા આગળ વધારો", ur: "کہانی جاری رکھیں", kn: "ಕಥೆಯನ್ನು ಮುಂದುವರಿಸಿ", ml: "കഥ തുടരുക", or: "କାହାଣୀ ଜାରି ରଖନ୍ତୁ" },
  projects: { en: "Stories", te: "కథలు", hi: "कहानियाँ", ta: "கதைகள்", bn: "গল্প", mr: "कथा", gu: "વાર્તાઓ", ur: "کہانیاں", kn: "ಕಥೆಗಳು", ml: "കഥകൾ", or: "କାହାଣୀ" },
  videos_ready: { en: "Videos ready", te: "సిద్ధమైన వీడియోలు", hi: "तैयार वीडियो", ta: "தயாரான வீடியோக்கள்", bn: "তৈরি ভিডিও", mr: "तयार व्हिडिओ", gu: "તૈયાર વિડિયો", ur: "تیار ویڈیوز", kn: "ಸಿದ್ಧ ವೀಡಿಯೊಗಳು", ml: "തയ്യാറായ വീഡിയോകൾ", or: "ପ୍ରସ୍ତୁତ ଭିଡିଓ" },
  no_videos: { en: "No stories yet", te: "ఇంకా కథలు లేవు", hi: "अभी कोई कहानी नहीं", ta: "இன்னும் கதைகள் இல்லை", bn: "এখনও গল্প নেই", mr: "अजून कथा नाहीत", gu: "હજુ વાર્તાઓ નથી", ur: "ابھی کہانیاں نہیں ہیں", kn: "ಇನ್ನೂ ಕಥೆಗಳಿಲ್ಲ", ml: "ഇതുവരെ കഥകളില്ല", or: "ଏପର୍ଯ୍ୟନ୍ତ କାହାଣୀ ନାହିଁ" },
  plan: { en: "Plan", te: "ప్లాన్", hi: "प्लान", ta: "திட்டம்", bn: "প্ল্যান", mr: "प्लॅन", gu: "પ્લાન", ur: "پلان", kn: "ಯೋಜನೆ", ml: "പ്ലാൻ", or: "ପ୍ଲାନ୍" },
  language: { en: "Language", te: "భాష", hi: "भाषा", ta: "மொழி", bn: "ভাষা", mr: "भाषा", gu: "ભાષા", ur: "زبان", kn: "ಭಾಷೆ", ml: "ഭാഷ", or: "ଭାଷା" },
  step: { en: "Step", te: "దశ", hi: "चरण", ta: "படி", bn: "ধাপ", mr: "पायरी", gu: "પગલું", ur: "مرحلہ", kn: "ಹಂತ", ml: "ഘട്ടം", or: "ପର୍ଯ୍ୟାୟ" },
  scene_editor: { en: "Scene editor", te: "దృశ్యాల సవరణ", hi: "दृश्य संपादक", ta: "காட்சி திருத்தம்", bn: "দৃশ্য সম্পাদনা", mr: "दृश्य संपादन", gu: "દૃશ્ય સંપાદન", ur: "منظر کی تدوین", kn: "ದೃಶ್ಯ ಸಂಪಾದನೆ", ml: "രംഗം തിരുത്തുക", or: "ଦୃଶ୍ୟ ସମ୍ପାଦନା" },
  edit_scene: { en: "Edit words or picture", te: "మాటలు లేదా చిత్రం మార్చండి", hi: "शब्द या तस्वीर बदलें", ta: "சொற்கள் அல்லது படத்தை மாற்றுங்கள்", bn: "কথা বা ছবি বদলান", mr: "शब्द किंवा चित्र बदला", gu: "શબ્દો અથવા ચિત્ર બદલો", ur: "الفاظ یا تصویر بدلیں", kn: "ಪದಗಳು ಅಥವಾ ಚಿತ್ರ ಬದಲಿಸಿ", ml: "വാക്കുകളോ ചിത്രമോ മാറ്റുക", or: "ଶବ୍ଦ କିମ୍ବା ଛବି ବଦଳାନ୍ତୁ" },
  narration: { en: "Narration", te: "కథనం", hi: "कथन", ta: "கதை உரை", bn: "বর্ণনা", mr: "निवेदन", gu: "વર્ણન", ur: "بیان", kn: "ನಿರೂಪಣೆ", ml: "വിവരണം", or: "ବର୍ଣ୍ଣନା" },
  picture: { en: "Picture", te: "చిత్రం", hi: "तस्वीर", ta: "படம்", bn: "ছবি", mr: "चित्र", gu: "ચિત્ર", ur: "تصویر", kn: "ಚಿತ್ರ", ml: "ചിത്രം", or: "ଛବି" },
  approve_picture: { en: "Approve picture", te: "చిత్రాన్ని ఆమోదించండి", hi: "तस्वीर मंज़ूर करें", ta: "படத்தை ஒப்புக்கொள்ளுங்கள்", bn: "ছবি অনুমোদন করুন", mr: "चित्र मंजूर करा", gu: "ચિત્ર મંજૂર કરો", ur: "تصویر منظور کریں", kn: "ಚಿತ್ರ ಅನುಮೋದಿಸಿ", ml: "ചിത്രം അംഗീകരിക്കുക", or: "ଛବି ଅନୁମୋଦନ କରନ୍ତୁ" },
  generate_pictures: { en: "Generate missing pictures", te: "మిగిలిన చిత్రాలు తయారు చేయండి", hi: "बाकी तस्वीरें बनाएं", ta: "மீதமுள்ள படங்களை உருவாக்குங்கள்", bn: "বাকি ছবি তৈরি করুন", mr: "उरलेली चित्रे तयार करा", gu: "બાકી ચિત્રો બનાવો", ur: "باقی تصاویر بنائیں", kn: "ಉಳಿದ ಚಿತ್ರಗಳನ್ನು ರಚಿಸಿ", ml: "ശേഷിക്കുന്ന ചിത്രങ്ങൾ നിർമ്മിക്കുക", or: "ବାକି ଛବି ତିଆରି କରନ୍ତୁ" },
  continue_voice: { en: "Continue to voice", te: "వాయిస్‌కి వెళ్లండి", hi: "आवाज़ पर जाएं", ta: "குரலுக்குச் செல்லுங்கள்", bn: "কণ্ঠে এগিয়ে যান", mr: "आवाजाकडे जा", gu: "અવાજ તરફ જાઓ", ur: "آواز کی طرف جائیں", kn: "ಧ್ವನಿಗೆ ಮುಂದುವರಿಸಿ", ml: "ശബ്ദത്തിലേക്ക് തുടരുക", or: "ସ୍ୱରକୁ ଯାଆନ୍ତୁ" },
  have_idea: { en: "I have an idea", te: "నాకు ఒక ఆలోచన ఉంది", hi: "मेरे पास एक विचार है", ta: "எனக்கு ஒரு யோசனை உள்ளது", bn: "আমার একটি ভাবনা আছে", mr: "माझ्याकडे एक कल्पना आहे", gu: "મારી પાસે એક વિચાર છે", ur: "میرے پاس ایک خیال ہے", kn: "ನನಗೆ ಒಂದು ಕಲ್ಪನೆ ಇದೆ", ml: "എനിക്ക് ഒരു ആശയമുണ്ട്", or: "ମୋର ଏକ ଧାରଣା ଅଛି" },
  find_idea: { en: "Find me an idea", te: "నాకు ఒక ఆలోచన చూపండి", hi: "मुझे एक विचार दें", ta: "எனக்கு ஒரு யோசனை காட்டுங்கள்", bn: "আমাকে একটি ভাবনা দিন", mr: "मला एक कल्पना द्या", gu: "મને એક વિચાર આપો", ur: "مجھے ایک خیال دیں", kn: "ನನಗೆ ಒಂದು ಕಲ್ಪನೆ ನೀಡಿ", ml: "എനിക്ക് ഒരു ആശയം തരൂ", or: "ମୋତେ ଏକ ଧାରଣା ଦିଅନ୍ତୁ" },
  write_script: { en: "Write my story", te: "నా కథను రాయండి", hi: "मेरी कहानी लिखें", ta: "என் கதையை எழுதுங்கள்", bn: "আমার গল্প লিখুন", mr: "माझी कथा लिहा", gu: "મારી વાર્તા લખો", ur: "میری کہانی لکھیں", kn: "ನನ್ನ ಕಥೆ ಬರೆಯಿರಿ", ml: "എന്റെ കഥ എഴുതുക", or: "ମୋ କାହାଣୀ ଲେଖନ୍ତୁ" },
  region: { en: "Region", te: "ప్రాంతం", hi: "क्षेत्र", ta: "பகுதி", bn: "অঞ্চল", mr: "प्रदेश", gu: "વિસ્તાર", ur: "علاقہ", kn: "ಪ್ರದೇಶ", ml: "പ്രദേശം", or: "ଅଞ୍ଚଳ" },
  length: { en: "Length", te: "నిడివి", hi: "अवधि", ta: "நீளம்", bn: "দৈর্ঘ্য", mr: "कालावधी", gu: "લંબાઈ", ur: "دورانیہ", kn: "ಅವಧಿ", ml: "ദൈർഘ്യം", or: "ଅବଧି" },
  tone: { en: "Tone", te: "శైలి", hi: "भाव", ta: "உணர்வு", bn: "ভাব", mr: "भाव", gu: "ભાવ", ur: "انداز", kn: "ಭಾವ", ml: "ഭാവം", or: "ଭାବ" },
  new_video: { en: "New video", te: "కొత్త వీడియో", hi: "नया वीडियो", ta: "புதிய வீடியோ", bn: "নতুন ভিডিও", mr: "नवीन व्हिडिओ", gu: "નવો વિડિયો", ur: "نئی ویڈیو", kn: "ಹೊಸ ವೀಡಿಯೊ", ml: "പുതിയ വീഡിയോ", or: "ନୂଆ ଭିଡିଓ" },
  my_videos: { en: "My videos", te: "నా వీడియోలు", hi: "मेरे वीडियो", ta: "என் வீடியோக்கள்", bn: "আমার ভিডিও", mr: "माझे व्हिडिओ", gu: "મારા વિડિયો", ur: "میری ویڈیوز", kn: "ನನ್ನ ವೀಡಿಯೊಗಳು", ml: "എന്റെ വീഡിയോകൾ", or: "ମୋ ଭିଡିଓ" },
  growth_coach: { en: "Growth Coach", te: "వృద్ధి మార్గదర్శి", hi: "विकास मार्गदर्शक", ta: "வளர்ச்சி வழிகாட்டி", bn: "বৃদ্ধির পরামর্শ", mr: "वाढ मार्गदर्शक", gu: "વિકાસ માર્ગદર્શક", ur: "ترقی کا رہنما", kn: "ಬೆಳವಣಿಗೆ ಮಾರ್ಗದರ್ಶಿ", ml: "വളർച്ചാ വഴികാട്ടി", or: "ବୃଦ୍ଧି ମାର୍ଗଦର୍ଶକ" },
  settings: { en: "Settings", te: "సెట్టింగులు", hi: "सेटिंग्स", ta: "அமைப்புகள்", bn: "সেটিংস", mr: "सेटिंग्ज", gu: "સેટિંગ્સ", ur: "ترتیبات", kn: "ಸೆಟ್ಟಿಂಗ್‌ಗಳು", ml: "ക്രമീകരണങ്ങൾ", or: "ସେଟିଂସ୍" },
  sign_out: { en: "Sign out", te: "లాగౌట్", hi: "लॉग आउट", ta: "வெளியேறு", bn: "সাইন আউট", mr: "लॉग आउट", gu: "લૉગ આઉટ", ur: "سائن آؤٹ", kn: "ಸೈನ್ ಔಟ್", ml: "പുറത്തുകടക്കുക", or: "ସାଇନ୍ ଆଉଟ୍" },
  step_1_label: { en: "Idea", te: "ఆలోచన", hi: "विचार", ta: "யோசனை", bn: "ভাবনা", mr: "कल्पना", gu: "વિચાર", ur: "خیال", kn: "ಕಲ್ಪನೆ", ml: "ആശയം", or: "ଧାରଣା" },
  step_2_label: { en: "Script", te: "కథ", hi: "कहानी", ta: "கதை", bn: "গল্প", mr: "कथा", gu: "વાર્તા", ur: "کہانی", kn: "ಕಥೆ", ml: "കഥ", or: "କାହାଣୀ" },
  step_3_label: { en: "Style", te: "శైలి", hi: "शैली", ta: "பாணி", bn: "শৈলী", mr: "शैली", gu: "શૈલી", ur: "انداز", kn: "ಶೈಲಿ", ml: "ശൈലി", or: "ଶୈଳୀ" },
  step_4_label: { en: "Scenes", te: "దృశ్యాలు", hi: "दृश्य", ta: "காட்சிகள்", bn: "দৃশ্য", mr: "दृश्ये", gu: "દૃશ્યો", ur: "مناظر", kn: "ದೃಶ್ಯಗಳು", ml: "രംഗങ്ങൾ", or: "ଦୃଶ୍ୟ" },
  step_5_label: { en: "Voice", te: "వాయిస్", hi: "आवाज़", ta: "குரல்", bn: "কণ্ঠ", mr: "आवाज", gu: "અવાજ", ur: "آواز", kn: "ಧ್ವನಿ", ml: "ശബ്ദം", or: "ସ୍ୱର" },
  step_6_label: { en: "Video", te: "వీడియో", hi: "वीडियो", ta: "வீடியோ", bn: "ভিডিও", mr: "व्हिडिओ", gu: "વિડિયો", ur: "ویڈیو", kn: "ವೀಡಿಯೊ", ml: "വീഡിയോ", or: "ଭିଡିଓ" },
  render_my_video: { en: "Render my video", te: "నా వీడియో తయారు చేయి", hi: "मेरा वीडियो बनाएं", ta: "என் வீடியோவை உருவாக்கு" },
  create_thumbnail: { en: "Create thumbnail", te: "థంబ్‌నెయిల్ చేయి", hi: "थंबनेल बनाएं", ta: "சிறுபடம் உருவாக்கு" },
  copy_package: { en: "Copy Complete YouTube Shorts Package", te: "మొత్తం YouTube వివరాలు కాపీ చేయి", hi: "पूरा YouTube पैकेज कॉपी करें", ta: "முழு YouTube தொகுப்பையும் நகலெடு" },
  burn_in_captions: { en: "Burn-in captions", te: "వీడియోపై అక్షరాలు (Captions)", hi: "वीडियो पर कैप्शन", ta: "வீడియో வசனங்கள்" },
  copied_package: { en: "Copied full metadata package for YouTube/Instagram!", te: "YouTube/Instagram వివరాలు కాపీ అయ్యాయి!", hi: "YouTube/Instagram पैकेज कॉपी किया गया!", ta: "YouTube/Instagram விவரங்கள் நகலெடுக்கப்பட்டன!" },
};

export const UI_LANGUAGES = LANGUAGES.filter((l) => !l.disabled).map(({ id, native }) => ({ id, label: native }));

// A build may set REACT_APP_DEFAULT_UI_LANG to open in a specific language (e.g. a
const DEFAULT_UI_LANG = process.env.REACT_APP_DEFAULT_UI_LANG || "en";

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const [locale, setLocale] = useState(() => {
    try {
      return localStorage.getItem("vidbharat_ui_lang") || DEFAULT_UI_LANG;
    } catch {
      return DEFAULT_UI_LANG;
    }
  });

  const changeLocale = useCallback((lang) => {
    setLocale(lang);
    try {
      localStorage.setItem("vidbharat_ui_lang", lang);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ur" ? "rtl" : "ltr";
  }, [locale]);

  const t = (key, values = {}) => {
    const text = (locale === "te" && translateStudioTelugu(key)) || DICTIONARY[key]?.[locale] || DICTIONARY[key]?.en || key;
    return String(text ?? "").replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match);
  };

  return (
    <LocaleContext.Provider value={{ locale, changeLocale, t }}>
      {children}
    </LocaleContext.Provider>
  );
}

export const useLocale = () => useContext(LocaleContext) || { locale: "en", changeLocale: () => {}, t: (k) => k };
