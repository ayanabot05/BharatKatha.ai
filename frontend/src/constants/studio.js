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
  { id: "ml", label: "Malayalam", native: "മലയാളം" },
  { id: "en", label: "English", native: "English" },
  { id: "pa", label: "Punjabi", native: "ਪੰਜਾਬੀ", disabled: true, badge: "Coming Soon" },
  { id: "or", label: "Odia", native: "ଓଡ଼ିଆ", disabled: true, badge: "Coming Soon" },
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

// Plan prices are NOT defined here. The single source of truth is the backend
// plan catalog served by GET /api/billing/plans (see backend/billing.py and the
// BILLING_PLANS_JSON env override). Read prices from the API; never hardcode them.
