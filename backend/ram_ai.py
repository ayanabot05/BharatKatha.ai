"""Ram AI 2.0 — Cultural Craft Engine for Indian Short-Form Video.
Craft corpus + region aesthetics + hard checks + hook scoring for the Pulse loop.
Weights are NOT trained here. This is a rule-and-corpus layer.
"""
import re
import unicodedata
from typing import Any, Dict, List, Tuple

# ---------- 1. CURATED GOLD HOOKS (32) ----------
RAM_AI_HOOKS: Dict[str, List[Dict[str, str]]] = {
    "te": [
        {"genre": "Moral", "hook": "ఒక్క చిన్న అబద్ధం... ఒక తండ్రి 20 ఏళ్ల జీవితాన్ని ఎలా మార్చేసిందో తెలుసా?", "topic": "తండ్రి త్యాగం"},
        {"genre": "Village", "hook": "మా ఊరి చెరువులో రాత్రి 12 గంటలకు ఆ గంట ఎందుకు మోగుతుందో ఎవరికీ తెలీదు!", "topic": "గ్రామ రహస్యం"},
        {"genre": "Family", "hook": "అమ్మ దాచిన ఆ పాత పెట్టెలో అసలు ఏముందో చూసి కొడుకు కన్నీళ్లు ఆగలేదు.", "topic": "అమ్మ ప్రేమ"},
        {"genre": "Mystery", "hook": "ఈ గుడి తలుపులు 400 ఏళ్లుగా ఎవరూ తెరవలేదు... కారణం తెలిస్తే ఒళ్లు గగుర్పొడుస్తుంది!", "topic": "రహస్య ఆలయం"},
        {"genre": "Kids", "hook": "కోతికి అద్దం దొరికితే ఏం చేసింది? ఈ చిన్న కథలో దాగున్న పెద్ద పాఠం!", "topic": "తెలివైన జంతువులు"},
        {"genre": "Comedy", "hook": "మా ఊరి సర్పంచ్ వేసిన ప్లాన్ చూసి ఊరంతా పడీ పడీ నవ్వింది!", "topic": "హాస్యం"},
        {"genre": "Motivation", "hook": "జేబులో 10 రూపాయలు లేని కుర్రాడు... నేడు కోట్లకు అధిపతి ఎలా అయ్యాడు?", "topic": "స్ఫూర్తి"},
        {"genre": "Moral", "hook": "ఎద్దును అమ్మేసిన రైతు... మరుసటి రోజు ఉదయం దాన్ని చూసి ఎందుకు షాక్ అయ్యాడు?", "topic": "రైతు నిజాయితీ"},
    ],
    "hi": [
        {"genre": "Moral", "hook": "एक गरीब मां की वो गुप्त डायरी, जिसने उसके घमंडी बेटे की आंखें खोल दीं।", "topic": "मां का त्याग"},
        {"genre": "Village", "hook": "बिहार के इस छोटे से गांव में हर रात पीपल के पेड़ के पास कौन दिया जलाता है?", "topic": "गांव का रहस्य"},
        {"genre": "Family", "hook": "पिताजी ने वसीयत में अपनी पुरानी टूटी घड़ी क्यों दी? राज जानकर बेटा रो पड़ा।", "topic": "पिता की सीख"},
        {"genre": "Mystery", "hook": "काशी की इस रहस्यमयी गली में जो भी गया, वो कभी वापस क्यों नहीं लौटा?", "topic": "काशी का रहस्य"},
        {"genre": "Kids", "hook": "शेर और चालाक खरगोश की ऐसी कहानी जो आपने पहले कभी नहीं सुनी होगी!", "topic": "चालाक खरगोश"},
        {"genre": "Comedy", "hook": "पंडित जी की चालाक बिल्ली ने जब गांव के दरोगा को दिन में तारे दिखा दिए!", "topic": "देसी हास्य"},
        {"genre": "Motivation", "hook": "सड़क पर चाय बेचने वाले लड़के ने जब पहली बार हवाई जहाज में उड़ान भरी!", "topic": "सफलता का सफर"},
        {"genre": "Village", "hook": "राजस्थान की वो वीरान हवेली जहां 100 साल से कोई रात को नहीं रुका!", "topic": "प्राचीन हवेली"},
    ],
    "ta": [
        {"genre": "Moral", "hook": "ஒரு தாயின் கடைசி ஆசை... மகனை கோடீஸ்வரனாக்கிய அந்த ஒரு மர்ம சொல்!", "topic": "தாயின் அன்பு"},
        {"genre": "Village", "hook": "எங்கள் கிராமத்து ஆலமரத்தடியில் நள்ளிரவில் கேட்கும் அந்த வினோத சத்தம் என்ன?", "topic": "கிராமத்து மர்மம்"},
        {"genre": "Family", "hook": "அப்பா மறைத்து வைத்த அந்த பழைய சைக்கிளின் பின்னால் இருந்த உண்மை!", "topic": "தந்தையின் தியாகம்"},
        {"genre": "Mystery", "hook": "தஞ்சை பெரிய கோயிலின் இந்த ரகசிய கதவு ஏன் 1000 ஆண்டுகளாக திறக்கப்படவில்லை?", "topic": "தஞ்சை ரகசியம்"},
        {"genre": "Kids", "hook": "புத்திசாலி அணிலும் பேராசைக்கார குரங்கும்... சிரிக்க வைக்கும் குட்டி கதை!", "topic": "சிறுவர் கதை"},
        {"genre": "Comedy", "hook": "ஊர் தலைவர் போட்ட வினோதமான சட்டம்... ஊரே சிரித்த சம்பவம்!", "topic": "கிராமத்து நகைச்சுவை"},
        {"genre": "Motivation", "hook": "காலில் செருப்பு கூட இல்லாத கிராமத்து மாணவன் ஐஏஎஸ் ஆன உண்மை கதை!", "topic": "வெற்றிப் பயணம்"},
        {"genre": "Moral", "hook": "விவசாயி காப்பாற்றிய அந்த பாம்பு செய்த ஆச்சரியமான நன்றிக்கடன்!", "topic": "நன்றி மறவாமை"},
    ],
    "en": [
        {"genre": "Moral", "hook": "He gave his last piece of bread to a stranger—what happened 10 minutes later will shock you.", "topic": "Karma & Kindness"},
        {"genre": "Village", "hook": "In a hidden Himalayan village, residents speak a language no outsider can decode.", "topic": "Mountain Secret"},
        {"genre": "Family", "hook": "A grandfather's secret lockbox that revealed why he never celebrated his birthday.", "topic": "Family Sacrifice"},
        {"genre": "Mystery", "hook": "The forgotten fortress in the Western Ghats that vanished from British maps in 1840.", "topic": "Vanishing Fort"},
        {"genre": "Kids", "hook": "Why the baby elephant refused to drink water until the ant spoke!", "topic": "Jungle Wisdom"},
        {"genre": "Comedy", "hook": "The groom who brought a 40-page Excel sheet to his traditional Indian wedding!", "topic": "Wedding Humor"},
        {"genre": "Motivation", "hook": "From sleeping on railway platforms to building a ₹100-crore empire.", "topic": "True Grit"},
        {"genre": "Culture", "hook": "The 1,000-year-old temple pillar that hangs completely in mid-air with zero support.", "topic": "Architectural Wonder"},
    ],
    # ---- SEED hooks for new languages. Replace with native-reviewed hooks before treating as gold. ----
    "kn": [
        {"genre": "Moral", "hook": "ಒಂದು ಸುಳ್ಳು... ಒಬ್ಬ ತಂದೆಯ 20 ವರ್ಷಗಳ ಬದುಕನ್ನು ಹೇಗೆ ಬದಲಿಸಿತು?", "topic": "ತಂದೆಯ ತ್ಯಾಗ"},
        {"genre": "Village", "hook": "ನಮ್ಮ ಊರಿನ ಕೆರೆಯಲ್ಲಿ ರಾತ್ರಿ 12 ಗಂಟೆಗೆ ಆ ಗಂಟೆ ಯಾಕೆ ಬಾರಿಸುತ್ತದೆ?", "topic": "ಗ್ರಾಮ ರಹಸ್ಯ"},
        {"genre": "Family", "hook": "ಅಮ್ಮ ಬಚ್ಚಿಟ್ಟ ಆ ಹಳೆಯ ಪೆಟ್ಟಿಗೆಯಲ್ಲಿ ಏನಿತ್ತು?", "topic": "ಅಮ್ಮ ಪ್ರೀತಿ"},
        {"genre": "Motivation", "hook": "ಜೇಬಿನಲ್ಲಿ 10 ರೂಪಾಯಿ ಇಲ್ಲದ ಹುಡುಗ ಇಂದು ಕೋಟ್ಯಧಿಪತಿ ಆದ ಕಥೆ!", "topic": "ಸ್ಫೂರ್ತಿ"},
    ],
    "ml": [
        {"genre": "Moral", "hook": "ഒരു ചെറിയ നുണ... ഒരു അച്ഛന്റെ 20 വർഷം മാറ്റിമറിച്ചതെങ്ങനെ?", "topic": "അച്ഛന്റെ ത്യാഗം"},
        {"genre": "Village", "hook": "ഞങ്ങളുടെ ഗ്രാമത്തിലെ കുളത്തിൽ രാത്രി 12 മണിക്ക് ആ മണി എന്തിന് മുഴങ്ങുന്നു?", "topic": "ഗ്രാമ രഹസ്യം"},
        {"genre": "Family", "hook": "അമ്മ ഒളിപ്പിച്ച ആ പഴയ പെട്ടിയിൽ എന്തുണ്ടായിരുന്നു?", "topic": "അമ്മയുടെ സ്നേഹം"},
        {"genre": "Motivation", "hook": "പോക്കറ്റിൽ 10 രൂപയില്ലാത്ത ചെറുക്കൻ ഇന്ന് കോടീശ്വരൻ!", "topic": "പ്രചോദനം"},
    ],
    "bn": [
        {"genre": "Moral", "hook": "একটা ছোট মিথ্যা... এক বাবার ২০ বছরের জীবন কীভাবে বদলে দিল?", "topic": "বাবার ত্যাগ"},
        {"genre": "Village", "hook": "আমাদের গ্রামের পুকুরে রাত ১২টায় ওই ঘণ্টা কেন বাজে কেউ জানে না!", "topic": "গ্রামের রহস্য"},
        {"genre": "Family", "hook": "মা লুকিয়ে রাখা সেই পুরনো বাক্সে আসলে কী ছিল?", "topic": "মায়ের ভালোবাসা"},
        {"genre": "Motivation", "hook": "পকেটে ১০ টাকা নেই যে ছেলেটা, আজ সে কোটিপতি!", "topic": "অনুপ্রেরণা"},
    ],
    "mr": [
        {"genre": "Moral", "hook": "एक छोटा खोटं... एका वडिलांचं 20 वर्षांचं आयुष्य कसं बदललं?", "topic": "वडिलांचा त्याग"},
        {"genre": "Village", "hook": "आमच्या गावच्या तलावात रात्री 12 वाजता ती घंटा का वाजते कोणालाच माहीत नाही!", "topic": "गावचं रहस्य"},
        {"genre": "Family", "hook": "आईने लपवलेल्या त्या जुन्या पेटीत नक्की काय होतं?", "topic": "आईचं प्रेम"},
        {"genre": "Motivation", "hook": "खिशात 10 रुपये नसलेला मुलगा आज कोट्यधीश कसा झाला?", "topic": "प्रेरणा"},
    ],
}

# ---------- 2. BANNED OPENERS (expanded) ----------
BANNED_OPENINGS = [
    r"once upon a time", r"once there lived", r"long long ago", r"in a land far away",
    r"there was a time", r"in ancient times", r"ages ago",
    r"అనగనగా", r"ఒకానొక", r"ఒకప్పుడు ఒక", r"పూర్వం ఒక",
    r"एक बार की बात है", r"बहुत पुरानी बात है", r"किसी गांव में एक", r"पुराने ज़माने में", r"किसी ज़माने में",
    r"ஒரு ஊர்ல ஒரு", r"முன்னொரு காலத்தில்", r"ஒரு காலத்தில்", r"பழைய காலத்தில்",
    r"ಒಂದಾನೊಂದು ಊರಿನಲ್ಲಿ", r"ಒಂದು ಕಾಲದಲ್ಲಿ",
    r"ഒരിടത്ത് ഒരിക്കൽ", r"പണ്ട് പണ്ട്",
    r"এক ছিল রাজা", r"একদা এক গ্রামে", r"সেকালে",
    r"एक होता राजा", r"पूर्वी एक गावात", r"जुन्या काळी",
]

# ---------- 3. REGION AESTHETICS (10) ----------
REGION_AESTHETICS = {
    "Telangana": "Rich red soil, Deccan granite boulders, Bathukamma floral motifs, Pochampally handloom, neem-tree village centre.",
    "Andhra": "Lush Godavari delta waterways, coconut groves, tile-roofed pelli illu, white dhoti with gold zari, coastal morning mist.",
    "Rayalaseema": "Arid red earth, Kadapa stone masonry, hill forts under blue sky, rustic cotton attire, golden pastoral light.",
    "Tamil Nadu": "Gopuram silhouettes, Chettinad courtyards, temple stone carvings, silk veshti, kuthuvilakku lamps.",
    "Hindi Belt": "Ganga ghats, terracotta courtyards, mustard fields, brass vessels, kurta-gamcha, dusty golden-hour lanes.",
    "Karnataka": "Mysore palace arches, sandalwood tones, Karnataka silk, Deccan plateau light, jasmine garlands.",
    "Kerala": "Backwater canals, coconut palms, red laterite walls, kasavu cream-and-gold saree, temple lamp glow at dusk.",
    "Bengal": "Terracotta temples, Durga Puja pandals, yellow taxis, Bengali red-bordered saree, misty Hooghly ghats.",
    "Maharashtra": "Sahyadri hills, Warkari saffron flags, Paithani silk, bullock carts, Koli coastal fishing boats.",
    "Odisha": "Jagannath temple spires, Pattachitra scroll art, silver filigree, Odissi dance mudras, Rath Yatra crowds.",
    "Punjab": "Golden wheat fields, Phulkari embroidery, Gurudwara domes, mustard blooms, bhangra drum beats.",
    "Northeast": "Green hills of Meghalaya, bamboo stilt houses, Naga shawls, living root bridges, misty pine forests.",
}

# ---------- 4. SCRIPT RANGES ----------
INDIC_RANGES = {
    "te": (0x0C00, 0x0C7F),  # Telugu
    "hi": (0x0900, 0x097F),  # Devanagari
    "mr": (0x0900, 0x097F),  # Devanagari
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "ml": (0x0D00, 0x0D7F),  # Malayalam
    "bn": (0x0980, 0x09FF),  # Bengali
    "gu": (0x0A80, 0x0AFF),  # Gujarati
    "or": (0x0B00, 0x0B7F),  # Odia
    "ur": (0x0600, 0x06FF),  # Urdu (Arabic script)
}

# Language-specific words per second calibration based on measured narration rates
WORDS_PER_SECOND = {
    "en": 2.1,
    "hi": 2.0,
    "ur": 2.0,
    "pa": 1.9,
    "bn": 1.8,
    "mr": 1.8,
    "te": 1.8,
    "gu": 1.8,
    "ta": 1.7,
    "kn": 1.7,
    "or": 1.7,
    "ml": 1.65,
}

SEXUAL_HATE_BLOCKLIST = [
    r"\bsex\b", r"\bporn\b", r"\bnude\b", r"\bnaked\b", r"\berotic\b", r"\bkill yourself\b",
    r"\brape\b", r"\bgore\b", r"\bblood bath\b", r"\bkamini\b", r"\braand\b", r"\bmadarchod\b",
    r"పోర్న్", r"సెక్స్", r"अश्लील", r"सेक्स", r"ஆபாச", r"போர்ன்",
]

# ---------- 5. CHECKS ----------
def check_native_script(text: str, lang: str) -> Tuple[bool, str]:
    text = unicodedata.normalize("NFKC", text or "")
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False, "No text found to verify the narration language."
    if lang == "en":
        latin = sum("LATIN" in unicodedata.name(ch, "") for ch in letters)
        if latin / len(letters) < 0.70:
            return False, "English narration must use mostly Latin letters."
        return True, "Predominantly Latin letters; English language and fluency still need review."
    if lang not in INDIC_RANGES:
        return False, f"Unsupported narration language: {lang}."
    low, high = INDIC_RANGES[lang]
    # Count letters on both sides: combining vowel marks must not inflate the ratio.
    indic = sum(low <= ord(ch) <= high or
                (lang == "ur" and (0x0750 <= ord(ch) <= 0x077F or 0x08A0 <= ord(ch) <= 0x08FF))
                for ch in letters)
    if indic / len(letters) < 0.70:
        return False, f"Script must use native {lang} letters, not Latin."
    return True, "Expected script predominates; language and fluency still need review."


def check_scene_languages(scenes, lang):
    for number, scene in enumerate(scenes, 1):
        passed, detail = check_native_script(scene.get("narration", ""), lang)
        if not passed:
            return False, f"Scene {number}: {detail}"
    if not scenes:
        return False, "No scene narration to check."
    return True, "Every scene uses the expected script. This does not verify language or natural phrasing."

def check_hook_pacing(scenes: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if not scenes:
        return False, "No scenes present."
    w = len(scenes[0].get("narration", "").split())
    if w > 10:
        return False, f"Hook too wordy ({w} words). Aim for 5-8 spoken words; check the generated audio timing."
    if w < 3:
        return False, "Hook too short for a curiosity loop."
    return True, f"Hook text is concise ({w} words). Spoken duration must be checked using audio."

def check_narration_budget(scenes: List[Dict[str, Any]], duration: int, lang: str = "") -> Tuple[bool, str]:
    words = sum(len(str(s.get("narration", "")).split()) for s in scenes)
    wps = WORDS_PER_SECOND.get(lang, 1.8)
    target = int(duration * wps)
    ceiling = int(duration * (wps + 0.35))
    if words > ceiling:
        return False, f"Narration has {words} words for {duration}s. Shorten toward {target} words, then verify with generated audio."
    return True, f"Narration text is within the {duration}s planning budget ({words} words). Verify with generated audio."

def check_scene_count(scenes: List[Dict[str, Any]]) -> Tuple[bool, str]:
    n = len(scenes)
    if n < 5 or n > 7:
        return False, f"{n} scenes. Shorts pacing requires 5-7."
    return True, f"Optimal scene count ({n})."

def check_scene_completeness(scenes: List[Dict[str, Any]]) -> Tuple[bool, str]:
    for number, scene in enumerate(scenes, 1):
        if not str(scene.get("narration") or "").strip():
            return False, f"Scene {number} needs spoken narration."
        if not str(scene.get("visual") or "").strip():
            return False, f"Scene {number} needs a visual direction before image generation."
    return True, "Every scene has narration and a visual direction."

def check_repeated_narration(scenes: List[Dict[str, Any]]) -> Tuple[bool, str]:
    seen = {}
    def normalized(text):
        text = unicodedata.normalize("NFKC", text).casefold()
        return "".join(ch for ch in text if unicodedata.category(ch)[0] in "LMN")
    for number, scene in enumerate(scenes, 1):
        narration = str(scene.get("narration") or "")
        sentences = [normalized(part) for part in re.split(r"[.!?।॥؟۔]+", narration)]
        sentences = [part for part in sentences if part]
        if any(left == right and len(left) >= 4 for left, right in zip(sentences, sentences[1:])):
            return False, f"Scene {number} repeats the same spoken sentence twice."
        line = normalized(narration)
        if line and line in seen:
            return False, f"Scenes {seen[line]} and {number} repeat the same spoken line. Give each scene a new story beat."
        if line:
            seen[line] = number
    return True, "No scene narration is repeated verbatim."

def check_ending_beat(scenes: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if not scenes:
        return False, "No scenes."
    last = scenes[-1]
    if not str(last.get("narration") or "").strip():
        return False, "Final scene needs a spoken payoff."
    beat = str(last.get("beat", "")).lower()
    if any(k in beat for k in ("ending", "twist", "payoff", "cta")):
        return True, "Ending delivers payoff/CTA."
    if len(str(last.get("narration", "")).split()) >= 4:
        return True, "Ending beat verified."
    return False, "Final scene lacks payoff or CTA."

def check_refusal_patterns(text: str) -> Tuple[bool, str]:
    for pat in BANNED_OPENINGS:
        if re.search(pat, text, re.IGNORECASE):
            return False, f"Cliché opener blocked: '{pat}'. Start in the middle of the action."
    return True, "No cliché openings."

def check_safety_block(text: str) -> Tuple[bool, str]:
    for bad in SEXUAL_HATE_BLOCKLIST:
        if re.search(bad, text, re.IGNORECASE):
            return False, f"STRICT BLOCK: prohibited term '{bad}' detected."
    return True, "Clean and safe for all audiences."

def run_ram_ai_checks(script: Dict[str, Any], lang: str, duration: int = 45) -> Dict[str, Any]:
    scenes = script.get("scenes", [])
    all_nar = " ".join(s.get("narration", "") for s in scenes)
    hook = scenes[0].get("narration", "") if scenes else ""
    full = f"{script.get('title','')} {script.get('hook','')} {all_nar} {script.get('story','')}"

    checks = [
        {"check": "Native Script", "passed": check_scene_languages(scenes, lang)[0], "detail": check_scene_languages(scenes, lang)[1]},
        {"check": "Hook Length (Text Estimate)", "passed": check_hook_pacing(scenes)[0], "detail": check_hook_pacing(scenes)[1]},
        {"check": "Narration Length (Text Estimate)", "passed": check_narration_budget(scenes, duration, lang)[0], "detail": check_narration_budget(scenes, duration, lang)[1]},
        {"check": "5-7 Scene Cadence", "passed": check_scene_count(scenes)[0], "detail": check_scene_count(scenes)[1]},
        {"check": "Complete Scene Directions", "passed": check_scene_completeness(scenes)[0], "detail": check_scene_completeness(scenes)[1]},
        {"check": "No Repeated Narration", "passed": check_repeated_narration(scenes)[0], "detail": check_repeated_narration(scenes)[1]},
        {"check": "Climactic Ending / Payoff", "passed": check_ending_beat(scenes)[0], "detail": check_ending_beat(scenes)[1]},
        {"check": "Cliché Opener Block", "passed": check_refusal_patterns(hook)[0], "detail": check_refusal_patterns(hook)[1]},
        {"check": "Safety & Brand Protection", "passed": check_safety_block(full)[0], "detail": check_safety_block(full)[1], "fatal": True},
    ]
    all_passed = all(c["passed"] for c in checks)
    safety_passed = next(c["passed"] for c in checks if c.get("fatal"))
    fixes = [c["detail"] for c in checks if not c["passed"]]

    return {
        "all_passed": all_passed,
        "safety_passed": safety_passed,
        "checks": checks,
        "fixes": fixes,
        "engine": "Ram AI 2.0 Craft Validator",
        "rating_label": "Ram AI Craft Opinion",
        "disclaimer": "Evaluated against Indian short-form story structure. Not an algorithmic view forecast.",
    }

# ---------- 6. LOOKUPS ----------
def get_regional_hooks(lang: str) -> List[Dict[str, str]]:
    # Unreviewed English examples can steer other languages toward English phrasing.
    return RAM_AI_HOOKS.get(lang, [])

def get_region_aesthetic_note(region: str) -> str:
    for k, v in REGION_AESTHETICS.items():
        if k.lower() in (region or "").lower():
            return v
    return (f"Use details genuinely associated with {region} only when they fit the story; "
            "avoid inventing regional clothing, landmarks or customs.")

def score_hook_novelty(hook: str, lang: str) -> float:
    """0.0 = exact duplicate of a corpus hook. 1.0 = fully novel."""
    if not hook:
        return 0.0
    corpus = [h["hook"].lower() for h in get_regional_hooks(lang)]
    h = hook.lower()
    for c in corpus:
        if h == c:
            return 0.0
        overlap = len(set(h.split()) & set(c.split()))
        if overlap / max(len(h.split()), 1) > 0.7:
            return 0.3
    return 1.0
