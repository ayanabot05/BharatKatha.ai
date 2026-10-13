export const STYLES = [
  { id: "human", label: "Human AI", hint: "Realistic Indian presenters" },
  { id: "cartoon", label: "Cartoon", hint: "3D animated characters" },
  { id: "cinematic", label: "Cinematic", hint: "Film-grade landscapes" },
  { id: "emoji", label: "Emoji", hint: "Expressive emoji mascot" },
  { id: "animals", label: "Animals", hint: "Talking animal tales" },
  { id: "storybook", label: "Storybook", hint: "Painted story pages" },
];

export const LANGUAGES = [
  { id: "hi", label: "Hindi", native: "हिन्दी" },
  { id: "bn", label: "Bengali", native: "বাংলা" },
  { id: "mr", label: "Marathi", native: "मराठी" },
  { id: "te", label: "Telugu", native: "తెలుగు" },
  { id: "ta", label: "Tamil", native: "தமிழ்" },
  { id: "gu", label: "Gujarati", native: "ગુજરાતી" },
  { id: "ur", label: "Urdu", native: "اردو" },
  { id: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
  { id: "or", label: "Odia", native: "ଓଡ଼ିଆ" },
  { id: "ml", label: "Malayalam", native: "മലയാളം" },
  { id: "en", label: "English", native: "English" },
];

export const TONES = ["Emotional", "Moral", "Funny", "Thriller", "Devotional", "Mythology", "Motivational", "Horror (kid-safe)"];
export const CATEGORIES = ["Moral stories", "Village life", "Mythology & Puranas", "Kids stories", "Love & family drama", "Mystery", "Motivation", "Animal fables", "Comedy"];
export const PLATFORMS = ["YouTube Shorts", "Instagram Reels"];

export const STEPS = [
  { n: 1, label: "Idea" },
  { n: 2, label: "Script" },
  { n: 3, label: "Style" },
  { n: 4, label: "Scenes" },
  { n: 5, label: "Voice" },
  { n: 6, label: "Render" },
];

export const PLANS = [
  { id: "free", name: "Free", price: "₹0", note: "3 videos / month", badge: "Trial", features: ["Idea + script studio", "3 video styles", "Watermarked MP4"] },
  { id: "creator", name: "Creator", price: "₹399", note: "30 videos / month", badge: "Popular", features: ["All 6 styles", "Regional AI voices", "Captions + tags", "No watermark"] },
  { id: "pro", name: "Pro", price: "₹999", note: "100 videos / month", badge: "Best value", features: ["Everything in Creator", "AI Growth Coach", "Weekly content plan", "Priority renders"] },
  { id: "studio", name: "Studio", price: "₹2,499", note: "Teams & agencies", badge: "Agency", features: ["Everything in Pro", "Brand presets", "Batch creation", "Multiple channels"] },
];
