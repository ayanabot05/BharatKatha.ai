# katha_studio: an Indian-first AI Shorts studio

A premium, mobile-first web app. Anyone, from a farmer with basic Telugu to a busy creator, speaks or types an idea and gets back a 1080p HD vertical Short. The video shows an AI human, cartoon or animal actually acting out the story, with a natural Indian-language narrator and captions.
Everything is made in the cloud using the owner's Google Cloud credits and bucket, so it never depends on a laptop. Indian AI models are used wherever they are ready today.

## Who it's for
- **First-time rural and small-town creators**: phone only, basic reading, never used an editor. This is the design target: if they can finish a video alone, everyone can.
- **Regional storytellers and small channels**: want 1–3 polished Shorts a day in Telugu, Hindi, Tamil or English.
- **Guna (owner/admin)**: runs the platform on his Google Cloud credits and watches cost and quality.

## Core features and experience (Phase 1, the MVP)
1. **Voice-first start**
   - The entire app interface is shown in the chosen language (Telugu/Hindi/Tamil/English).
   - **"I have an idea"**: type it, or tap the mic and speak it.
   - **"Give me an idea"**: 5 story suggestions suited to the language and region, such as moral tales, village stories, animal fables, mythology-inspired originals and kids' stories.
2. **AI Script Studio** (Gemini 3.1 Pro)
   - Writes a 30–60 second script: Hook → Story → 5–7 scenes → Ending.
   - Each scene has a narration line and an action description (what the character does on screen).
   - Three automatic checks with simple badges:
     - **Hook & pacing**: will viewers keep watching?
     - **Safety**: no 18+, sexual, violent or hateful content; it blocks or rewrites.
     - **Originality**: not a repeat of this user's past scripts.
   - The user can edit any line, tap "Make it better", or approve.
3. **Choose a style**: 7 large picture cards: Human AI, Cartoon, Storybook, Animals, Emoji face, Faceless/Cinematic, Indian mythology art. Prompts are culture- and region-aware (Indian faces, clothing, villages, festivals).
4. **Scene previews, then shot-by-shot editing (cheap step)**
   - The app first draws one still preview frame per scene, with the same main character in every scene.
   - The user fixes any scene in plain words, typed or spoken, such as "add a rat near the cat" or "make it night". Only that preview is redrawn.
   - Scenes can be reordered, deleted or retimed.
   - Video money is not spent until the user is happy with the previews.
5. **Make it real: 1080p AI video (premium step)**
   - Each approved preview becomes a real moving video clip. The AI human or character walks, cooks, runs or reacts, in vertical 1080p HD.
   - A clear cost/credit estimate shows before the user taps "Make my video".
   - A single clip can be regenerated if one comes out wrong.
6. **Audio Studio**
   - **Default: voice-over.** The character acts, and a natural Indian narrator tells the story, with no lip-sync problems.
   - **Optional per scene: "Speaks to camera" (beta).** The character says a short line on camera. Lip movement in Telugu/Hindi/Tamil may not match perfectly, so the app labels this clearly.
   - Narrator voices in each language (warm storyteller, energetic, calm, elder/grandparent).
   - Or record your own voice in the browser, or upload audio.
   - Optional background music from a built-in royalty-free set, with a volume slider.
7. **Final HD video, captions and tags**
   - The cloud joins the clips, voice and music into one 1080×1920 MP4.
   - Captions are timed word by word from the real audio and display Telugu/Hindi/Tamil letters correctly. There are 3 caption looks.
   - The app suggests a title, description and hashtags for YouTube Shorts and Instagram Reels.
8. **My Videos**: all projects (draft / previews ready / video ready). Users can preview, download in HD and copy the title and tags. Drafts can be reopened and edited.
9. **Accounts**: email + password through Supabase. Each user sees only their own work. All media is saved in the owner's Google Cloud bucket.

## User flow
1. Open the app → pick a language → sign up / log in.
2. **I have an idea** (speak/type) or **Give me an idea** (pick 1 of 5).
3. Review the script and its 3 badges → edit or tap "Make it better" → **Approve**.
4. Pick a style card.
5. Scene previews appear → fix scenes by typing or speaking → **Looks good**.
6. Choose narrator voice, record your own, or upload one → optional music → optionally mark a scene "speaks to camera".
7. See the cost estimate → **Make my HD video** → watch friendly progress messages.
8. Watch the finished 1080p Short with captions → download, copy title and tags → post on YouTube or Instagram. Direct upload comes in Phase 2.

## UI/UX feel
- **High-class and calm.** It should feel like a premium creative studio (think Apple or Canva quality), with an Indian soul: rich warm colours, elegant native-script typography and cinematic previews.
- **Easy for anyone.** One clear step per screen, a progress bar (Idea → Script → Style → Scenes → Voice → Video), big tap targets, icons on every action, very little text, and a mic wherever typing is needed.
- **Mobile-first**, while also looking polished on laptop screens.
- **Built to maintain.** Each AI provider (script, image, video, voice, captions) can be swapped behind the scenes without redesigning the app, so Indian models can replace global ones as they mature.

## Implementation phases
**Phase 1: HD Creator MVP (built now)**
Everything under Core features:
- voice/text idea entry and idea suggestions
- Gemini 3.1 Pro scripts with 3 checks
- 7 styles
- scene previews with shot-by-shot editing
- 1080p AI video clips per scene
- Indian narrator, own recording or upload, and music
- final HD video with word-timed captions
- title and tags
- My Videos
- Supabase login
- 4 interface languages
- all media in your GCS bucket

**Phase 2: Made-in-India video, publishing and growth**
- **Varya (Avataar AI / IndiaAI Mission) becomes the video engine**, either through its developer API when it opens or by running its open weights from AIKosh on your Google Cloud GPU credits. It is roughly 20× cheaper than Veo and built for Indian culture.
- YouTube (then Instagram) connection: private upload first, then scheduled publishing (for example 3 Shorts a day). It brings over the safeguards from your old repo:
  - private-only uploads
  - audience and AI/synthetic-media declarations for every video
  - approval tied to the exact file
  - a daily upload cap
  - no duplicate uploads
- **AI Growth Coach** (higher plan): reads channel analytics (views, retention, swipe-away). It explains in plain language what worked and what failed, suggests next week's videos, and gives a weekly/monthly guide.
- Trending-topic ideas by region.
- Phone OTP login.
- More languages: Kannada, Malayalam, Marathi, Gujarati, Punjabi, Bengali.
- Plans and payments (Free / Creator / Pro / Studio, with usage limits).

**Phase 3: Our own Indian AI**
- Fine-tune open Indian models from AIKosh / AI4Bharat / Sarvam / BharatGen for Indian-language scripts.
- Build regional narrator voices from consented recordings (for example a Telangana village storyteller or a Coastal Andhra grandmother).
- Train a speech-to-text model that handles dialects.
- Fine-tune Varya on Indian story styles.
- Add recurring characters for series and talking avatars.

## Assumptions
- **Made in India, today:**
  - **Narrator voice:** Sarvam **Bulbul V3**, an Indian model with natural Telugu/Hindi/Tamil and many voices.
  - **Speech-to-text** (voice input and captions): Sarvam **Saaras V4**, which handles dialects and mixed Telugu-English speech.
  - Both need a free Sarvam API key from sarvam.ai, which I'll ask for during the build.
  - Google Chirp 3 HD voices (on your credits) stay as a backup voice.
- **Video in the MVP is Google Veo 3.1 (Fast, 1080p, 9:16) on your Google credits, not Varya.** Varya launched in June 2026 but has no public developer API yet, only a web app. Running its open weights ourselves needs GPU setup that would delay the MVP. Veo is the bridge, and the app is built so Varya replaces it in Phase 2 without users noticing. **This is the main decision to challenge.**
- **Approximate cost per video with Veo:** about $0.12 per second of video, so a 40-second Short is about $5 of Google credits. Scene previews are a few cents. A per-video cap of 60 seconds and a visible estimate keep spending in check.
- **Scripts:** Gemini 3.1 Pro on your Google credits, as you chose. Sarvam-105B is a possible Indian swap later.
- **Scene previews** use Google's Gemini image model on your credits. This keeps the main character consistent and gives Veo the starting frame.
- **Voice-over is the default.** "Speaks to camera" is offered per scene as beta, because Veo's lip-sync is only reliable in English.
- **The final video is assembled in the cloud** (1080×1920, H.264). Your Windows laptop is only used to open the app in a browser.
- **What you'll provide during the build:**
  - Google Cloud project ID, region, GCS bucket name, and a service-account JSON key (Vertex AI User, Storage Object Admin, Cloud Text-to-Speech)
  - Supabase Project URL and anon/publishable key
  - Sarvam API key
- **Phase 1 limits:**
  - No YouTube/Instagram upload, analytics, payments or usage plans.
  - All users get the same features; cost is controlled by the per-video cap.
  - Background music is a small bundled royalty-free set; users can't upload music.
  - The originality check covers each user's own past scripts only, not all of YouTube.
- **Name and old code:** the product and repo name is **katha_studio**, replacing "Guna Shorts Studio". The old desktop code is not reused directly. Its rules (script validation, Indian-script captions, upload safeguards) carry over as product behaviour.
- **Repo security:** before the repo stays public, check that no `oauth-client.json`, token or `.env` file was committed. If one was, revoke and rotate it in Google Cloud.
